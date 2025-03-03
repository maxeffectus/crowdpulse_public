#pragma once

#include <nx/kit/ini_config.h>

namespace tigre::crowdpulse {

struct Ini: public nx::kit::IniConfig
{
    Ini(): IniConfig("crowdpulse_plugin.ini") { reload(); }

    NX_INI_FLAG(false, enableOutput, "Enables plugin output to console and logs");
    NX_INI_FLAG(false, disableUnpack, "Debug: Disables Web Application unpaking upon startup");
    NX_INI_STRING("python3", webAppExec, "Debug: Web Application executable");
    NX_INI_STRING("flaskr", webAppName, "Debug: Web Application name");
    NX_INI_INT(1, restartDelay, "Webapp restart delay in seconds");
};

Ini& ini();

} // namespace tigre::crowdpulse
