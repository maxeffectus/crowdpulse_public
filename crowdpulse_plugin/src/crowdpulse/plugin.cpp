#include "plugin.h"

#include "engine.h"

#include <QtCore/QFile>

#include <nx/network/http/http_types.h>
#include <nx/sdk/helpers/error.h>

namespace tigre::crowdpulse {

using namespace nx::sdk;
using namespace nx::sdk::analytics;

void Plugin::doMediaserverGetRequest(const std::string& path, RequestResultCallback callback)
{
    doMediaserverRequest(path, {}, nx::network::http::Method::get, std::move(callback));
}

void Plugin::doMediaserverPostRequest(
    const std::string& path, const std::string& body, RequestResultCallback callback)
{
    doMediaserverRequest(path, body, nx::network::http::Method::post, std::move(callback));
}

void Plugin::doMediaserverRequest(
    const std::string& path,
    const std::string& body,
    std::string_view method,
    RequestResultCallback callback)
{
    auto handlerCallback = [callback = std::move(callback)](auto result)
    {
        if (!result)
            callback(std::move(result));

        constexpr std::string_view delimeter{"\r\n\r\n"};
        const auto idx = result.value().find(delimeter);
        callback(result.value().substr(idx + delimeter.size()));
    };

    auto handler = nx::sdk::makePtr<RequestCompletionHandler>(std::move(handlerCallback));
    utilityProvider()->sendHttpRequest(
        nx::sdk::IUtilityProvider::HttpDomainName::vms,
        path.c_str(),
        method.data(),
        nx::network::http::header::ContentType::kJson.toString().c_str(),
        body.c_str(),
        handler);
}

Result<IEngine*> Plugin::doObtainEngine()
{
    try
    {
        return new Engine(this);
    }
    catch (const std::exception& e)
    {
        return nx::sdk::error(nx::sdk::ErrorCode::internalError, e.what());
    }

    return nx::sdk::error(nx::sdk::ErrorCode::otherError, "Should never get here");
}

std::string Plugin::manifestString() const
{
    QFile file(":/manifests/plugin_manifest.json");
    if (!file.open(QFile::ReadOnly))
        return {};
    return file.readAll().toStdString();
}

extern "C" NX_PLUGIN_API nx::sdk::IPlugin* createNxPlugin()
{
    // The object will be freed when the Server calls releaseRef().
    return new Plugin();
}

} // namespace tigre::crowdpulse
