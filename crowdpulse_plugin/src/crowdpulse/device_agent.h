#pragma once

#include <array>
#include <memory>
#include <QThread>

#include <nx/sdk/analytics/helpers/consuming_device_agent.h>
#include <nx/utils/url.h>

#include "api/analytics_event.h"
#include "utils.h"

namespace tigre::crowdpulse {

class Engine;
class StreamReader;

class DeviceAgent: public nx::sdk::analytics::ConsumingDeviceAgent
{
public:
    DeviceAgent(Engine* engine, const nx::sdk::IDeviceInfo* deviceInfo);
    virtual ~DeviceAgent() override;

    const std::string deviceId() const noexcept;
    const nx::utils::Url& streamUrl() const noexcept;
    AuthData authData() const;

    void authUpdated();

    void pushAnalyticsEvent(AnalyticsEvent event);
    void pushMetadataToApp(QString metadata);

protected:
    virtual std::string manifestString() const override;

    virtual void doSetNeededMetadataTypes(
        nx::sdk::Result<void>*, const nx::sdk::analytics::IMetadataTypes*) override;

    virtual void getPluginSideSettings(
        nx::sdk::Result<const nx::sdk::ISettingsResponse*>* outResult) const override;

    virtual bool pushUncompressedVideoFrame(
        const nx::sdk::analytics::IUncompressedVideoFrame*) override;

    virtual void finalize() override;

private:
    void setupRtspClient();
    void stopRtspClient();

private:
    Engine* const m_engine;
    const std::string m_deviceId;
    const nx::utils::Url m_streamUrl;
    bool m_streamStarted = false;

    std::unique_ptr<StreamReader> m_reader;
};

} // namespace tigre::crowdpulse
