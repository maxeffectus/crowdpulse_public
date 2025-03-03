#include "utils.h"

#include <QtCore/QDir>
#include <QtCore/QDirIterator>

#include <nx/kit/ini_config.h>

namespace tigre::crowdpulse {

bool unpackResources(const QString& resourceDirectory, const QString& outputDirectory)
{
    // Ensure the output directory exists
    QDir tempDir(outputDirectory);
    if (!tempDir.exists() && !tempDir.mkpath("."))
    {
        qWarning() << "Failed to create output directory:" << outputDirectory;
        return false;
    }

    // Iterate over all files and directories in the specified QRC directory
    QDirIterator it(resourceDirectory, QDirIterator::Subdirectories);
    while (it.hasNext())
    {
        QString resourcePath = it.next();
        QFileInfo fileInfo(resourcePath);

        // Create the corresponding path in the output directory
        QString relativePath = resourcePath.mid(resourceDirectory.length());
        QString outputFilePath = tempDir.filePath(relativePath);

        if (fileInfo.isDir())
        {
            qDebug() << "Creating dir" << outputFilePath;
            // If it's a directory, create it in the output folder
            if (!QDir().mkpath(outputFilePath))
            {
                qWarning() << "Failed to create directory:" << outputFilePath;
                return false;
            }
        }
        else if (fileInfo.isFile())
        {
            qDebug() << "Copying" << resourcePath << "to" << outputFilePath;

            // If it's a file, copy it to the output folder
            QFile resourceFile(resourcePath);

            // Ensure the subdirectory structure exists for files
            QDir().mkpath(QFileInfo(outputFilePath).absolutePath());
            // Delete old version of the file
            QFile::remove(outputFilePath);

            if (!resourceFile.copy(outputFilePath))
            {
                qWarning() << "Failed to copy file" << resourcePath
                           << "to" << outputFilePath
                           << "Error:" << resourceFile.errorString();
                return false;
            }
        }
    }
    return true;
}

QString runtimeDataDir()
{
    // Assume that folder with ini files is in writable location.
    QDir dir(nx::kit::IniConfig::iniFilesDir());
    dir.mkpath("../crowdpulse/");
    dir.cd("../crowdpulse/");
    return dir.absolutePath();
}

std::map<std::string, std::string> toStdMap(
    const nx::sdk::Ptr<const nx::sdk::IStringMap>& sdkMap)
{
    std::map<std::string, std::string> result;
    if (sdkMap)
    {
        for (int i = 0; i < sdkMap->count(); ++i)
            result[sdkMap->key(i)] = sdkMap->value(i);
    }
    return result;
}

bool toBool(std::string_view value)
{
    return value == "true";
}

} // namespace tigre::crowdpulse

