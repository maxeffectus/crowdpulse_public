#include "engine.h"

#include <QtCore/QFile>
#include <QtCore/QUrl>

#include "device_agent.h"
#include "ini.h"
#include "internal_api_server.h"
#include "plugin.h"
#include "utils.h"
#include "webapp_runner.h"

#include <nx/sdk/helpers/action_response.h>
#include <nx/sdk/helpers/active_setting_changed_response.h>
#include <nx/utils/log/format.h>
#include <nx/kit/json.h>

namespace tigre::crowdpulse {

using namespace nx::sdk;
using namespace nx::sdk::analytics;

Engine::Engine(Plugin* plugin):
    nx::sdk::analytics::Engine(ini().enableOutput),
    m_plugin(plugin),
    m_api(std::make_unique<InternalApiServer>(this)),
    m_runtimeDir(runtimeDataDir())
{
    if (!ini().disableUnpack)
    {
        if (!unpackResources(":/webapp/", m_runtimeDir))
        {
            throw std::runtime_error(
                NX_FMT("Failed to unpack webapp to %1", m_runtimeDir).toStdString());
        }
    }

    launchServerInfoTimer();
}

Engine::~Engine()
{
    m_asyncGuard->terminate();
    m_serverInfoTimer.pleaseStopSync();
}

void Engine::deviceAgentAboutToBeDestroyed(const std::string& id)
{
    m_deviceAgents.lock()->erase(id);
}

std::string Engine::manifestString() const
{
    QFile file(":/manifests/engine_manifest.json");
    if (!file.open(QFile::ReadOnly))
        return {};
    return file.readAll().toStdString();
}

nx::sdk::Result<const nx::sdk::ISettingsResponse*> Engine::settingsReceived()
{
    startWebApplication();
    return nullptr;
}

void Engine::doObtainDeviceAgent(Result<IDeviceAgent*>* outResult, const IDeviceInfo* deviceInfo)
{
    auto agent = new DeviceAgent(this, deviceInfo);
    m_deviceAgents.lock()->insert_or_assign(agent->deviceId(), agent);
    *outResult = agent;
}

void Engine::doGetSettingsOnActiveSettingChange(
    nx::sdk::Result<const nx::sdk::IActiveSettingChangedResponse*>* outResult,
    const nx::sdk::IActiveSettingChangedAction* activeSettingChangedAction)
{
    const std::string_view activeSetting(activeSettingChangedAction->activeSettingName());
    qDebug() << __func__ << activeSetting.data();

    if (activeSetting == "webapp.open")
    {
        const auto actionResponse = makePtr<nx::sdk::ActionResponse>();

        const bool useProxy = [activeSettingChangedAction]()
        {
            const auto values = toStdMap(activeSettingChangedAction->settingsValues());
            if (auto it = values.find("webapp.useProxy"); it != values.end())
                return toBool(it->second);
            return false;
        }();
        actionResponse->setUseProxy(useProxy);
        actionResponse->setActionUrl(webAppUrl().toString().toStdString());

        auto response = makePtr<nx::sdk::ActiveSettingChangedResponse>();
        response->setActionResponse(actionResponse);
        *outResult = response.releasePtr();
    }
    else if (activeSetting == "webapp.stop")
    {
        if (m_appRunner)
            m_appRunner->stop();
    }
    else if (activeSetting == "webapp.restart")
    {
        if (m_appRunner)
            m_appRunner->restart();
    }
}

DeviceAgent* Engine::getDeviceAgent(const std::string &id) const
{
    auto agents = m_deviceAgents.lock();
    if (auto it = agents->find(id); it != agents->end())
        return it->second;
    return nullptr;
}

std::vector<std::string> Engine::getDeviceAgentIds() const
{
    std::vector<std::string> ids;

    auto agents = m_deviceAgents.lock();
    for (const auto& [id, _]: *agents)
        ids.push_back(id);

    return ids;
}

void Engine::updateAuth(AuthData newData)
{
    auto curData = m_authData.lock();
    if (curData->user != newData.user || curData->token != newData.token)
    {
        qDebug() << "Auth updated";
        *curData = std::move(newData);
        curData.unlock();
        auto agents = m_deviceAgents.lock();
        for (const auto& [_, agent]: *agents)
            agent->authUpdated();
    }
}

AuthData Engine::authData() const
{
    return *(m_authData.lock());
}

std::optional<ServerInfo> Engine::serverInfo() const
{
    return m_serverInfo;
}

void Engine::pushMetadataToApp(QString metadata)
{
    auto url = webAppUrl();
    url.setPath("/metadata");

    const auto tracks = metadata.split('\n');
    for (const auto& track: tracks)
    {
        m_httpClient.doPost(
            url,
            nx::network::http::header::ContentType::kJson.toString(),
            track.toStdString());
    }
}

void Engine::pushDiagEvent(DiagEvent event) const
{
    pushPluginDiagnosticEvent(
        event.level, std::move(event.caption), std::move(event.description));
}

Plugin* Engine::plugin() const
{
    return m_plugin;
}

int64_t Engine::currentSystemTime() const
{
    return m_plugin->utilityProvider()->vmsSystemTimeSinceEpochMs();
}

nx::utils::Url Engine::webAppUrl() const
{
    nx::utils::Url url;
    url.setScheme(nx::network::http::kUrlSchemeName);
    url.setHost("localhost");
    url.setPort(webAppPort());
    return url;
}

int Engine::webAppPort() const
{
    return QString::fromStdString(settingValue("webapp.port")).toInt();
}

void Engine::startWebApplication()
{
    if (!m_serverInfo)
    {
        qDebug() << "Cant start before info received";
        return;
    }

    if (!m_appRunner)
        m_appRunner = std::make_unique<WebappRunner>();

    auto parameters = WebappParameters{
        .path = m_runtimeDir + "/flask_app",
        .httpPort = webAppPort(),
        .apiPort = m_api->port(),
        .mediaserverPort = m_serverInfo->port,
        .autoRestart = toBool(settingValue("webapp.autoRestart")),
    };

    auto onStarted = m_asyncGuard.wrap(
        [this](bool started)
        {
            if (!started)
            {
                pushPluginDiagnosticEvent(
                    IPluginDiagnosticEvent::Level::error,
                    "CrowdPulse Web Application",
                    "Web Application failed to start");
            }
        });

    m_appRunner->start(std::move(parameters), std::move(onStarted));
}

void Engine::launchServerInfoTimer()
{
    m_serverInfoTimer.start(
        std::chrono::seconds(1),
        m_asyncGuard.wrap([this](){ fetchServerInfo(); }));
}

void Engine::fetchServerInfo()
{
    m_plugin->doMediaserverGetRequest(
        "/rest/v3/servers/this",
        m_asyncGuard.wrap([this](auto result)
        {
            onServerInfoFetched(std::move(result));
        }));
}

void Engine::onServerInfoFetched(RequestCompletionHandler::CompletionResult result)
{
    if (!result)
    {
        qDebug() << __func__ << "error" << result.error().c_str();
        launchServerInfoTimer();
        return;
    }

    auto parseResult = parseServerInfo(std::move(result.value()));
    if (!parseResult)
    {
        pushPluginDiagnosticEvent(
            IPluginDiagnosticEvent::Level::warning,
            "API Respose parsing error",
            NX_FMT("Error occured while parsing server response: %1", parseResult.error()).toStdString());
        return;
    }

    m_serverInfo = std::move(parseResult.value());
    if (!m_serverInfo->aiManagerPresent)
    {
        pushPluginDiagnosticEvent(
            IPluginDiagnosticEvent::Level::warning,
            "Nx AI Manager not found",
            "Nx AI Manager is essential to CrowdPulse Plugin to work properly. "
            "Please check your mediaserver setup.");
    }

    startWebApplication();
}

Engine::ExpectedServerInfo Engine::parseServerInfo(const std::string& data) const
{
    std::string error;
    const auto json = nx::kit::Json::parse(data, error);
    if (!json.is_object())
        return nx::utils::unexpected(std::move(error));

    const int port = QUrl::fromUserInput(json["url"].string_value().c_str()).port();
    if (port < 0)
        return nx::utils::unexpected(std::string("Can't extract port"));

    ServerInfo result;
    result.port = port;

    const nx::kit::Json::object plugins =
        json["parameters"]["analyticsTaxonomyDescriptors"]["pluginDescriptors"].object_items();
    result.aiManagerPresent = plugins.find("nx.nxai") != plugins.end();

    return result;
}

} // tigre::crowdpulse
