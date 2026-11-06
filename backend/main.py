import argparse
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from functools import partial
from importlib import import_module
from pathlib import Path
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.user_config import UserConfigStore
from backend.process_manager import ManagedProcessRegistry
from backend.plugin_manager import MAX_PLUGIN_ARCHIVE_BYTES, PluginRepositoryManager
from backend.plugin_runtime import PluginNotReadyError, PluginRuntime, PluginWorker
from backend.settings import read_appearance, theme_presets, update_appearance
from backend.diagnostics import configure_logging


configure_logging(PROJECT_ROOT / 'data' / 'logs')
logger = logging.getLogger(__name__)


BACKEND_PORT = 37651
APP_VERSION = '0.1.0'
PLUGIN_ROOT = PROJECT_ROOT / 'plugins'
TOOL_TYPES = {'continuous', 'on_demand'}


class PluginDescriptor(BaseModel):
    id: str
    name: str
    description: str
    icon: str | None = None
    category: str
    color: str
    tool_type: Literal['continuous', 'on_demand']
    enabled: bool
    view: str = 'generic'
    runtime: PluginRuntime | None = None
    backend_ready: bool = False


class PluginToggleRequest(BaseModel):
    enabled: bool


class PluginOrderRequest(BaseModel):
    order: list[str]


class PluginDownloadRequest(BaseModel):
    repository_url: str


class PluginUpdateIntervalRequest(BaseModel):
    minutes: int


class PluginRunRequest(BaseModel):
    arguments: dict[str, object] = Field(default_factory=dict)


class CommandRequest(BaseModel):
    command: Literal['exit']


def load_plugin_manifests() -> tuple[list[dict[str, object]], dict[str, Path]]:
    manifests: list[dict[str, object]] = []
    plugin_roots: dict[str, Path] = {}
    for manifest_path in sorted(PLUGIN_ROOT.glob('*/manifest.json')):
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if not isinstance(manifest, dict):
            raise ValueError(f'Plugin manifest must contain an object: {manifest_path}')
        plugin_id = manifest.get('id')
        if not isinstance(plugin_id, str) or not plugin_id:
            raise ValueError(f'Plugin manifest id is invalid: {manifest_path}')
        if plugin_id in plugin_roots:
            raise ValueError(f'Duplicate plugin id: {plugin_id}')
        tool_type = manifest.get('tool_type')
        if not isinstance(tool_type, str) or tool_type not in TOOL_TYPES:
            raise ValueError(f'Plugin tool_type is invalid: {manifest_path}')
        icon = manifest.get('icon')
        if icon is not None and not isinstance(icon, str):
            raise ValueError(f'Plugin icon is invalid: {manifest_path}')
        plugin_roots[plugin_id] = manifest_path.parent
        manifests.append(manifest)
    return manifests, plugin_roots


def load_plugin_handler(
    manifest: dict[str, object],
    plugin_root: Path,
    program_config_store: UserConfigStore,
    process_registry: ManagedProcessRegistry,
) -> Any:
    plugin_id = manifest['id']
    backend_entry = manifest.get('backend')
    if backend_entry is None:
        raise ValueError(f'Plugin backend entry is missing: {plugin_id}')
    if not isinstance(plugin_id, str) or not isinstance(backend_entry, str):
        raise ValueError(f'Plugin backend entry is invalid: {plugin_id}')
    module_name, separator, factory_name = backend_entry.partition(':')
    if not separator or not module_name or not factory_name:
        raise ValueError(f'Plugin backend entry must use module:factory format: {plugin_id}')
    module = import_module(module_name)
    factory = getattr(module, factory_name)
    plugin_config_store = UserConfigStore(plugin_root / 'config.ini')
    plugin_config_store.migrate_section_from(program_config_store, plugin_id)
    handler = factory(plugin_root, plugin_config_store, process_registry)
    required_methods = (
        ('start', 'stop', 'runtime_status')
        if manifest['tool_type'] == 'continuous'
        else ('run',)
    )
    missing_methods = [
        method_name
        for method_name in required_methods
        if not callable(getattr(handler, method_name, None))
    ]
    if missing_methods:
        raise ValueError(
            f'Plugin handler is missing methods for {plugin_id}: '
            f'{", ".join(missing_methods)}'
        )
    return handler


PLUGIN_DEFINITIONS, PLUGIN_ROOTS = load_plugin_manifests()
PLUGIN_WORKERS: dict[str, PluginWorker] = {}
PROGRAM_CONFIG_STORE: UserConfigStore | None = None
PLUGIN_REPOSITORY_MANAGER: PluginRepositoryManager | None = None
PLUGIN_PROCESS_REGISTRY = ManagedProcessRegistry()
enabled_plugins = {plugin['id']: True for plugin in PLUGIN_DEFINITIONS}
plugin_order = [plugin['id'] for plugin in PLUGIN_DEFINITIONS]


