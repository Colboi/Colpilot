# Feature Requests

Capabilities requested by the user.

---

## [FEAT-20261015-003] plugin_local_config_files

**Logged**: 2026-10-15T21:20:00+08:00
**Priority**: high
**Status**: resolved
**Area**: config

### Requested Capability
将各插件的配置文件保存到对应插件目录，程序目录只保留程序级配置。

### User Context
绝大部分配置项属于具体插件，配置文件需要跟随插件目录管理，并且 portable 构建不能携带用户配置。

### Suggested Implementation
为每个插件创建独立的 `config.ini`，继续使用插件配置节；程序级 `config.ini` 只保存插件启用状态。启动时迁移旧版程序级插件配置和旧 JSON 配置，构建复制阶段过滤所有插件配置文件。

### Metadata
- Frequency: correction
- Related Features: central_personal_config_ini, packaged_client_output
- Tags: config, plugin, ini, migration, portable

### Resolution
- **Resolved**: 2026-10-15T21:55:00+08:00
- **Notes**: 已将插件设置移动到各插件目录的 `config.ini`，程序级文件只保存插件启用状态；旧程序级配置、旧 JSON 配置和 portable 输出规则均已完成验证。

## [FEAT-20261015-002] central_personal_config_ini

**Logged**: 2026-10-15T16:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: config

### Requested Capability
将个人配置统一保存到程序目录的 `config.ini`，构建输出和 portable 压缩包不包含该文件。

### User Context
用户需要更新配置时保留已有敏感字段，并让程序目录中的个人信息与可发布的客户端文件分离。

### Complexity Estimate
complex

### Suggested Implementation
建立共享的 `UserConfigStore`，让各插件使用独立配置节保存设置；启动器向后端传递程序目录配置路径；构建脚本排除个人配置、旧配置文件和运行生成文件。

### Metadata
- Frequency: first_time
- Related Features: campus_credentials_ui_and_blank_template, packaged_client_output

### Resolution
- **Resolved**: 2026-10-15T16:50:00+08:00
- **Notes**: 已加入共享 `UserConfigStore`、程序目录配置路径传递、插件配置节、旧配置迁移、敏感配置保护和 portable 构建排除规则，并完成源代码、portable 后端和完整客户端构建验证。

---

## [FEAT-20261014-001] colmon_continuous_monitor_plugin

**Logged**: 2026-10-14
**Priority**: high
**Status**: resolved
**Area**: integration

### Requested Capability
将 `D:\ColboiIN\code\Colmon` 集成为持续运行插件，管理除番茄钟外的三个任务栏窗口，并在 ColPilot 页面显示窗口信息与可调整的信息刷新频率。

### User Context
用户希望在 ColPilot 工作台中统一查看 Colmon 的任务栏监控状态，并通过页面调整三个窗口的数据更新间隔。

### Complexity Estimate
complex

### Suggested Implementation
为 Colmon 增加独立的窗口设置目录参数；插件后端启动和终止 Colmon 进程，使用状态文件读取三个任务栏窗口的机器可读信息，通过插件页面展示状态并保存全局刷新频率。

### Metadata
- Frequency: first_time
- Related Features: continuous_tool_lifecycle

### Resolution
- **Resolved**: 2026-10-14
- **Notes**: 已加入 colmon continuous 插件、三个任务栏窗口状态页面、统一刷新频率设置、独立窗口设置目录和 portable Colmon 运行文件；构建与自动测试已经通过。

---

## [FEAT-20261013-004] campus_credentials_ui_and_blank_template

**Logged**: 2026-10-13
**Priority**: high
**Status**: resolved
**Area**: config

### Requested Capability
在 colszunet 插件页面提供校园网账号和密码输入框，停止输入后自动保存，并将空账号密码配置文件同步至 GitHub。

### User Context
用户需要在界面中维护本机账号信息，同时让独立插件仓库保留可以安全同步的配置模板。

### Complexity Estimate
medium

