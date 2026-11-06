import argparse
import logging
import subprocess
import sys
import threading
from pathlib import Path
from tempfile import TemporaryDirectory


project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
from backend.diagnostics import configure_logging


def child(directory: Path, mode: str) -> None:
    configure_logging(directory)
    if mode == 'thread-error':
        def fail():
            raise RuntimeError('线程异常诊断验证')
        thread = threading.Thread(target=fail, name='diagnostics-verification')
        thread.start()
        thread.join()
        raise AssertionError('线程异常没有终止进程')
    if mode == 'exception':
        raise RuntimeError('主线程异常诊断验证')
    raise ValueError(mode)


def verify() -> None:
    directory = project_root / 'artifacts' / 'diagnostics-verification'
    directory.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=directory) as temporary:
        root = Path(temporary)
        configure_logging(root / 'rotation')
        handler = next(item for item in logging.getLogger().handlers if hasattr(item, 'maxBytes'))
        handler.maxBytes = 512
        for index in range(100):
            logging.info('日志轮换验证 index=%s', index)
        assert len(list((root / 'rotation').glob('backend.log*'))) == 11
        logging.shutdown()
        for mode in ('exception', 'thread-error'):
            output = root / mode
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), '--child', mode, '--directory', str(output)],
                capture_output=True, text=True, encoding='utf-8', timeout=15,
            )
            assert result.returncode == 1, (mode, result.returncode, result.stderr)
            content = (output / 'backend.log').read_text(encoding='utf-8')
            assert 'RuntimeError' in content and '诊断验证' in content, content
    print('日志轮换、主线程异常记录、工作线程异常记录与进程终止验证通过')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--child', choices=('exception', 'thread-error'))
    parser.add_argument('--directory', type=Path)
    arguments = parser.parse_args()
    if arguments.child:
        child(arguments.directory, arguments.child)
    else:
        verify()
