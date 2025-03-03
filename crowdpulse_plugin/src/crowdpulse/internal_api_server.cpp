#include "internal_api_server.h"
#include "device_agent.h"
#include "engine.h"

#include <nx/kit/json.h>
#include <nx/network/http/buffer_source.h>

#include "api/analytics_event.h"
#include "api/diag_event.h"

namespace tigre::crowdpulse {

using namespace nx::network;

InternalApiServer::InternalApiServer(Engine* engine):
    m_engine(engine),
    m_messageDispatcher(std::make_unique<Dispatcher>()),
    m_server(std::make_unique<http::HttpStreamSocketServer>(m_messageDispatcher.get()))
{
    initialize();
}

InternalApiServer::~InternalApiServer()
{
    m_server->pleaseStopSync();
}

int InternalApiServer::port() const
{
    return m_server->address().port;
}

void InternalApiServer::initialize()
{
    if (!m_server->bind(SocketAddress(HostAddress::localhost, kAnyPort)))
        throw std::runtime_error("Unable to start command server: bind failed");
    if (!m_server->listen())
        throw std::runtime_error("Unable to start command server: listen failed");

    qDebug() << "Listening at port" << port();

    auto reg = [this](http::Method method, std::string path, auto apiFunc)
    {
        m_messageDispatcher->registerRequestProcessorFunc(
            method,
            path,
            [this, apiFunc](http::RequestContext context, http::RequestProcessedHandler handler)
            {
                const ApiResult apiResult = (this->*(apiFunc))(std::move(context));

                http::RequestResult result(apiResult.statusCode);
                if (apiResult.response)
                {
                    result.body = std::make_unique<http::BufferSource>(
                        http::header::ContentType::kJson.toString(),
                        *apiResult.response);
                }
                handler(std::move(result));
            });
    };

    reg(http::Method::post, "/plugin/sendDiagEvent", &InternalApiServer::handlePluginSendDiagEvent);
    reg(http::Method::post, "/plugin/token", &InternalApiServer::handleToken);
    reg(http::Method::post, "/device/{deviceId}/sendEvent", &InternalApiServer::handleDeviceSendEvent);
    reg(http::Method::get, "/device/listActive", &InternalApiServer::handleListDevices);
}

DeviceAgent* InternalApiServer::getDeviceAgent(const nx::network::http::RequestContext& context)
{
    return m_engine->getDeviceAgent(context.requestPathParams.getByName("deviceId"));
}

InternalApiServer::ApiResult InternalApiServer::handlePluginSendDiagEvent(http::RequestContext context)
{
    DiagEvent event = DiagEvent::unserialize(context.request.messageBody.toStdString());
    if (!event.isValid())
        return { .statusCode = http::StatusCode::badRequest };

    m_engine->pushDiagEvent(std::move(event));
    return { .statusCode = http::StatusCode::ok };
}

InternalApiServer::ApiResult InternalApiServer::handleDeviceSendEvent(http::RequestContext context)
{
    const auto agent = getDeviceAgent(context);
    if (!agent)
        return { .statusCode = http::StatusCode::notFound };

    AnalyticsEvent event = AnalyticsEvent::unserialize(context.request.messageBody.toStdString());
    if (!event.isValid())
        return { .statusCode = http::StatusCode::badRequest };

    agent->pushAnalyticsEvent(std::move(event));
    return { .statusCode = http::StatusCode::ok };
}

InternalApiServer::ApiResult InternalApiServer::handleListDevices(http::RequestContext)
{
    nx::kit::Json::array result;
    for (std::string& id: m_engine->getDeviceAgentIds())
        result.push_back(nx::kit::Json(std::move(id)));

    return {
        .statusCode = http::StatusCode::ok,
        .response = nx::kit::Json(result).dump()
    };
}

InternalApiServer::ApiResult InternalApiServer::handleToken(nx::network::http::RequestContext context)
{
    std::string jsonString = context.request.messageBody.toStdString();
    std::string error;
    const nx::kit::Json json = json.parse(jsonString, error);
    if (!json.is_object())
        return { .statusCode = http::StatusCode::badRequest };

    auto data = AuthData{
        .user = json["user"].string_value(),
        .token = json["token"].string_value()
    };
    if (!data.isValid())
        return { .statusCode = http::StatusCode::unprocessableEntity };

    m_engine->updateAuth(std::move(data));
    return { .statusCode = http::StatusCode::ok };
}


} // namespace tigre::crowdpulse