### Suggested Implementation
后端扩展插件设置接口和状态返回字段，前端使用防抖保存减少请求次数；插件仓库跟踪空账号密码配置文件，个人凭据保留在本机。

### Metadata
- Frequency: first_time
- Related Features: independent_plugin_subprojects, configurable_connectivity_interval

### Resolution
- **Resolved**: 2026-10-13
- **Notes**: 已加入账号密码输入框、700 毫秒防抖保存、空凭据状态提示和 GitHub 可同步的空配置，并推送至 `colpilot.colszunet` 的 `main` 分支。

## [FEAT-20261013-003] independent_plugin_subprojects

**Logged**: 2026-10-13
**Priority**: high
**Status**: resolved
**Area**: infra

### Requested Capability
将现有插件作为独立子项目维护，并将校园网监控与 DMM 作品资料项目编号分别设置为 `colszunet` 与 `coldmmpics`。

### User Context
用户需要清晰区分插件项目目录、项目编号、后端入口、前端视图和运行文件。

### Complexity Estimate
medium

### Suggested Implementation
为每个插件建立独立目录，更新 manifest、backend、frontend、worker、API 路径与文档路径；核心项目保留插件目录入口，并忽略插件仓库内容。

### Metadata
- Frequency: first_time
- Related Features: optional_plugin_repository_sync

### Resolution
- **Resolved**: 2026-10-13
- **Notes**: 已完成 `colszunet` 与 `coldmmpics` 仓库目录、manifest、后端入口、前端入口、运行文件和文档路径更新，并完成 Python 导入检查、Python 编译检查和前端构建检查。

## [FEAT-20261013-002] plugin_change_startup_rebuild

**Logged**: 2026-10-13
**Priority**: high
**Status**: resolved
**Area**: infra

### Requested Capability
程序启动时检查本地插件内容变化，按照改动类型自动重启 backend 或构建前端资源，并隐藏构建窗口。

### User Context
用户希望插件文件放入本机后，程序可以自动识别变化并完成更新，减少手动构建操作。

### Complexity Estimate
complex

### Suggested Implementation
为每个插件保存内容摘要和构建状态；backend 与 worker 改动触发 backend 重启，UI 与 manifest 改动触发构建；使用独立启动器和 staging 目录执行构建，成功后重新启动客户端，失败时显示状态并保留日志；portable 客户端需要预置构建工具，或者改为加载插件预构建 UI 资源。

### Metadata
- Frequency: first_time
- Related Features: optional_plugin_repository_sync

---

## [FEAT-20261013-001] optional_plugin_repository_sync

**Logged**: 2026-10-13
**Priority**: high
**Status**: pending
**Area**: infra

### Requested Capability
将核心项目与各插件放置在独立 GitHub 仓库；默认同步核心项目时不取得插件内容，用户可以按需取得指定插件。

### User Context
用户希望插件互相独立，核心项目迁移到其他机器时保持目录整洁，并按需选择插件。

### Complexity Estimate
medium

### Suggested Implementation
使用 Git submodule 记录插件仓库地址和提交版本；核心项目保留空插件目录；增加按需初始化指定插件的说明与检查；调整构建流程，使无插件状态可以正常编译和运行；为每个插件单独维护敏感配置和生成文件的忽略规则。

### Metadata
- Frequency: first_time
- Related Features: plugin_tool_execution_types

### Resolution
- **Resolved**: 2026-10-14
- **Notes**: `plugins/colszunet` 与 `plugins/coldmmpics` 已作为独立 Git 仓库推送至 GitHub；核心项目继续忽略插件具体内容，按需获取插件仓库即可。

---

## [FEAT-20261012-004] dmm_access_confirmation

**Logged**: 2026-10-12T18:20:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Requested Capability
DMM 返回年龄或地区确认页面时，自动提交确认并继续访问作品页面。

### User Context
作品搜索和作品页面可能先返回确认页面，插件需要保持按需任务流程连续运行。

### Complexity Estimate
medium

### Suggested Implementation
复用 HTTP 客户端 Cookie，识别 DMM 确认页面中的明确确认入口，自动提交确认请求并继续处理搜索、作品页面和预览图请求；确认入口无法识别时显示网络访问错误。

