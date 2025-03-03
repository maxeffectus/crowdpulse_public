#include "webapp_runner.h"

#include "ini.h"

#include <chrono>
#include <QtCore/QDir>
#include <QtCore/QScopedValueRollback>
#include <QtCore/QTimer>

namespace tigre::crowdpulse {

RunnerPrivate::RunnerPrivate(WebappParameters parameters, OnStartCallback onStarted):
    m_parameters(std::move(parameters)),
    m_autoRestartBak(m_parameters.autoRestart),
    m_startCallback(std::move(onStarted))
{
}

void RunnerPrivate::start()
{
    const auto arguments = makeArguments();
    qDebug() << "Starting" << ini().webAppExec << arguments << "in working Directory:" << m_parameters.path;

    m_parameters.autoRestart = m_autoRestartBak;
    if (!m_process)
    {
        m_process = new QProcess(this);
        connect(m_process, &QProcess::finished, this, &RunnerPrivate::onFinished, Qt::QueuedConnection);
        connect(m_process, &QProcess::readyReadStandardOutput, m_process,
                [this](){ qDebug() << "[webapp stdout]" << m_process->readAllStandardOutput(); });
        connect(m_process, &QProcess::readyReadStandardError, m_process,
                [this](){ qDebug() << "[webapp stderr]" << m_process->readAllStandardError(); });
    }

    m_process->setWorkingDirectory(m_parameters.path);
    m_process->start(ini().webAppExec, arguments);

    const bool started = m_process->waitForStarted();
    m_startCallback(started);
}

void RunnerPrivate::stop()
{
    if (!m_process)
        return;

    qDebug() << "Stopping Web application";
    m_parameters.autoRestart = false;

    m_process->terminate();
    if (!m_process->waitForFinished())
    {
        m_process->kill();
        m_process->waitForFinished();
    }
}

void RunnerPrivate::restart()
{
    qDebug() << "Restarting Web application";

    stop();
    // Start via queue to get onFinished executed as expected
    QMetaObject::invokeMethod(this, &RunnerPrivate::start, Qt::QueuedConnection);
}

void RunnerPrivate::onFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    qDebug() << "Webapp finished with code" << exitCode << exitStatus;

    if (m_parameters.autoRestart)
    {
        const int delay = ini().restartDelay;
        qDebug() << "Starting webapp after delay" << delay << "seconds";
        QTimer::singleShot(std::chrono::seconds(delay), this, &RunnerPrivate::start);
    }
}

QStringList RunnerPrivate::makeArguments() const
{
    QStringList arguments;
    arguments << "-m" << ini().webAppName;
    arguments << "--web-app-port" << QString::number(m_parameters.httpPort);
    arguments << "--crowdpulse-plugin-port" << QString::number(m_parameters.apiPort);
    arguments << "--mediaserver-port" << QString::number(m_parameters.mediaserverPort);
    return arguments;
}

WebappRunner::WebappRunner()
{
}

WebappRunner::~WebappRunner()
{
    forceStopSync();
}

void WebappRunner::start(WebappParameters parameters, OnStartCallback onStarted)
{
    forceStopSync();

    auto runner = new RunnerPrivate(std::move(parameters), std::move(onStarted));
    runner->moveToThread(&m_thread);
    connect(this, &WebappRunner::_start, runner, &RunnerPrivate::start);
    connect(this, &WebappRunner::_stop, runner, &RunnerPrivate::stop);
    connect(this, &WebappRunner::_stopSync, runner, &RunnerPrivate::stop, Qt::BlockingQueuedConnection);
    connect(this, &WebappRunner::_restart, runner, &RunnerPrivate::restart);
    connect(&m_thread, &QThread::finished, runner, &QObject::deleteLater);
    m_thread.start();

    Q_EMIT _start();
}

void WebappRunner::stop()
{
    Q_EMIT _stop();
}

void WebappRunner::restart()
{
    Q_EMIT _restart();
}

void WebappRunner::forceStopSync()
{
    if (m_thread.isRunning())
    {
        Q_EMIT _stopSync();
        m_thread.quit();
        m_thread.wait();
    }
}

} // namespace tigre::crowdpulse
