#pragma once

#include <map>
#include <string>
#include <string_view>

#include <QtCore/QString>

#include <network/system_helpers.h>
#include <nx/sdk/i_string_map.h>

namespace tigre::crowdpulse {

struct ServerInfo
{
    int port = helpers::kDefaultConnectionPort;
    bool aiManagerPresent = false;
};

struct AuthData
{
    std::string user;
    std::string token;

    bool isValid() const { return !user.empty() && !token.empty(); }
};

bool unpackResources(const QString& resourceDirectory, const QString& outputDirectory);
QString runtimeDataDir();

std::map<std::string, std::string> toStdMap(
    const nx::sdk::Ptr<const nx::sdk::IStringMap>& sdkMap);
bool toBool(std::string_view value);

} // namespace tigre::crowdpulse
