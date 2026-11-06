import json
import os
import queue
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path


project_root = Path(__file__).resolve().parent.parent
directory = project_root / 'artifacts' / 'native-diagnostics-verification' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
directory.mkdir(parents=True, exist_ok=True)
process = subprocess.Popen(
    [str(project_root / 'target/Colpilot/plugins/colmon/native/publish/ColpilotColmonWindows.exe')],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding='utf-8',
    env={**os.environ, 'COLMON_LOG_DIRECTORY': str(directory),
         'DOTNET_BUNDLE_EXTRACT_BASE_DIR': str(directory / 'runtime')},
    creationflags=subprocess.CREATE_NO_WINDOW,
)
messages = queue.Queue()


def read_output():
    for line in process.stdout:
        messages.put(json.loads(line))


reader = threading.Thread(target=read_output, daemon=True)
reader.start()
try:
    deadline = time.monotonic() + 15
    windows = set()
    while True:
        message = messages.get(timeout=max(0.1, deadline - time.monotonic()))
        if message['type'] == 'window' and message['attached']:
            windows.add(message['windowId'])
        if message['type'] == 'ready':
            assert message['windowCount'] == 3 and len(windows) == 3, message
            break
        assert time.monotonic() < deadline
    time.sleep(6)
    process.stdin.write(json.dumps({'type': 'diagnostics-invalid-command'}) + '\n')
    process.stdin.flush()
    process.wait(timeout=10)
    reader.join(timeout=2)
    output = '\n'.join(path.read_text(encoding='utf-8-sig') for path in directory.glob('native-*.log'))
    assert 'diagnostics-invalid-command' in output and 'InvalidOperationException' in output, output
    assert '窗口宿主退出' in output, output
    assert '窗口宿主定期检查' in output, output
    assert any(message['type'] == 'error' for message in list(messages.queue))
    print('真实窗口宿主启动、三个任务栏窗口附着、无效命令错误记录及退出验证通过')
finally:
    if process.poll() is None:
        process.kill()
        process.wait(timeout=5)
