#pragma once

#include <optional>

#include <nx/sdk/helpers/ref_countable.h>
#include <nx/sdk/i_utility_provider.h>
#include <nx/utils/std/expected.h>

namespace tigre::crowdpulse {

class RequestCompletionHandler: public nx::sdk::RefCountable<nx::sdk::IUtilityProvider::IHttpRequestCompletionHandler>
{
public:
    using RequestResult = nx::sdk::Result<nx::sdk::IString*>;
    using CompletionResult = nx::utils::expected<std::string, std::string>;
    using Callback = std::function<void(CompletionResult)>;

    RequestCompletionHandler(Callback callback):
        m_callback(std::move(callback))
    {
    }

    virtual void execute(RequestResult result) override
    {
        if (!result.isOk())
        {
            std::string error = "Totally unknown error";
            if (result.error().errorMessage())
            {
                error = result.error().errorMessage()->str();
                result.error().errorMessage()->releaseRef();
            }
            m_callback(nx::utils::unexpected(std::move(error)));
        }

        std::string response = result.value()->str();
        result.value()->releaseRef();
        m_callback(std::move(response));
    }

private:
    Callback m_callback;
};


} // namespace tigre::crowdpulse
