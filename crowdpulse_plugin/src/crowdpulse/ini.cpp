#include "ini.h"

namespace tigre::crowdpulse {

Ini& ini()
{
    static Ini ini;
    return ini;
}

} // tigre::crowdpulse
