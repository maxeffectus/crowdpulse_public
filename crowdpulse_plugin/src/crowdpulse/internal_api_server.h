#pragma once

#include <optional>

#include <nx/network/http/http_types.h>
#include <nx/network/http/server/http_stream_socket_server.h>
#include <nx/network/http/server/rest/http_server_rest_path_matcher.h>

namespace tigre::crowdpulse {

class Engine;
class DeviceAgent;

class InternalApiServer
{
public:
    explicit InternalApiServer(Engine* engine);
    ~InternalApiServer();

    int port() const;

private:
    void initialize();
    DeviceAgent* getDeviceAgent(const nx::network::http::RequestContext& context);

// API Handlers
private:
    struct ApiResult
    {
        nx::network::http::StatusCode::Value statusCode = nx::network::http::StatusCode::ok;
        std::optional<std::string> response = std::nullopt;
    };

    ApiResult handlePluginSendDiagEvent(nx::network::http::RequestContext context);
    ApiResult handleDeviceSendEvent(nx::network::http::RequestContext context);
    ApiResult handleListDevices(nx::network::http::RequestContext context);
    ApiResult handleToken(nx::network::http::RequestContext context);

private:
    Engine* const m_engine;

    using Dispatcher =
        nx::network::http::BasicMessageDispatcher<nx::network::http::server::rest::PathMatcher>;
    std::unique_ptr<Dispatcher> m_messageDispatcher;
    std::unique_ptr<nx::network::http::HttpStreamSocketServer> m_server;
};

} // tigre::crowdpulse
