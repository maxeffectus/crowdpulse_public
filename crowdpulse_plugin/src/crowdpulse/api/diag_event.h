#pragma once

#include <string>
#include <nx/sdk/i_plugin_diagnostic_event.h>

namespace tigre::crowdpulse {

struct DiagEvent
{
    using Level = nx::sdk::IPluginDiagnosticEvent::Level;
    Level level = Level::info;
    std::string caption;
    std::string description;

    bool isValid() const;
    static DiagEvent unserialize(const std::string& jsonString);
};

} // namespace tigre::crowdpulse