def configure_runtime(config_path: Path) -> None:
    global PLUGIN_WORKERS, PROGRAM_CONFIG_STORE, PLUGIN_REPOSITORY_MANAGER
    resolved_path = config_path.expanduser().resolve()
    if PROGRAM_CONFIG_STORE is not None and PROGRAM_CONFIG_STORE.path == resolved_path:
        return
    if PLUGIN_REPOSITORY_MANAGER is not None:
        PLUGIN_REPOSITORY_MANAGER.stop()
    PROGRAM_CONFIG_STORE = UserConfigStore(resolved_path)
    PLUGIN_REPOSITORY_MANAGER = PluginRepositoryManager(PLUGIN_ROOT, PROGRAM_CONFIG_STORE)
    enabled_plugins.clear()
    enabled_plugins.update(_read_enabled_plugins(PROGRAM_CONFIG_STORE))
    plugin_order.clear()
    plugin_order.extend(_read_plugin_order(PROGRAM_CONFIG_STORE))
    PLUGIN_WORKERS = {
        plugin['id']: PluginWorker(
            plugin['id'],
            partial(
                load_plugin_handler,
                plugin,
                PLUGIN_ROOTS[plugin['id']],
                PROGRAM_CONFIG_STORE,
                PLUGIN_PROCESS_REGISTRY,
            ),
            continuous=plugin['tool_type'] == 'continuous',
            enabled=enabled_plugins[plugin['id']],
        )
        for plugin in PLUGIN_DEFINITIONS
    }


def _read_enabled_plugins(config_store: UserConfigStore) -> dict[str, bool]:
    raw_settings = config_store.read_section('colpilot')
    supported_keys = {
        'plugin_order',
        *(f'enabled_{plugin["id"]}' for plugin in PLUGIN_DEFINITIONS),
    }
    unknown_keys = sorted(set(raw_settings) - supported_keys)
    if unknown_keys:
        raise ValueError(f'unsupported saved settings: {", ".join(unknown_keys)}')

    enabled: dict[str, bool] = {}
    for plugin in PLUGIN_DEFINITIONS:
        plugin_id = plugin['id']
        key = f'enabled_{plugin_id}'
        raw_value = raw_settings.get(key)
        if raw_value is None:
            enabled[plugin_id] = True
            continue
        normalised = raw_value.strip().lower()
        if normalised in {'true', '1', 'yes', 'on'}:
            enabled[plugin_id] = True
        elif normalised in {'false', '0', 'no', 'off'}:
            enabled[plugin_id] = False
        else:
            raise ValueError(f'{key} must be a boolean')
    return enabled


def _read_plugin_order(config_store: UserConfigStore) -> list[str]:
    default_order = [plugin['id'] for plugin in PLUGIN_DEFINITIONS]
    raw_order = config_store.read_section('colpilot').get('plugin_order')
    if raw_order is None:
        return default_order

    saved_order = [plugin_id.strip() for plugin_id in raw_order.split(',')]
    if any(not plugin_id for plugin_id in saved_order):
        raise ValueError('plugin_order contains an empty plugin id')
    if len(saved_order) != len(set(saved_order)):
        raise ValueError('plugin_order contains duplicate plugin ids')

    unknown_ids = sorted(set(saved_order) - set(default_order))
    if unknown_ids:
        raise ValueError(f'plugin_order contains unknown plugin ids: {", ".join(unknown_ids)}')

    return saved_order + [
        plugin_id
        for plugin_id in default_order
        if plugin_id not in saved_order
    ]


def _validate_plugin_order(order: list[str]) -> list[str]:
    available_ids = {plugin['id'] for plugin in PLUGIN_DEFINITIONS}
    if len(order) != len(available_ids):
        raise ValueError('plugin order must contain every plugin exactly once')
    if any(not plugin_id for plugin_id in order):
        raise ValueError('plugin order contains an empty plugin id')
    if len(order) != len(set(order)):
        raise ValueError('plugin order contains duplicate plugin ids')
    unknown_ids = sorted(set(order) - available_ids)
    if unknown_ids:
        raise ValueError(f'plugin order contains unknown plugin ids: {", ".join(unknown_ids)}')
    return order


configure_runtime(PROJECT_ROOT / 'config.ini')


def stop_plugin_handlers() -> None:
    workers = list(PLUGIN_WORKERS.values())
    for worker in workers:
        worker.close()
    deadline = time.monotonic() + 2.0
    try:
        for worker in workers:
            worker.join(deadline - time.monotonic())
    finally:
        PLUGIN_PROCESS_REGISTRY.stop_all()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info('后端启动 plugins=%s', list(PLUGIN_WORKERS))
    try:
        get_plugin_repository_manager().start()
        for worker in PLUGIN_WORKERS.values():
            worker.start()
        yield
    finally:
        logger.info('后端开始关闭')
        try:
            get_plugin_repository_manager().stop()
        finally:
            stop_plugin_handlers()
            logger.info('后端关闭完成')


