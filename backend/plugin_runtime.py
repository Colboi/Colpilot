import logging
import threading
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class PluginRuntime(BaseModel):
    status: Literal['starting', 'ready', 'running', 'stopping', 'stopped', 'error']
    detail: str
    exit_code: int | None = None


class PluginNotReadyError(RuntimeError):
    pass


class PluginWorker:
    def __init__(
        self,
        plugin_id: str,
        factory: Callable[[], Any],
        continuous: bool,
        enabled: bool,
    ) -> None:
        self.plugin_id = plugin_id
        self._factory = factory
        self._continuous = continuous
        self._enabled = enabled
        self._condition = threading.Condition()
        self._handler: Any = None
        self._revision = 0
        self._closed = False
        self._runtime = PluginRuntime(status='starting', detail='正在加载插件')
        self._thread = threading.Thread(
            target=self._run,
            name=f'plugin-{plugin_id}',
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def set_enabled(self, enabled: bool) -> None:
        with self._condition:
            if self._closed:
                raise RuntimeError(f'插件已经关闭：{self.plugin_id}')
            self._enabled = enabled
            self._revision += 1
            self._runtime = PluginRuntime(
                status='starting' if enabled else 'stopping',
                detail='正在启动插件' if enabled else '正在停止插件',
            )
            self._condition.notify_all()

    def snapshot(self) -> tuple[PluginRuntime, bool]:
        with self._condition:
            return self._runtime.model_copy(), self._handler is not None

    def get_handler(self) -> Any:
        with self._condition:
            if self._handler is None or self._runtime.status in {'starting', 'stopping'}:
                raise PluginNotReadyError(self._runtime.detail)
            return self._handler

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def join(self, timeout: float) -> None:
        if self._thread.ident is not None:
            self._thread.join(timeout=max(0.0, timeout))

    def _run(self) -> None:
        handler: Any = None
        applied_revision = -1
        failed = False
        try:
            while True:
                with self._condition:
                    if self._revision == applied_revision and not self._closed:
                        self._condition.wait(timeout=None if failed else 0.5)
                    if self._closed:
                        break
                    revision = self._revision
                    enabled = self._enabled

                if failed and revision == applied_revision:
                    continue

                # 每个插件在自己的线程中执行，错误保存在该插件的状态中。
                try:
                    if revision != applied_revision:
                        if enabled and handler is None:
                            handler = self._factory()
                            with self._condition:
                                self._handler = handler
                        if self._continuous and handler is not None:
                            if enabled:
                                handler.start()
                            else:
                                handler.stop()
                    if not enabled:
                        runtime = PluginRuntime(status='stopped', detail='插件已停用')
                    elif self._continuous:
                        runtime = PluginRuntime(**handler.runtime_status())
                    else:
                        runtime = PluginRuntime(status='ready', detail='插件已就绪')
                    failed = False
                except Exception as error:
                    logger.exception('插件 %s 执行失败', self.plugin_id)
                    runtime = PluginRuntime(
                        status='error',
                        detail=f'{type(error).__name__}: {error}',
                    )
                    failed = True

                with self._condition:
                    if revision == self._revision:
                        if runtime != self._runtime:
                            logger.log(
                                logging.ERROR if runtime.status == 'error' else logging.INFO,
                                '插件状态 plugin=%s status=%s detail=%s',
                                self.plugin_id, runtime.status, runtime.detail,
                            )
                        self._runtime = runtime
                applied_revision = revision
        finally:
            if handler is not None:
                stop_method = getattr(handler, 'stop', None)
                if callable(stop_method):
                    try:
                        stop_method()
                    except Exception:
                        logger.exception('插件 %s 停止失败', self.plugin_id)