### Metadata
- Frequency: first_time
- Related Features: dmm_metadata_preview_workflow

### Resolution
- **Resolved**: 2026-10-12T18:20:00+08:00
- **Notes**: 已通过实际 DMM 请求确认 `age_check_done` Cookie 和作品页面跳转，搜索接口已经返回 `SNOS-308` 对应页面。

---

## [FEAT-20261008-002] colpilot_desktop_icon

**Logged**: 2026-10-08T12:15:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: config

### Requested Capability
为 ColPilot 设计并接入任务栏、窗口和托盘使用的统一图标。

### User Context
用户需要清晰、可识别、适合 Windows 桌面显示的应用图标。

### Complexity Estimate
medium

### Suggested Implementation
生成透明背景的品牌图案，制作 Windows 多尺寸 `ICO`，更新 Tauri bundle 配置，并让托盘读取同一份 PNG。

### Metadata
- Frequency: first_time
- Related Features: tray_click_opens_frontend

### Resolution
- **Resolved**: 2026-10-08T12:32:00+08:00
- **Notes**: 已生成 ColPilot 图案、Windows `ICO` 和托盘 PNG，并完成前端构建、Rust 检查及 Tauri Release 打包验证。

---

## [FEAT-20261005-001] tray_click_opens_frontend

**Logged**: 2026-10-05
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Requested Capability
打包后的程序启动时显示前端窗口，点击系统托盘图标时显示并聚焦前端窗口。

### User Context
用户希望将程序作为 exe 使用，并通过托盘图标快速回到工具工作台。

### Complexity Estimate
simple

### Suggested Implementation
使用 Tauri 托盘左键事件显示主窗口、取消最小化并设置焦点；右键继续保留退出菜单。

### Metadata
- Frequency: first_time
- Related Features: tray_exit

### Resolution
- **Resolved**: 2026-10-05
- **Notes**: 已完成托盘左键唤起、启动显示主窗口和关闭窗口回到托盘的行为。

---

## [FEAT-20261005-002] colszunet_campus_monitor_plugin

**Logged**: 2026-10-05
**Priority**: high
**Status**: resolved
**Area**: frontend

### Requested Capability
将 `D:\ColboiIN\code\colszunet` 加入 Colpilot，提供校园网当前状态、监听状态和 24h/7d 状态信息。

### User Context
用户希望在统一工作台中查看校园网自动登录监控运行情况。

### Complexity Estimate
medium

### Suggested Implementation
启动 `colszunet` 监控进程，读取其状态日志，在 FastAPI 中提供插件状态接口，并在 Vue 插件详情区域展示三类状态。

### Metadata
- Frequency: first_time
- Related Features: campus_network_monitor

### Resolution
- **Resolved**: 2026-10-05
- **Notes**: 已接入监控进程、状态接口、插件启停和 Vue 状态面板。

---

## [FEAT-20261005-003] background_python_process

**Logged**: 2026-10-05
**Priority**: medium
**Status**: resolved
**Area**: infra

### Requested Capability
启动 Colpilot 时不显示 Python 命令提示符窗口，并保持 Python 后端在后台运行。

### User Context
用户希望程序启动过程保持安静，同时继续使用本地 Python 服务。

### Complexity Estimate
simple

### Suggested Implementation
为 Windows 后端子进程设置 `CREATE_NO_WINDOW`，并将标准输出与错误输出重定向到空设备。

### Metadata
- Frequency: first_time
- Related Features: backend_process_lifecycle

### Resolution
- **Resolved**: 2026-10-05
- **Notes**: 已为 Rust 启动的 Python 后端加入无窗口标志，并完成构建验证。

---

## [FEAT-20261005-004] configurable_connectivity_interval

**Logged**: 2026-10-05
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Requested Capability
将校园网连通性检查间隔改为可配置秒数，默认值为 300 秒，并提供前端设置入口。

