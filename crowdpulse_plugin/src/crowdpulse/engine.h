#pragma once

#include <map>
#include <optional>

#include <nx/sdk/analytics/helpers/engine.h>
#include <nx/sdk/analytics/helpers/plugin.h>
#include <nx/sdk/analytics/i_compressed_video_packet.h>
#include <nx/network/aio/timer.h>
#include <nx/network/http/http_client.h>
#include <nx/utils/async_operation_guard.h>
#include <nx/utils/lockable.h>
#include <nx/utils/std/expected.h>

#include "api/diag_event.h"
#include "request_completion_handler.h"
#include "utils.h"

namespace tigre::crowdpulse {

class DeviceAgent;
class InternalApiServer;
class Plugin;
class WebappRunner;

class Engine: public nx::sdk::analytics::Engine
{
public:
    Engine(Plugin* plugin);
    virtual ~Engine() override;

    void deviceAgentAboutToBeDestroyed(const std::string& id);
    DeviceAgent* getDeviceAgent(const std::string& id) const;
    std::vector<std::string> getDeviceAgentIds() const;

    void updateAuth(AuthData authData);
    AuthData authData() const;

    std::optional<ServerInfo> serverInfo() const;

    void pushMetadataToApp(QString metadata);
    void pushDiagEvent(DiagEvent event) const;
    Plugin* plugin() const;

    int64_t currentSystemTime() const;
    nx::utils::Url webAppUrl() const;

protected:
    virtual std::string manifestString() const override;
    virtual nx::sdk::Result<const nx::sdk::ISettingsResponse*> settingsReceived() override;
    virtual void doObtainDeviceAgent(
        nx::sdk::Result<nx::sdk::analytics::IDeviceAgent*>* outResult,
        const nx::sdk::IDeviceInfo* deviceInfo) override;
    virtual void doGetSettingsOnActiveSettingChange(
        nx::sdk::Result<const nx::sdk::IActiveSettingChangedResponse*>* outResult,
        const nx::sdk::IActiveSettingChangedAction* activeSettingChangedAction) override;

private:
    int webAppPort() const;
    void startWebApplication();

    void launchServerInfoTimer();

    void fetchServerInfo();
    void onServerInfoFetched(RequestCompletionHandler::CompletionResult result);

    using ExpectedServerInfo = nx::utils::expected<ServerInfo, std::string>;
    ExpectedServerInfo parseServerInfo(const std::string& data) const;

private:
    Plugin* const m_plugin;

    using DeviceAgents = std::map<std::string, DeviceAgent*>;
    nx::Lockable<DeviceAgents> m_deviceAgents;
    nx::Lockable<AuthData> m_authData;

    nx::network::aio::Timer m_serverInfoTimer;
    nx::utils::AsyncOperationGuard m_asyncGuard;

    std::unique_ptr<InternalApiServer> m_api;
    std::unique_ptr<WebappRunner> m_appRunner;

    std::optional<ServerInfo> m_serverInfo;
    QString m_runtimeDir;

    nx::network::http::HttpClient m_httpClient{nx::network::ssl::kAcceptAnyCertificate};
};

} // namespace tigre::crowdpulse
