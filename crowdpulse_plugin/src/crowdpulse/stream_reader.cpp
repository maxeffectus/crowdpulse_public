#include "stream_reader.h"
#include "device_agent.h"

#include <nx/network/http/auth_tools.h>
#include <nx/network/http/custom_headers.h>
#include <nx/rtp/rtp.h>
#include <nx/utils/datetime.h>
#include <nx/utils/scope_guard.h>

namespace tigre::crowdpulse {

static const QString kCodecName = "t140";
constexpr int kPayload = 103;

ReaderThread::ReaderThread(QObject* parent, AuthData authData, nx::utils::Url streamUrl):
    QThread(parent),
    m_rtspClient(std::make_unique<QnRtspClient>(QnRtspClient::Config())),
    m_url(std::move(streamUrl))
{
    m_rtspClient->setCredentials(
        nx::network::http::Credentials{nx::network::http::BearerAuthToken{authData.token}},
        nx::network::http::header::AuthScheme::bearer);

    m_rtspClient->setAdditionAttribute(Qn::EC2_RUNTIME_GUID_HEADER_NAME, authData.token.c_str());
    m_rtspClient->setAdditionAttribute(Qn::CUSTOM_USERNAME_HEADER_NAME, authData.user.c_str());

    m_rtspClient->setAdditionalSupportedCodecs({kCodecName});

    m_rtspClient->setTransport(nx::vms::api::RtpTransportType::tcp);
    m_rtspClient->setTcpRecvBufferSize(256 * 1024);
}

void ReaderThread::run()
{
    auto guard = nx::utils::makeScopeGuard(
        [this]()
        {
            qDebug() << "Reader thread for" << m_url.toString() << "finished";
        });

    if (!openStream())
    {
        stopClient();
        return;
    }

    while (!m_stopped)
    {
        if (auto res = getNextData())
            ((StreamReader*)parent())->onObjectMetadata(std::move(*res));
    }
    stopClient();
}

void ReaderThread::stop()
{
    m_stopped = true;
}

bool ReaderThread::openStream()
{
    m_rtpData = nullptr;

    const auto openResult = m_rtspClient->open(m_url);
    qDebug() << m_url.toString() << "OPEN RESULT" << (int)openResult.errorCode << openResult.toString(nullptr);

    if (!openResult)
        return false;

    const bool playResult = m_rtspClient->play(DATETIME_NOW, DATETIME_NOW, m_rtspClient->getScale());
    qDebug() << m_url.toString() << "PLAY RESULT" << playResult;

    const auto& trackInfo = m_rtspClient->getTrackInfo();
    const auto it = std::find_if(trackInfo.begin(), trackInfo.end(),
        [](const auto& info)
        {
            return info.sdpMedia.payloadType == kPayload;
        });
    if (it != trackInfo.end())
    {
        m_rtpData = it->ioDevice.get();
        qDebug() << "Selected SDP" << it->sdpMedia.toString();
    }

    return playResult && !!m_rtpData;
}

void ReaderThread::stopClient()
{
    m_rtspClient->stop();
}

bool ReaderThread::reopen()
{
    qDebug() << "Reopening stream" << m_url.toString();
    stopClient();
    return openStream();
}

std::optional<QByteArray> ReaderThread::getNextData()
{
    std::optional<QByteArray> result;
    while(!result && !m_stopped)
    {
        if (!m_rtpData || !m_rtspClient->isOpened())
        {
            qDebug() << "Rtsp session closed, reopen rtsp session for" << m_url.toString();
            reopen();
            return result;
        }

        int blockSize = m_rtpData->read(m_buffer.data(), m_buffer.size());
        if (blockSize <= 0)
        {
            reopen();
            return result;
        }

        if (blockSize < 4)
            return result;

        char* data = m_buffer.data();
        blockSize -= 4;
        data += 4;

        const int rtpChannelNum = m_buffer[1];
        const QString codecName = m_rtspClient->getTrackCodec(rtpChannelNum).toLower();
        if (codecName == kCodecName)
        {
            blockSize -= nx::rtp::RtpHeader::kSize;
            data += nx::rtp::RtpHeader::kSize;
            result = QByteArray(data, blockSize);
        }

    }
    return result;
}

StreamReader::StreamReader(DeviceAgent* agent):
    m_agent(agent)
{
}

StreamReader::~StreamReader()
{
    forceStopSync();
}

void StreamReader::forceStopSync()
{
    qDebug() << "Reader thread force stop for" << m_agent->deviceId();
    if (auto curThread = std::exchange(m_thread, nullptr))
    {
        curThread->stop();
        curThread->quit();
        curThread->wait();
    }
}

void StreamReader::onThreadFinished()
{
    qDebug() << "Reader thread finished for" << m_agent->deviceId();
    m_thread = nullptr;
}

void StreamReader::onObjectMetadata(QString objectData)
{
    m_agent->pushMetadataToApp(std::move(objectData));
}

void StreamReader::start()
{
    forceStopSync();
    m_thread = new ReaderThread(this, m_agent->authData(), m_agent->streamUrl());
    connect(m_thread, &ReaderThread::finished, this, &StreamReader::onThreadFinished);
    connect(m_thread, &ReaderThread::finished, m_thread, &ReaderThread::deleteLater);

    qDebug() << "starting reader thread for" << m_agent->deviceId();
    m_thread->start();
}

} // namespace tigre::crowdpulse