app = FastAPI(
    title='Colpilot Backend',
    version=APP_VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://127.0.0.1:1420',
        'http://localhost:1420',
        'tauri://localhost',
        'http://tauri.localhost',
        'https://tauri.localhost',
    ],
    allow_credentials=False,
    allow_private_network=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type'],
)


@app.middleware('http')
async def log_requests(request: Request, call_next):
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception('请求处理失败 method=%s path=%s', request.method, request.url.path)
        raise
    elapsed = time.monotonic() - started
    if response.status_code >= 500 or elapsed > 2:
        logger.log(
            logging.ERROR if response.status_code >= 500 else logging.WARNING,
            '请求状态 method=%s path=%s status=%s elapsed_ms=%.1f',
            request.method, request.url.path, response.status_code, elapsed * 1000,
        )
    return response


def get_plugin_definition(plugin_id: str) -> dict[str, object]:
    plugin = next((item for item in PLUGIN_DEFINITIONS if item['id'] == plugin_id), None)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f'Unknown plugin: {plugin_id}')
    return plugin


def get_plugin_handler(plugin_id: str) -> Any:
    get_plugin_definition(plugin_id)
    try:
        return PLUGIN_WORKERS[plugin_id].get_handler()
    except PluginNotReadyError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error


def get_plugin_runtime(plugin_id: str) -> PluginRuntime | None:
    get_plugin_definition(plugin_id)
    runtime, _ = PLUGIN_WORKERS[plugin_id].snapshot()
    return runtime


def build_plugin_descriptor(plugin_id: str) -> PluginDescriptor:
    plugin = get_plugin_definition(plugin_id)
    runtime, backend_ready = PLUGIN_WORKERS[plugin_id].snapshot()
    return PluginDescriptor(
        **plugin,
        enabled=enabled_plugins[plugin_id],
        runtime=runtime,
        backend_ready=backend_ready,
    )


def get_plugin_repository_manager() -> PluginRepositoryManager:
    if PLUGIN_REPOSITORY_MANAGER is None:
        raise RuntimeError('插件管理器尚未初始化')
    return PLUGIN_REPOSITORY_MANAGER


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'colpilot-backend'}


@app.get('/api/settings')
def get_settings() -> dict[str, object]:
    if PROGRAM_CONFIG_STORE is None:
        raise RuntimeError('Program config store is not ready')
    manager = get_plugin_repository_manager()
    return {
        'appearance': read_appearance(PROGRAM_CONFIG_STORE),
        'themes': theme_presets(),
        'plugin_update_interval_minutes': manager.get_update_interval(),
        'about': {
            'author': 'Colboi',
            'version': APP_VERSION,
        },
    }


@app.post('/api/settings/appearance')
def save_appearance(settings: dict[str, object]) -> dict[str, object]:
    if PROGRAM_CONFIG_STORE is None:
        raise RuntimeError('Program config store is not ready')
    try:
        appearance = update_appearance(PROGRAM_CONFIG_STORE, settings)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {'appearance': appearance, 'themes': theme_presets()}


@app.post('/api/settings/plugin-update-interval')
def save_plugin_update_interval(request: PluginUpdateIntervalRequest) -> dict[str, int]:
    manager = get_plugin_repository_manager()
    try:
        minutes = manager.set_update_interval(request.minutes)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {'plugin_update_interval_minutes': minutes}


@app.get('/api/plugins', response_model=list[PluginDescriptor])
def list_plugins() -> list[PluginDescriptor]:
    return [build_plugin_descriptor(plugin_id) for plugin_id in plugin_order]


@app.post('/api/plugins/order', response_model=list[PluginDescriptor])
def update_plugin_order(request: PluginOrderRequest) -> list[PluginDescriptor]:
    try:
        next_order = _validate_plugin_order(request.order)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if PROGRAM_CONFIG_STORE is None:
        raise RuntimeError('Program config store is not ready')

    PROGRAM_CONFIG_STORE.update_section(
        'colpilot',
        {'plugin_order': ','.join(next_order)},
    )
    plugin_order.clear()
    plugin_order.extend(next_order)
    return list_plugins()


@app.get('/api/plugins/installed')
def list_installed_plugins() -> list[dict[str, object]]:
    return get_plugin_repository_manager().list_installed()


@app.post('/api/plugins/check-updates')
def check_plugin_updates() -> list[dict[str, object]]:
    return get_plugin_repository_manager().check_updates()


