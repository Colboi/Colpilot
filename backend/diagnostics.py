import faulthandler
import logging
import logging.handlers
import os
import sys
import threading
from datetime import datetime
from pathlib import Path


fault_file = None


class LocalTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created).astimezone().isoformat(timespec='milliseconds')


def configure_logging(directory: Path) -> None:
    global fault_file
    directory.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        directory / 'backend.log', maxBytes=5 * 1024 * 1024, backupCount=10,
        encoding='utf-8',
    )
    handler.setFormatter(LocalTimeFormatter(
        '%(asctime)s %(levelname)s pid=%(process)d thread=%(threadName)s '
        '%(name)s %(message)s',
    ))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    fault_handler = logging.handlers.RotatingFileHandler(
        directory / 'python-fault.log', maxBytes=5 * 1024 * 1024,
        backupCount=3, encoding='utf-8',
    )
    if (directory / 'python-fault.log').stat().st_size >= fault_handler.maxBytes:
        fault_handler.doRollover()
    fault_file = fault_handler
    faulthandler.enable(file=fault_handler.stream, all_threads=True)

    def report_exception(exception_type, exception, traceback):
        root.critical('Python 未处理异常', exc_info=(exception_type, exception, traceback))

    def report_thread_exception(arguments):
        root.critical(
            'Python 线程异常 thread=%s', arguments.thread.name,
            exc_info=(arguments.exc_type, arguments.exc_value, arguments.exc_traceback),
        )
        # 工作线程异常终止整个后端，主程序会检测进程退出。
        logging.shutdown()
        os._exit(1)

    sys.excepthook = report_exception
    threading.excepthook = report_thread_exception
    root.info('后端日志启动 Python=%s executable=%s', sys.version, sys.executable)
