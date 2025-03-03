#include "analytics_event.h"

#include <nx/kit/json.h>

namespace tigre::crowdpulse {

bool AnalyticsEvent::isValid() const
{
    return !type.empty();
}

AnalyticsEvent AnalyticsEvent::unserialize(const std::string& jsonString)
{
    std::string error;
    const nx::kit::Json json = json.parse(jsonString, error);

    decltype(AnalyticsEvent::attributes) attributes;
    for (const auto& [key, value]: json["attributes"].object_items())
    {
        if (const auto& stringValue = value.string_value(); !stringValue.empty())
            attributes[key] = stringValue;
    }

    return AnalyticsEvent{
        .type = json["type"].string_value(),
        .caption = json["caption"].string_value(),
        .description = json["description"].string_value(),
        .attributes = std::move(attributes),
    };
}

nx::sdk::Ptr<nx::sdk::analytics::EventMetadata> AnalyticsEvent::toEventMetadata() const
{
    auto eventMetadata = nx::sdk::makePtr<nx::sdk::analytics::EventMetadata>();
    eventMetadata->setTypeId(type);
    eventMetadata->setCaption(caption);
    eventMetadata->setDescription(description);
    for (const auto& [key, value]: attributes)
        eventMetadata->addAttribute(nx::sdk::makePtr<nx::sdk::Attribute>(key, value));
    return eventMetadata;
}

} // namespace tigre::crowdpulse
