#include "device_agent.h"

#include "engine.h"
#include "ini.h"
#include "stream_reader.h"

#include <nx/sdk/analytics/helpers/event_metadata_packet.h>
#include <nx/sdk/helpers/settings_response.h>

#include <QtCore/QFile>

namespace tigre::crowdpulse {

using namespace nx::sdk;
using namespace nx::sdk::analytics;

nx::utils::Url makeStreamUrl(Engine* engine, const nx::sdk::IDeviceInfo* deviceInfo)
{
    nx::utils::Url url;
    url.setScheme(nx::network::rtsp::kSecureUrlSchemeName);
    url.setHost("localhost");
    url.setPath(QString(deviceInfo->id()).replace('{', "").replace('}', "").prepend('/'));
    url.setPort(engine->serverInfo().value_or(ServerInfo{}).port);
    url.setQuery("enable_analytics_objects=true");
    return url;
}

DeviceAgent::DeviceAgent(Engine* engine, const nx::sdk::IDeviceInfo* deviceInfo):
    ConsumingDeviceAgent(deviceInfo, ini().enableOutput),
    m_engine(engine),
    m_deviceId(deviceInfo->id()),
    m_streamUrl(makeStreamUrl(engine, deviceInfo))
{
}

DeviceAgent::~DeviceAgent()
{
    qDebug() << "Stopping stream for" << m_deviceId;
    stopRtspClient();
}

const std::string DeviceAgent::deviceId() const noexcept
{
    return m_deviceId;
}

const nx::utils::Url& DeviceAgent::streamUrl() const noexcept
{
    return m_streamUrl;
}

AuthData DeviceAgent::authData() const
{
    return m_engine->authData();
}

void DeviceAgent::authUpdated()
{
    if (m_streamStarted)
        setupRtspClient();
}

void DeviceAgent::pushAnalyticsEvent(AnalyticsEvent event)
{
    auto eventMetadataPacket = nx::sdk::makePtr<nx::sdk::analytics::EventMetadataPacket>();
    eventMetadataPacket->setTimestampUs(m_engine->currentSystemTime());
    eventMetadataPacket->setDurationUs(0);

    const auto eventMetadata = event.toEventMetadata();
    eventMetadataPacket->addItem(eventMetadata.get());
    pushMetadataPacket(eventMetadataPacket.releasePtr());
}

void DeviceAgent::pushMetadataToApp(QString metadata)
{
    m_engine->pushMetadataToApp(std::move(metadata));
}

std::string DeviceAgent::manifestString() const
{
    QFile file(":/manifests/device_agent_manifest.json");
    if (!file.open(QFile::ReadOnly))
        return {};
    return file.readAll().toStdString();
}

void DeviceAgent::doSetNeededMetadataTypes(
    nx::sdk::Result<void>*, const nx::sdk::analytics::IMetadataTypes*)
{
}

void DeviceAgent::getPluginSideSettings(
    nx::sdk::Result<const nx::sdk::ISettingsResponse*>* outResult) const
{
    QFile file(":/manifests/device_agent_settings.json.in");
    if (!file.open(QFile::ReadOnly))
        return;

    const auto hasAuth = !m_engine->authData().token.empty();
    const auto hasAiManager = m_engine->serverInfo()
        ? m_engine->serverInfo()->aiManagerPresent
        : false;

    QString settingsModel = file.readAll();
    settingsModel.replace("%OK_VISIBLE%", (hasAuth && hasAiManager) ? "true" : "false");
    settingsModel.replace("%AUTH_VISIBLE%", hasAuth ? "false" : "true");
    settingsModel.replace("%AI_VISIBLE%", hasAiManager ? "false" : "true");
    settingsModel.replace("%LINK%", m_engine->webAppUrl().toString());

    const auto response = new nx::sdk::SettingsResponse();
    response->setModel(settingsModel.toStdString());
    *outResult = response;
}

bool DeviceAgent::pushUncompressedVideoFrame(const nx::sdk::analytics::IUncompressedVideoFrame*)
{
    if (!std::exchange(m_streamStarted, true))
    {
        if (!m_engine->authData().token.empty())
            setupRtspClient();
    }
    return true;
}

void DeviceAgent::finalize()
{
    stopRtspClient();
    m_engine->deviceAgentAboutToBeDestroyed(deviceId());
}

void DeviceAgent::setupRtspClient()
{
    stopRtspClient();

    m_reader = std::make_unique<StreamReader>(this);
    m_reader->start();
}

void DeviceAgent::stopRtspClient()
{
    m_reader.reset();
}

} // namespace tigre::crowdpulse