@app.post('/api/plugins/download')
def download_plugin(request: PluginDownloadRequest) -> dict[str, object]:
    try:
        result = get_plugin_repository_manager().install_from_github_url(
            request.repository_url
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        **result,
        'installed': get_plugin_repository_manager().list_installed(),
    }


@app.post('/api/plugins/import-zip')
async def import_plugin_zip(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=422, detail='插件 ZIP 文件名称不能为空')
    try:
        archive = await file.read(MAX_PLUGIN_ARCHIVE_BYTES + 1)
        if len(archive) > MAX_PLUGIN_ARCHIVE_BYTES:
            raise ValueError('插件压缩包超过 100 MB，无法安装')
        result = get_plugin_repository_manager().install_from_zip_archive(
            file.filename,
            archive,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        await file.close()
    return {
        **result,
        'installed': get_plugin_repository_manager().list_installed(),
    }


@app.get('/api/plugins/{plugin_id}/status')
def plugin_status(plugin_id: str) -> Any:
    handler = get_plugin_handler(plugin_id)
    status_method = getattr(handler, 'status', None)
    if not callable(status_method):
        raise HTTPException(
            status_code=501,
            detail=f'Plugin status interface is unavailable: {plugin_id}',
        )
    return status_method(enabled_plugins[plugin_id])


@app.post('/api/plugins/{plugin_id}/settings')
def update_plugin_settings(plugin_id: str, settings: dict[str, object]) -> Any:
    handler = get_plugin_handler(plugin_id)
    settings_method = getattr(handler, 'update_settings', None)
    if not callable(settings_method):
        raise HTTPException(
            status_code=501,
            detail=f'Plugin settings interface is unavailable: {plugin_id}',
        )
    try:
        settings_method(settings, enabled_plugins[plugin_id])
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return handler.status(enabled_plugins[plugin_id])


@app.post('/api/plugins/{plugin_id}/open-output-directory')
def open_plugin_output_directory(plugin_id: str) -> Any:
    get_plugin_definition(plugin_id)
    if not enabled_plugins[plugin_id]:
        raise HTTPException(status_code=409, detail=f'Plugin is disabled: {plugin_id}')
    handler = get_plugin_handler(plugin_id)
    open_method = getattr(handler, 'open_output_directory', None)
    if not callable(open_method):
        raise HTTPException(
            status_code=501,
            detail=f'Plugin output directory interface is unavailable: {plugin_id}',
        )
    try:
        return open_method(enabled_plugins[plugin_id])
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post('/api/plugins/{plugin_id}/toggle', response_model=PluginDescriptor)
def toggle_plugin(plugin_id: str, request: PluginToggleRequest) -> PluginDescriptor:
    get_plugin_definition(plugin_id)
    if PROGRAM_CONFIG_STORE is None:
        raise RuntimeError('Program config store is not ready')
    PROGRAM_CONFIG_STORE.update_section(
        'colpilot',
        {f'enabled_{plugin_id}': request.enabled},
    )
    enabled_plugins[plugin_id] = request.enabled
    PLUGIN_WORKERS[plugin_id].set_enabled(request.enabled)
    return build_plugin_descriptor(plugin_id)


@app.post('/api/plugins/{plugin_id}/run')
def run_plugin(plugin_id: str, request: PluginRunRequest) -> Any:
    plugin = get_plugin_definition(plugin_id)
    if plugin['tool_type'] != 'on_demand':
        raise HTTPException(
            status_code=409,
            detail=f'Continuous tool cannot be run on demand: {plugin_id}',
        )
    if not enabled_plugins[plugin_id]:
        raise HTTPException(status_code=409, detail=f'Plugin is disabled: {plugin_id}')
    handler = get_plugin_handler(plugin_id)
    run_method = getattr(handler, 'run', None)
    if not callable(run_method):
        raise HTTPException(
            status_code=501,
            detail=f'Plugin run interface is unavailable: {plugin_id}',
        )
    try:
        result = run_method(request.arguments)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {'accepted': True, 'result': result}


@app.post('/api/commands')
def execute_command(request: CommandRequest) -> dict[str, str | bool]:
    logger.info('收到程序退出请求')
    server = getattr(app.state, 'server', None)
    if server is None:
        raise RuntimeError('Backend server is not ready')
    server.should_exit = True
    return {'accepted': True, 'command': request.command}


def main() -> None:
    parser = argparse.ArgumentParser(description='Colpilot local backend')
    parser.add_argument('--port', type=int, default=BACKEND_PORT)
    parser.add_argument(
        '--config-path',
        type=Path,
        default=PROJECT_ROOT / 'config.ini',
    )
    arguments = parser.parse_args()
    configure_runtime(arguments.config_path)

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host='127.0.0.1',
            port=arguments.port,
            log_level='warning',
            log_config=None,
            access_log=False,
        )
    )
    app.state.server = server
    server.run()


if __name__ == '__main__':
    main()
