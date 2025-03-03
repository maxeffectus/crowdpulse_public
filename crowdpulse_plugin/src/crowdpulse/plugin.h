#pragma once

#include <nx/sdk/analytics/helpers/plugin.h>
#include <nx/sdk/analytics/i_engine.h>

#include "request_completion_handler.h"

namespace tigre::crowdpulse {

class Plugin: public nx::sdk::analytics::Plugin
{
public:
    // Handler will be called in some random AIO thread
    // Not guaranteed to be the callers one
    using RequestResultCallback = std::function<void(RequestCompletionHandler::CompletionResult)>;
    void doMediaserverGetRequest(const std::string& path, RequestResultCallback callback);
    void doMediaserverPostRequest(
        const std::string& path, const std::string& body,RequestResultCallback callback);

private:
    void doMediaserverRequest(
        const std::string& path,
        const std::string& body,
        std::string_view method,
        RequestResultCallback callback);

protected:
    virtual nx::sdk::Result<nx::sdk::analytics::IEngine*> doObtainEngine() override;
    virtual std::string manifestString() const override;
};

} // tigre::crowdpulse
