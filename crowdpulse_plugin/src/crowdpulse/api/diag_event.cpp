#include "diag_event.h"

#include <nx/kit/json.h>

namespace tigre::crowdpulse {

DiagEvent::Level toLevel(const std::string& value)
{
    if (value == "error")
        return DiagEvent::Level::error;
    if (value == "warning")
        return DiagEvent::Level::warning;
    return DiagEvent::Level::info;
}

bool DiagEvent::isValid() const
{
    return !caption.empty() && !description.empty();
}

DiagEvent DiagEvent::unserialize(const std::string& jsonString)
{
    std::string error;
    const nx::kit::Json json = json.parse(jsonString, error);

    return DiagEvent{
        .level = toLevel(json["error"].string_value()),
        .caption = json["caption"].string_value(),
        .description = json["description"].string_value(),
    };
}

} // namespace tigre::crowdpulse
