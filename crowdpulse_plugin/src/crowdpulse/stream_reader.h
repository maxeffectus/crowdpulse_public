#pragma once

#include <nx/streaming/rtsp_client.h>

#include <QThread>

#include "utils.h"

namespace tigre::crowdpulse {

class ReaderThread: public QThread
{
    Q_OBJECT

public:
    ReaderThread(QObject *parent, AuthData authData, nx::utils::Url streamUrl);

    void run();
    void stop();

private:
    bool openStream();
    void stopClient();
    bool reopen();

    std::optional<QByteArray> getNextData();

private:
    std::unique_ptr<QnRtspClient> m_rtspClient;
    QnRtspIoDevice* m_rtpData = nullptr;

    std::array<char, 65536> m_buffer;
    std::atomic_bool m_stopped = false;

    const nx::utils::Url m_url;
};

class DeviceAgent;

class StreamReader: public QObject
{
    Q_OBJECT

public:
    explicit StreamReader(DeviceAgent* agent);
    ~StreamReader();

    void start();
    void onObjectMetadata(QString objectData);

private:
    void forceStopSync();
    void onThreadFinished();

private:
    DeviceAgent* const m_agent;
    ReaderThread* m_thread = nullptr;
};

} // namespace tigre::crowdpulse