### User Context
用户需要控制 `colszunet` 的网络检查频率，减少不必要的网络请求。

### Complexity Estimate
medium

### Suggested Implementation
读取并更新 `probe_interval_seconds`，通过 FastAPI 保存设置并重启监控进程，在校园网插件详情页面提供秒数输入和保存按钮。

### Metadata
- Frequency: first_time
- Related Features: colszunet_campus_monitor_plugin

### Resolution
- **Resolved**: 2026-10-05
- **Notes**: 已完成默认间隔更新、前端设置、配置保存和监控进程重启。

---

## [FEAT-20261008-001] campus_history_status_bar

**Logged**: 2026-10-08
**Priority**: medium
**Status**: in_progress
**Area**: frontend

### Requested Capability
将校园网监控的 24h/7d 状态条改为按检测记录显示历史状态，连通性失败记录使用红色显示。

### User Context
用户希望直接看到历史检测记录中的成功与失败变化。

### Complexity Estimate
medium

### Suggested Implementation
后端返回时间范围内的连通性记录，前端将每条记录显示为绿色或红色状态段，并保留检测时间和失败详情提示。

### Metadata
- Frequency: first_time
- Related Features: configurable_connectivity_interval

### Resolution
- **Resolved**: 2026-10-08
- **Notes**: 已加入按时间段显示的历史状态条，成功显示绿色，失败显示红色，无记录显示灰色，并完成 Release 程序验证。

---

## [FEAT-20261008-002] packaged_client_output

**Logged**: 2026-10-08
**Priority**: medium
**Status**: resolved
**Area**: infra

### Requested Capability
整理项目文件，并且将可整体复制使用的完整 portable 客户端输出到项目根目录的 `target`。

### User Context
用户需要包含配置文件、后端文件、插件文件和运行依赖的客户端目录，减少构建缓存和前端中间文件对项目目录的干扰。

### Complexity Estimate
medium

### Suggested Implementation
增加统一客户端构建脚本，将 exe、后端文件、Python 运行依赖、校园网插件和配置文件复制到 `target`，并在复制完成后清理 `dist`、`src-tauri/target` 与 Python 编译缓存。

### Metadata
- Frequency: first_time
- Related Features: background_python_process

### Resolution
- **Resolved**: 2026-10-08
- **Notes**: `target` 已包含可执行文件、后端文件、独立 Python 运行目录、插件文件和插件配置；构建完成后会清理前端与 Rust 构建目录，安装程序保留在构建过程内部并清理。

---

## [FEAT-20261012-001] plugin_tool_execution_types

**Logged**: 2026-10-12
**Priority**: high
**Status**: resolved
**Area**: backend

### Requested Capability
提供持续运行工具和按需运行工具两类接口，并在侧边栏显示持续运行工具的脚本运行状态。

### User Context
校园网监控需要持续显示后台脚本的运行情况，按需运行工具不需要占用侧边栏状态标志。脚本异常退出需要与校园网连通性失败区分显示。

### Complexity Estimate
medium

### Suggested Implementation
在插件清单中声明 `tool_type`；持续运行工具实现 `start`、`stop`、`runtime_status`，按需运行工具实现 `run(arguments)`。通用插件接口返回脚本运行状态，前端仅为持续运行工具绘制状态标志。

### Metadata
- Frequency: first_time
- Related Features: plugin_materials_stay_with_plugin

### Resolution
- **Resolved**: 2026-10-12
- **Notes**: 已加入两类工具接口、侧边栏运行标志和脚本异常状态识别，并使用真实校园网监控进程退出与重新启动完成验证。

---

## [FEAT-20261012-002] dmm_request_capture

**Logged**: 2026-10-12T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Requested Capability
记录访问 `dmm.co.jp` 期间产生的 HTTP(S) 请求，重点标记地区确认相关请求，帮助用户生成针对性的代理规则。

### User Context
用户需要确认地区检查的请求地址、请求方法、重定向关系和关联域名，以便设置代理转发范围。

### Complexity Estimate
medium

