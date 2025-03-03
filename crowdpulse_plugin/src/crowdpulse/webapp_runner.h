#pragma once

#include <QtCore/QObject>
#include <QtCore/QProcess>
#include <QtCore/QThread>

namespace tigre::crowdpulse {

struct WebappParameters
{
    QString path;
    int httpPort;
    int apiPort;
    int mediaserverPort;
    bool autoRestart = true;
};

using OnStartCallback = std::function<void(bool)>;

class RunnerPrivate: public QObject
{
    Q_OBJECT

public:
    RunnerPrivate(WebappParameters parameters, OnStartCallback onStarted);

    void start();
    void stop();
    void restart();

private:
    void onFinished(int exitCode, QProcess::ExitStatus exitStatus);
    QStringList makeArguments() const;

private:
    QProcess* m_process = nullptr;
    WebappParameters m_parameters;
    bool m_autoRestartBak;
    OnStartCallback m_startCallback;
};

class WebappRunner: public QObject
{
    Q_OBJECT

public:
    WebappRunner();
    ~WebappRunner();

    void start(WebappParameters parameters, OnStartCallback onStarted);
    void stop();
    void restart();

Q_SIGNALS:
    void _start();
    void _stop();
    void _stopSync();
    void _restart();

private:
    void forceStopSync();

private:
    QThread m_thread;
};

} // namespace tigre::crowdpulse
