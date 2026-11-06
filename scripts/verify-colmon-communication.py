import json
import ctypes
from ctypes import wintypes
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.process_manager import ManagedProcessRegistry
from backend.user_config import UserConfigStore
from plugins.colmon.backend import ColmonPlugin
from plugins.colmon.native_host import TaskbarWindowController

directory = project_root / 'artifacts' / 'communication-verification' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
directory.mkdir(parents=True)
plugin_root = project_root / 'target/Colpilot/plugins/colmon'


def verify_file_readers():
    runtime_root = directory / 'reader-runtime'
    shutil.copytree(plugin_root / 'native/publish', runtime_root / 'native/publish')
    registry = ManagedProcessRegistry()
    plugin = ColmonPlugin(runtime_root, UserConfigStore(runtime_root / 'config.ini'), registry)
    try:
        plugin.start()
        deadline = time.monotonic() + 20
        while True:
            status = plugin.status(True)
            if all(window['status'] == 'ready' for window in status['windows']):
                break
            assert time.monotonic() < deadline, status
            time.sleep(0.1)
        state_path = plugin.controller.windows['codex-weekly'].state_path
        previous_modified = state_path.stat().st_mtime_ns
        # 真实读取句柄保持打开，状态接口同时连续读取更新后的 JSON。
        with state_path.open('rb'):
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                status = plugin.status(True)
                assert status['runtime']['status'] == 'running', status
                assert all(window['status'] == 'ready' for window in status['windows']), status
                time.sleep(0.02)
            assert state_path.stat().st_mtime_ns > previous_modified
        print('真实读取句柄持续打开期间状态更新与并发状态查询：通过')
    finally:
        plugin.stop()
        registry.stop_all()


def verify_file_failure():
    registry = ManagedProcessRegistry()
    controller = TaskbarWindowController(plugin_root, directory / 'state', 60, registry)
    try:
        controller.start()
        process = controller.helper_process
        state_path = controller.windows['codex-weekly'].state_path
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                         ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        # 使用真实 Windows 句柄拒绝写入与删除共享。
        handle = kernel32.CreateFileW(str(state_path), 0x80000000, 1, None, 3, 0, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            deadline = time.monotonic() + 8
            while controller.last_error is None and time.monotonic() < deadline:
                time.sleep(0.05)
            assert controller.last_error and '保存窗口状态失败' in controller.last_error, controller.last_error
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                raise AssertionError('状态文件写入失败后窗口宿主仍在运行') from None
            assert controller.stop_event.is_set()
        finally:
            kernel32.CloseHandle(handle)
        print('真实文件占用触发错误后窗口宿主及时终止：通过')
    finally:
        controller.stop()
        registry.stop_all()


def verify_output_pressure():
    log_directory = directory / 'pressure'
    process = subprocess.Popen(
        [str(plugin_root / 'native/publish/ColpilotColmonWindows.exe')],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, 'COLMON_LOG_DIRECTORY': str(log_directory),
             'DOTNET_BUNDLE_EXTRACT_BASE_DIR': str(directory / 'runtime')},
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        # 保持真实管道连接并停止读取，触发操作系统管道容量限制。
        try:
            process.wait(timeout=18)
        except subprocess.TimeoutExpired:
            raise AssertionError('宿主输出通信超时后仍在运行') from None
        output = '\n'.join(path.read_text(encoding='utf-8-sig') for path in log_directory.glob('native-*.log'))
        assert '宿主输出通信超时' in output, output
        assert '窗口宿主响应异常' not in output, output
        assert process.returncode != 0
        print('真实管道停止读取期间 UI 保持响应并及时终止宿主：通过')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


verify_file_readers()
verify_file_failure()
verify_output_pressure()