### Suggested Implementation
提供基于浏览器开发者工具或本地代理的请求记录流程，保存请求时间、主机名、路径、请求方法、状态码、重定向链和触发来源，并支持按 `region`、`country`、`locale`、`geo` 等关键词筛选。

### Metadata
- Frequency: first_time
- Related Features: plugin_tool_execution_types

---

## [FEAT-20261012-003] dmm_metadata_preview_workflow

**Logged**: 2026-10-12T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: workflow

### Requested Capability
根据作品番号搜索 `video.dmm.co.jp` 作品 URL，读取作品元数据，并下载页面公开的预览图。

### User Context
用户通常输入作品编号，需要得到规范作品页、作品字段、图片地址和本地文件结果。

### Complexity Estimate
medium

### Suggested Implementation
规范作品番号、通过 DMM 搜索页面获取作品 URL、解析作品页面、提取 JSON-LD、整理页面字段、下载 CDN 图片并写入 JSON；选择输出文件夹后立即保存设置，页面访问失败时显示具体错误信息。

### Metadata
- Frequency: first_time
- Related Features: dmm_request_capture

### Resolution
- **Resolved**: 2026-10-12T17:05:00+08:00
- **Notes**: 已加入 DMM `on_demand` 插件、番号搜索、输出文件夹自动保存、任务状态、元数据保存、预览图下载和输出文件夹打开功能。

---

## [FEAT-20261015-001] desc_container_auto_renewal

**Logged**: 2026-10-15T15:20:00+08:00
**Priority**: high
**Status**: resolved
**Area**: integration

### Requested Capability
开发 Colpilot 插件，访问 DESC 容器管理服务，读取用户容器剩余时间，并提供账号登录、自动登录和自动续约功能。

### User Context
DESC 服务需要登录认证，用户希望在 Colpilot 中持续查看容器时间，并在设置的时间阈值内自动完成续约。

### Complexity Estimate
complex

### Suggested Implementation
在独立插件目录中维护 manifest、FastAPI 插件后端、Vue 页面和本地设置文件。后端保存账号设置、管理 Bearer token，在服务返回 401 时重新登录，按周期读取容器列表和剩余时间，并依据用户设置执行自动续约。

### Metadata
- Frequency: first_time
- Related Features: plugin_materials_stay_with_plugin, plugin_tool_execution_types
- Tags: desc, containers, login, auto-renewal

### Resolution
- **Resolved**: 2026-10-15T15:40:00+08:00
- **Notes**: 已加入 `colcontainers` continuous 插件、DESC 账号设置、Bearer token 自动登录、容器剩余时间同步、自动续约阈值和 portable 构建复制。当前对话没有账号凭据，真实账号登录与续约请求将在用户填写账号后执行。

---

## [FEAT-20261016-001] single_dashboard_plugin_cards

**Logged**: 2026-10-16
**Priority**: high
**Status**: resolved
**Area**: frontend

### Requested Capability
将前端收敛为单一仪表盘，同时显示全部插件卡片；左侧插件管理用于滚动到对应卡片；顶部只保留程序名和设置按钮。

### User Context
用户需要直接在一个工作区域使用全部插件，并减少欢迎内容、统计信息、服务状态和重复导航内容。

### Suggested Implementation
移除欢迎区域、统计区域、插件标题区域、顶部服务状态、圆形用户图标和侧边栏底部提示。让每张插件卡片直接承载对应插件界面，插件导航通过卡片标识执行平滑滚动。

### Metadata
- Frequency: correction
- Related Features: plugin_materials_stay_with_plugin
- Tags: frontend, dashboard, plugin-card, navigation

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 主区域已经同时渲染全部插件卡片和对应界面；左侧导航使用平滑滚动；顶部只显示 `Colpilot` 和设置按钮；前端构建与 Tauri portable 构建均已通过。

---

## [FEAT-20261016-002] plugin_process_lifecycle

**Logged**: 2026-10-16
**Priority**: critical
**Status**: resolved
**Area**: backend

