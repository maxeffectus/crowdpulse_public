#pragma once

#include <map>
#include <string>

#include <nx/sdk/analytics/helpers/event_metadata.h>

namespace tigre::crowdpulse {

struct AnalyticsEvent
{
    std::string type;
    std::string caption;
    std::string description;
    std::map<std::string, std::string> attributes;

    bool isValid() const;
    static AnalyticsEvent unserialize(const std::string& jsonString);
    nx::sdk::Ptr<nx::sdk::analytics::EventMetadata> toEventMetadata() const;
};

} // namespace tigre::crowdpulse