### Requested Capability
将 `colmon` 改为 Colpilot 专用插件，直接管理三个任务栏窗口；统一管理全部插件创建的进程，并在 Colpilot 退出时安全关闭。

### User Context
当前残留进程会占用插件文件，影响文件修改和程序更新。用户需要退出 Colpilot 后释放全部插件进程和窗口资源。

### Complexity Estimate
complex

### Suggested Implementation
为 Colpilot 增加受管进程注册表和退出关闭流程；为持续运行插件提供停止接口和结束等待；将三个任务栏窗口的管理逻辑放入 `colmon` 插件后端，避免启动独立 Colmon 程序。

### Metadata
- Frequency: correction
- Related Features: colmon_continuous_monitor_plugin, plugin_tool_execution_types
- Tags: colmon, process, lifecycle, shutdown

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: `colmon` 已改为后端内原生任务栏窗口插件；所有后台进程经过统一登记，桌面端关闭时先请求后端退出，再等待清理，超时由 Windows Job Object 回收进程树。

---

## [FEAT-20261016-003] plugin_drag_reordering

**Logged**: 2026-10-16
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Requested Capability
允许用户拖拽左侧插件导航调整顺序，并让右侧插件卡片使用相同顺序。

### User Context
用户需要按照个人使用习惯排列插件，快速导航和仪表盘卡片需要保持一致。

### Complexity Estimate
medium

### Suggested Implementation
使用左侧导航的拖拽事件更新共享插件数组，通过后端接口保存插件标识顺序到程序级 `config.ini`；后端返回清单时按照保存顺序排列。

### Metadata
- Frequency: first_time
- Related Features: dashboard_card_navigation
- Tags: frontend, plugin-order, drag-and-drop, config

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成拖拽排序、后端顺序接口、程序级配置保存、重启读取和 portable 客户端验证。

---

## [FEAT-20261016-004] settings_plugin_distribution_and_themes

**Logged**: 2026-10-16
**Priority**: high
**Status**: resolved
**Area**: frontend

### Requested Capability
增加内置设置窗口、外观主题管理、GitHub 插件下载与更新检查，并生成不包含插件文件的 portable 客户端目录和 release zip。

### User Context
用户需要在 Colpilot 内完成个人配置、主题调整和插件来源管理，同时保持客户端发布包的基础内容清晰可控。

### Complexity Estimate
complex

### Suggested Implementation
使用独立的设置界面、程序级 appearance 配置和插件来源管理模块。插件安装记录保存仓库地址与提交标识，定时检查只更新状态，不自动覆盖插件文件。构建脚本输出 plugin-free portable 目录及其 zip 文件。

### Metadata
- Frequency: first_time
- Related Features: plugin_materials_stay_with_plugin, plugin_drag_reordering
- Tags: settings, themes, github, plugin-manager, portable

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成内置设置窗口、外观预设和颜色配置、GitHub 插件下载与提交状态检查、可选插件图标接口，以及 plugin-free portable 文件夹和 release zip 构建输出。

---

## [FEAT-20261017-001] private_plugin_zip_import

**Logged**: 2026-10-17T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Requested Capability
在插件管理设置中导入本地 ZIP 仓库，以便安装私有插件。

### User Context
部分插件仓库无法通过公开 GitHub 地址访问，需要使用本地 ZIP 文件安装，并继续由 Colpilot 保存来源信息和管理插件生命周期。

### Complexity Estimate
medium

### Suggested Implementation
复用插件清单校验、安全解压和插件来源记录流程，增加 multipart ZIP 上传接口与设置页面文件选择器。本地 ZIP 来源显示本地文件名称，定时更新检查只处理 GitHub 来源。

### Metadata
- Frequency: first_time
- Related Features: settings_plugin_distribution_and_themes
- Tags: settings, private-plugin, zip, plugin-manager

### Resolution
- **Resolved**: 2026-10-17
- **Notes**: 已加入本地 ZIP 选择器、multipart 上传接口、安全解压、来源记录和本地来源状态；实际插件 ZIP 导入与发布版 portable 客户端验证已经通过。

---
