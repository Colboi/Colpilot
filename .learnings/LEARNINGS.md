# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20261015-006] plugin_config_ownership

**Logged**: 2026-10-15T21:20:00+08:00
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
插件设置应由插件目录中的独立 `config.ini` 管理，程序级配置只保存程序自身状态。

### Details
共享配置读取器可以继续复用，但每个插件需要获得指向自身目录的 `UserConfigStore`。从旧程序级配置迁移插件配置时，复制对应配置节并移除旧配置节；旧 JSON 文件继续作为迁移来源。

### Suggested Action
构建阶段递归过滤插件目录中的 `config.ini`，运行验证需要分别检查程序级配置路径和插件级配置路径。

### Metadata
- Source: correction
- Related Files: backend/main.py, backend/user_config.py, scripts/build-client.ps1
- Tags: config, plugin, ownership, migration

### Resolution
- **Resolved**: 2026-10-15T21:55:00+08:00
- **Notes**: 每个插件使用自身目录的 `UserConfigStore`，旧程序级插件配置会迁移并移除旧配置节；最终 portable 输出没有任何 `config.ini`。

## [LRN-20261015-005] portable_runtime_cache_filter

**Logged**: 2026-10-15T20:45:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: build

### Summary
portable 运行目录需要过滤 Python 运行时内部各层目录中的缓存文件。

### Details
只过滤复制源目录的顶层缓存目录无法覆盖标准库和第三方依赖内部的嵌套缓存目录。构建脚本在复制运行时后，按目录深度清理全部 `__pycache__` 目录，并清理剩余的 `.pyc` 文件。

### Suggested Action
每次修改 portable 复制规则后，检查发布目录的配置文件、日志、运行状态和 Python 缓存文件。

### Metadata
- Source: best_practice
- Related Files: scripts/build-client.ps1
- Tags: portable, build, python-cache

### Resolution
- **Resolved**: 2026-10-15T20:45:00+08:00
- **Notes**: 已加入递归缓存清理步骤，最终构建检查确认发布目录没有 Python 缓存目录和缓存文件。

## [LRN-20261015-004] program_directory_config_store

**Logged**: 2026-10-15T16:50:00+08:00
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
portable 程序需要将个人配置路径传递给后端，并在构建复制阶段排除个人文件与旧配置文件。

### Details
程序目录由 Tauri 启动器确定，开发模式使用项目根目录，发布模式使用可执行文件所在目录。后端通过 `UserConfigStore` 维护一个 `config.ini`，插件分别使用自己的配置节；没有用户设置时不创建文件。旧 JSON 配置只用于迁移，portable 输出使用过滤复制，避免将个人配置、旧配置、日志和运行状态带入发布目录。

### Suggested Action
新增插件设置时复用共享配置对象，只写入对应配置节，并为部分更新字段保留已有敏感值；构建验证需要检查发布目录中不存在 `config.ini`、旧配置文件和敏感日志。

### Metadata
- Source: best_practice
- Related Files: backend/user_config.py, backend/main.py, scripts/build-client.ps1, src-tauri/src/lib.rs
- Tags: config, ini, portable, credentials, migration

### Resolution
- **Resolved**: 2026-10-15T16:50:00+08:00
- **Notes**: 已完成实现并通过 Python、Vite、Tauri、portable 后端和发布目录检查。

---

## [LRN-20261015-003] partial_config_update_semantics

**Logged**: 2026-10-15T16:02:00+08:00
**Priority**: high
**Status**: pending
**Area**: config

### Summary
配置更新接口需要区分字段缺失、空字符串、`null` 和明确清空动作，防止表单默认空值覆盖已保存的敏感配置。

### Details
更新请求采用部分更新语义时，字段缺失表示保留原值；允许清空的字段使用统一的 `null` 语义或明确的清空字段；账号密码等敏感字段需要由后端再次保护，并且响应只返回是否已经设置。

### Suggested Action
为更新请求使用可选字段，在后端仅处理请求中出现的字段；为密码设置明确的保留与清空规则；为字段缺失、空字符串、`null`、新值和并发更新分别增加验证。

### Metadata
- Source: conversation
- Related Files: backend/main.py, plugins/campus_network/backend.py, plugins/colcontainers/backend.py
- Tags: config, partial-update, credentials, api

---

## [LRN-20261014-002] continuous_plugin_startup_state

**Logged**: 2026-10-14
**Priority**: high
**Status**: resolved
**Area**: runtime

### Summary
持续运行插件遇到可识别的外部进程占用时，需要保留主服务并把处理提示交给插件页面。

### Details
Colmon 已经运行时，插件记录 `error` 运行状态和具体处理提示，三个窗口状态页面继续可访问，主程序可以正常打开。

### Suggested Action
持续运行插件应区分可识别的启动条件与未处理的程序错误，并为前者提供明确的运行状态。

### Metadata
- Source: self_improvement
- Related Files: plugins/colmon/backend.py
- Tags: continuous, startup, process

### Resolution
- **Resolved**: 2026-10-14
- **Notes**: 已验证已有 Colmon 进程时后端健康接口、插件列表接口和 Colmon 状态接口均正常返回。

## [LRN-20261014-001] external_taskbar_host_integration

**Logged**: 2026-10-14
**Priority**: high
**Status**: resolved
**Area**: integration

### Summary
集成外部任务栏宿主时，需要同时隔离进程状态目录、窗口设置目录和运行文件，并通过状态快照向工作台提供数据。

### Details
Colmon 的三个信息窗口已经可以使用独立的 `--artifact-dir` 与 `--window-options-dir`。ColPilot 插件保存统一刷新频率，启动 Colmon 时生成 `showPomodoro: false` 的配置，并读取三个窗口的状态文件展示当前数据、状态和更新时间。

### Suggested Action
集成持续运行桌面程序时，为每个插件实例指定独立状态目录，使用原程序提供的机器可读状态，并在页面中标记数据过期状态。

### Metadata
- Source: best_practice
- Related Files: plugins/colmon/backend.py, plugins/colmon/ui/ColmonView.vue, D:\ColboiIN\code\Colmon\src\Colmon.App\Program.cs
- Tags: integration, taskbar, continuous, state-snapshot

### Resolution
- **Resolved**: 2026-10-14
- **Notes**: 已完成 Colmon 插件接入、portable 运行文件打包和构建验证。


## [LRN-20261013-004] broad_project_repository_scope

**Logged**: 2026-10-13
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
本项目中的“项目”表示 GitHub 仓库边界；独立插件仓库按需要保留源文件和仓库配置，根项目保留根目录 `AGENTS.md`。

### Details
- `plugins/colszunet` 与 `plugins/coldmmpics` 作为独立 GitHub 仓库管理。
- 插件目录不需要额外的 `AGENTS.md` 等代理说明文件。
- 核心项目通过插件清单发现本机已经放入的插件。

### Suggested Action
后续新增插件仓库时，只添加运行所需文件和必要的仓库配置，避免为每个插件复制核心项目管理文件。

### Metadata
- Source: user_feedback
- Related Files: README.md, plugins
- Tags: github, plugin-repository, project-boundary

### Resolution
- **Resolved**: 2026-10-13
- **Notes**: 已更新项目说明并移除插件目录中的额外 `AGENTS.md` 文件。

## [LRN-20261012-004] dmm_search_video_link_priority

**Logged**: 2026-10-12
**Priority**: high
**Status**: resolved
**Area**: integration

### Summary
DMM 搜索结果会同时包含 DVD、月租视频和视频详情链接，旧式 `cid` 链接需要按照目录类型筛选。

### Details
- 搜索番号使用字母与数字分开的形式，例如 `miad 657`。
- 搜索结果优先匹配 `/av/content/?id=...` 视频详情链接。
- 旧式 `cid` 链接只接受 `digital`、`videoa`、`video` 和 `av` 目录，跳过 DVD 与月租详情链接。
- `MIAD-657` 的有效 content id 是 `miad00657`，实际验证成功下载 12 张预览图。

### Suggested Action
处理 DMM 搜索结果时，先根据链接目录确认商品类型，再解析 content id。

### Metadata
- Source: user_feedback_and_verified_direct_http_workflow
- Related Files: plugins/dmm_metadata/backend.py
- Tags: dmm, search, content-id, preview-image

### Resolution
- **Resolved**: 2026-10-12
- **Notes**: 分词搜索和视频链接筛选已经写入插件。

---

## [LRN-20261012-003] dmm_nextjs_graphql_metadata_source

**Logged**: 2026-10-12
**Priority**: high
**Status**: resolved
**Area**: integration

### Summary
DMM 当前作品页面可能只返回 Next.js 应用外壳，作品资料与预览图通过 `api.video.dmm.co.jp/graphql` 的 `ppvContent` 查询提供。

### Details
- 保留页面 `Product JSON-LD` 读取路径，用于兼容仍然提供结构化资料的页面。
- 页面缺少 `Product JSON-LD` 时，使用已经确认年龄或地区页面的同一个 `httpx.Client` 请求 GraphQL 接口。
- 查询 `ppvContent` 的标题、描述、发行时间、演员、导演、制作信息、分类、商品价格和预览图；通过 `reviewSummary` 获取评价数据。
- GraphQL 预览图选择封面、海报和大尺寸样本图，`SNOS-308` 实际下载 13 张 JPG 文件。
- 运行环境不设置代理参数；DMM 访问失败时由插件返回具体错误。

### Suggested Action
DMM 页面资料读取应同时支持结构化数据和官方页面使用的 GraphQL 查询，并对 GraphQL 错误直接报告。

### Metadata
- Source: verified_direct_http_workflow
- Related Files: plugins/dmm_metadata/backend.py, README.md
- Tags: dmm, graphql, nextjs, metadata, preview-image

### Resolution
- **Resolved**: 2026-10-12
- **Notes**: 源代码和 portable 后端均已通过真实 DMM 请求验证。

---

## [LRN-20261008-002] portable_output_contains_runtime_assets

**Logged**: 2026-10-08
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
portable 客户端目录需要包含可执行文件、后端文件、插件文件、配置文件和运行依赖。

### Details
`target` 目录需要整体复制使用，Tauri 启动程序根据自身目录定位 `backend`、Python 运行依赖和 `plugins/colszunet`，校园网配置文件需要位于 portable 目录内。

### Suggested Action
让构建脚本生成完整 portable 目录，并让 Rust 启动器与 Python 后端优先使用自身目录中的文件。

### Metadata
- Source: user_feedback
- Related Files: scripts/build-client.ps1, src-tauri/src/lib.rs, backend/main.py
- Tags: portable, packaging, runtime

### Resolution
- **Resolved**: 2026-10-08
- **Notes**: `target\runtime\python.exe` 使用目录内部的 Python 文件和依赖；启动验证确认后端与校园网插件均使用 `target` 路径，退出后进程数量与端口监听数量均为零。

---

## [LRN-20261008-002] correction

**Logged**: 2026-10-08T12:40:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: config

### Summary
任务栏图标需要优先使用大轮廓与少量形状，并直接表达助手定位。

### Details
用户指出当前图标的纹理细节在任务栏尺寸下难以识别，同时需要强化智能助手含义。后续候选图案使用对话气泡、助手星芒和简化 `C` 形作为主要识别元素。

### Suggested Action
图标设计检查需要覆盖 16px、24px、32px 与 48px 显示尺寸，限制内部形状数量，优先保证助手符号清晰可见。

### Metadata
- Source: user_feedback
- Related Files: src-tauri/icons/colpilot-icon.png, src-tauri/icons/candidates
- Tags: icon, taskbar, assistant, simplification

### Resolution
- **Resolved**: 2026-10-08T12:12:00+08:00
- **Notes**: 已采用 C 形助手图案，更新所有应用图标来源并完成调试版与 Release 构建验证。

---

## [LRN-20261008-001] campus_history_bucket_display

**Logged**: 2026-10-08
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
历史状态条使用固定数量的时间段，可以保持长时间范围的状态清晰可见并控制页面数据量。

### Details
24h 使用 48 个时间段，7d 使用 168 个时间段。每个时间段出现失败记录时显示红色，全部成功时显示绿色，没有检测记录时显示灰色，同时保留精确的检测次数和成功率统计。

### Suggested Action
新增长时间范围的历史状态显示时，使用时间段汇总，并通过悬停提示展示时间范围与状态详情。

### Metadata
- Source: conversation
- Related Files: backend/main.py, src/App.vue, src/style.css
- Tags: frontend, history, status

---

## [LRN-20261008-003] portable_directory_boundary

**Logged**: 2026-10-08
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
portable 目录只保留解压后即可运行的客户端文件。

### Details
安装程序属于安装发布文件，不属于 portable 客户端目录。`target` 需要包含可执行文件、后端文件、运行时、插件文件和插件配置。

### Suggested Action
构建脚本将安装程序留在构建过程内部，并在完成 portable 文件复制后清理构建目录。

### Metadata
- Source: user_feedback
- Related Files: scripts/build-client.ps1, README.md
- Tags: correction, portable, packaging

### Resolution
- **Resolved**: 2026-10-08
- **Notes**: 已移除 `target\installers`，重新定义 `target` 为解压后即可运行的客户端目录。

---

## [LRN-20261008-004] placeholder_plugin_cleanup

**Logged**: 2026-10-08
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
当前插件清单只保留已经接入页面和后端功能的校园网监控插件。

### Details
占位工具会进入插件清单、侧边栏、仪表盘卡片和启用数量统计，影响用户判断可用功能。未实现的工具不应出现在运行客户端中。

### Suggested Action
从 `PLUGIN_DEFINITIONS` 移除未实现工具，并验证 `/api/plugins`、前端插件卡片和校园网监控页面仍然正常。

### Metadata
- Source: user_feedback
- Related Files: backend/main.py, src/App.vue
- Tags: correction, plugins, cleanup

### Resolution
- **Resolved**: 2026-10-08
- **Notes**: `PLUGIN_DEFINITIONS` 只保留校园网监控，接口验证返回一个插件，portable 客户端启动和退出验证完成。

---

## [LRN-20261012-001] plugin_materials_stay_with_plugin

**Logged**: 2026-10-12
**Priority**: high
**Status**: resolved
**Area**: architecture

### Summary
插件清单、后端实现、前端组件、样式和运行文件都放在对应插件目录中。

### Details
主程序负责发现插件清单、加载插件后端、管理生命周期和提供通用 HTTP 接口。前端主容器通过清单加载插件页面，插件功能页面与样式由插件目录提供。

### Suggested Action
新增插件时，在 `plugins/<plugin_directory>` 中同时维护清单、后端、前端和运行文件；主程序只扩展通用接口。

### Metadata
- Source: user_feedback
- Related Files: plugins/campus_network, backend/main.py, src/plugin-views.js, src/App.vue
- Tags: plugins, architecture, separation

### Resolution
- **Resolved**: 2026-10-12
- **Notes**: 校园网插件已经迁移为独立目录，后端和前端都通过插件清单加载，portable 输出验证通过。

---

## [LRN-20261012-002] dmm_metadata_preview_workflow

**Logged**: 2026-10-12
**Priority**: high
**Status**: resolved
**Area**: workflow

### Summary
`video.dmm.co.jp` 作品页可以通过公开的 `Product` JSON-LD 获取主要元数据和预览图地址。

### Details
- 使用 `site:video.dmm.co.jp <maker_code>` 搜索作品页，读取搜索结果实际跳转地址。
- 作品页的规范地址包含内部 `content_id`，例如 `SNOS-308` 对应 `snos00308`。
- 读取 `script[type="application/ld+json"]` 并使用 `JSON.parse` 获取 `name`、`sku`、`brand`、`image`、`offers`、`aggregateRating` 与嵌套 `VideoObject` 字段。
- 页面可见字段补充配信开始日期、商品発売日期、收录时长、导演、标签、厂家品番和配信品番。
- `image` 数组包含封面、海报和样本图的原始 CDN 地址；本次 `SNOS-308` 共取得 13 个 JPG 文件。
- 下载时通过 `127.0.0.1:7890` 代理，携带作品页 `Referer`，随后检查 JPEG 文件头、文件大小和图片尺寸。

### Suggested Action
实现同类输入时，保留“作品编号搜索、规范地址解析、JSON-LD 提取、页面字段补充、预览图下载、文件验证、JSON 输出”的顺序，并避免保存 Cookie 与授权信息。

### Metadata
- Source: verified_browser_workflow
- Related Files: artifacts/dmm/SNOS-308/metadata.json, artifacts/dmm/SNOS-308/*.jpg
- Tags: dmm, fanza, metadata, preview-image, browser, proxy

### Resolution
- **Resolved**: 2026-10-12
- **Notes**: 已使用 `SNOS-308` 成功读取元数据，下载 13 张 JPG 预览图，并验证全部图片可以由 `System.Drawing.Image` 读取。

---

## [LRN-20261013-001] campus_portal_proxy_diagnostic

**Logged**: 2026-10-13T13:55:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
校园网认证状态检查需要使用校园门户路径，并且门户认证请求需要明确使用直连网络。

### Details
Clash Verge 当前启用 TUN 与 fake-IP，`net.szu.edu.cn` 在 Mihomo 实时连接中匹配 `DomainSuffix szu.edu.cn` 并使用 `DIRECT`。校园网监控程序使用 Python `urllib.request.urlopen`，会继承 `HTTP(S)_PROXY=http://127.0.0.1:7890`。目标目录日志记录了多次 `SSL: UNEXPECTED_EOF_WHILE_READING`，外部网站检查和 `/cgi-bin/get_challenge` 请求同时失败。外部网站恢复后，监控程序会记录在线状态，即使门户仍然返回上网认证页面。

### Suggested Action
为校园门户请求创建明确的直连网络客户端，并使用校园网认证状态作为健康检查依据。监控生命周期需要保证同时只有一个校园网监控进程。

### Metadata
- Source: verified_diagnostic
- Related Files: plugins/campus_network/worker/campus_auto_login.py, plugins/campus_network/worker/config.json
- Tags: campus-network, clash, tun, proxy, health-check

### Resolution
- **Resolved**: 2026-10-13T14:55:00+08:00
- **Notes**: 校园网检测和门户请求已经改为显式直连 opener；进程内增加校园域名的 `NO_PROXY` 排除项；Windows 单实例锁、日志轮换和请求级别网络诊断已经加入，并同步到 portable 运行目录。

---

## [LRN-20261013-002] campus_network_request_observability

**Logged**: 2026-10-13T14:55:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
网络故障排查需要在每次请求中记录路径、目标、错误类别和耗时，同时保留原有连通性摘要供状态页面读取。

### Details
校园网状态页面依赖固定的 `连通性测试成功` 和 `连通性测试失败：` 日志文本。诊断信息需要增加到独立日志行，避免破坏历史统计；请求日志需要隐藏查询参数，运行上下文需要隐藏代理认证信息。

### Suggested Action
使用轮换文件日志，记录进程标识、Python 与 OpenSSL 版本、直连策略、请求编号、HTTP 状态、响应大小、错误类别和耗时。

### Metadata
- Source: best_practice
- Related Files: plugins/campus_network/worker/campus_auto_login.py, plugins/campus_network/backend.py
- Tags: campus-network, logging, observability, proxy, tls

### Resolution
- **Resolved**: 2026-10-13T14:55:00+08:00
- **Notes**: 已加入 2 MB 文件轮换、5 个历史文件、网络异常分类、请求编号以及代理信息脱敏；状态页面使用的摘要日志格式保持不变。

---

## [LRN-20261013-003] core_repository_without_plugin_submodules

**Logged**: 2026-10-13
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
核心仓库保留插件入口目录并忽略插件内容，可以满足默认同步过程不取得插件文件的要求。

### Details
用户确认核心仓库保存插件加载约定，插件源代码和运行文件通过本机独立复制或外部安装方式提供。Git submodule 会增加独立插件仓库维护工作，当前需求不需要采用该方式。

### Suggested Action
核心仓库跟踪 `plugins/__init__.py` 和 `.gitkeep`，忽略 `plugins/*` 下的插件目录；构建脚本继续依据实际存在的 `manifest.json` 复制插件；更新 README 说明插件安装流程。

### Metadata
- Source: user_feedback
- Related Files: .gitignore, backend/main.py, scripts/build-client.ps1
- Tags: github, plugins, repository, synchronization

---

## [LRN-20261015-001] campus_portal_tun_fake_ip_path

**Logged**: 2026-10-15T15:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
校园网门户认证失效时，Clash 的 TUN 路由与 fake-IP DNS 会共同影响 `net.szu.edu.cn` 的访问。

### Details
当前运行配置启用了 `tun.enable: true`、`auto-route: true`、`dns-hijack: any:53` 和 `dns.enhanced-mode: fake-ip`，同时未配置 `tun.route-exclude-address`。`net.szu.edu.cn` 经当前 DNS 解析为 `198.18.1.37`，使用校园网本地 DNS 查询到的实际地址为 `172.31.63.36`。现有 `DOMAIN-SUFFIX,szu.edu.cn,DIRECT` 规则只选择直连出口，无法让目标流量离开 TUN 路由。认证完成后校园网放行策略改变，表面上会让相同配置恢复访问。

### Suggested Action
将 `net.szu.edu.cn` 加入 `dns.fake-ip-filter`，让门户解析返回实际地址；在 Clash Verge 的 TUN 设置中加入实际门户地址的 `/32` 路由排除，例如 `172.31.63.36/32`；保留 `DOMAIN,net.szu.edu.cn,DIRECT` 规则，并检查最终运行配置是否保留这些字段。

### Metadata
- Source: verified_diagnostic
- Related Files: C:/Users/10168/AppData/Roaming/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml, C:/Users/10168/AppData/Roaming/io.github.clash-verge-rev.clash-verge-rev/dns_config.yaml
- Tags: campus-network, clash, tun, fake-ip, captive-portal, route-exclude

---

## [LRN-20261015-002] desc_service_api_protocol

**Logged**: 2026-10-15T15:40:00+08:00
**Priority**: high
**Status**: resolved
**Area**: integration

### Summary
DESC 容器页面通过 Bearer token 访问用户信息、容器列表、剩余时间和续约接口。

### Details
页面入口加载的 bundle 确认登录接口为 `POST /api/user/validate`，请求体包含 `username` 和 `password`，响应提供 `valid` 与 `token`。用户信息接口为 `GET /api/users`，容器列表接口为 `GET /api/container/ofuser?uid=...`，剩余时间接口为 `GET /api/incus/{server}/{container}`，续约接口为 `PUT /api/container/renew?cid=...`。认证请求使用 `Authorization: Bearer <token>`；容器列表没有记录时服务返回 404。

### Suggested Action
插件后端保存账号设置，在收到 401 时重新登录，按照用户编号读取容器，并按照服务页面使用的节点名称和容器名称读取剩余时间。

### Metadata
- Source: verified_diagnostic
- Related Files: plugins/colcontainers/backend.py, plugins/colcontainers/ui/ColcontainersView.vue
- Tags: desc, api, bearer-token, container-renewal

### Resolution
- **Resolved**: 2026-10-15T15:40:00+08:00
- **Notes**: 已依据当前站点 bundle 和未认证接口响应完成协议核对，并接入插件后端。

---

## [LRN-20261016-001] dashboard_card_navigation

**Logged**: 2026-10-16
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
单一仪表盘同时承载全部插件界面时，每张插件卡片需要成为完整功能容器，左侧导航通过卡片标识执行滚动定位。

### Details
主容器直接遍历插件清单并渲染对应的动态 Vue 组件，插件导航按钮使用 `scrollIntoView` 定位卡片。卡片需要保留唯一 `id`、滚动顶部间距和启用状态控制，才能在全部界面同时显示时保持导航清晰。

### Suggested Action
新增插件时继续将页面组件放入对应插件目录，并确认 manifest 中的 `view` 可以被主容器加载；卡片标识使用插件 `id` 生成，导航逻辑只依赖该标识。

### Metadata
- Source: user_feedback
- Related Files: src/App.vue, src/style.css, src/plugin-views.js
- Tags: frontend, dashboard, plugin-card, scroll-navigation

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成全部插件卡片嵌入、滚动导航和卡片样式调整，并通过前端构建与客户端打包验证。

---

## [LRN-20261016-002] colpilot_owned_plugin_processes

**Logged**: 2026-10-16
**Priority**: critical
**Status**: resolved
**Area**: backend

### Summary
插件创建的全部外部进程必须登记到 Colpilot 的生命周期管理中，Colmon 功能需要直接由插件维护三个任务栏窗口。

### Details
Colmon 插件应在 Colpilot 后端中管理窗口创建、状态读取、窗口更新和窗口关闭。插件启动的 worker、监控程序和辅助程序都需要由统一的进程管理器登记，Colpilot 退出时按照插件顺序停止并等待进程结束。

### Suggested Action
建立统一的受管进程登记与关闭接口，为持续运行插件提供关闭方法；退出路径同时覆盖正常关闭、窗口关闭事件、后端异常和插件重新加载。

### Metadata
- Source: user_feedback
- Related Files: backend/main.py, plugins/colmon/backend.py, src-tauri/src/lib.rs
- Tags: process-lifecycle, plugin, colmon, shutdown

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已加入进程登记表、插件退出清理、Windows Job Object 子进程归属和三个原生任务栏窗口；Python 生命周期测试、真实子进程回收测试、Rust 检查与 portable 构建均已通过。

---

## [LRN-20261016-003] colmon_native_window_architecture_comparison

**Logged**: 2026-10-16T15:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
任务栏窗口显示问题需要同时核对窗口生命周期、跨进程挂载、DPI 感知、任务栏子窗口遮挡和实际绘制区域。

### Details
Colmon 使用带 `PerMonitorV2` manifest 的 WinForms UI 线程，通过 `Form.Show()` 创建窗口，调用 `SetParent` 挂载到任务栏，并依据实际任务栏子窗口占用区域计算位置。Colpilot 的 colmon 插件现在启动独立的 WinForms 原生窗口宿主，使用标准控件绘制三个窗口；Python 层通过 JSON 标准输入输出传递显示数据、句柄、可见性、祖先关系、DPI 和实际矩形。窗口宿主由插件进程登记表管理，窗口宿主退出或插件停止时会执行清理。

### Suggested Action
继续以原生 WinForms 宿主承载任务栏窗口，发布 portable 客户端时复制自包含单文件宿主；插件状态文件保存窗口实际信息，插件退出流程负责关闭窗口宿主及其查询进程。

### Metadata
- Source: user_feedback | verified_diagnostic
- Related Files: plugins/colmon/taskbar.py, src-tauri/tauri.conf.json, D:/ColboiIN/code/Colmon/src/Colmon.App/TaskbarHostForm.cs, D:/ColboiIN/code/Colmon/src/Colmon.App/app.manifest
- Tags: colmon, taskbar, hwnd, dpi, win32, architecture
- See Also: LRN-20261016-002

### Resolution
- **Resolved**: 2026-10-16T17:40:00+08:00
- **Notes**: 已完成独立 WinForms 窗口宿主、任务栏附着验证、portable 单文件复制和插件停止回收测试；用户已经确认三个窗口可以显示。

---

## [LRN-20261016-004] colmon_data_isolation_and_bounded_shutdown

**Logged**: 2026-10-16
**Priority**: critical
**Status**: resolved
**Area**: backend

### Summary
任务栏用量读取与进程退出需要分别管理每个窗口的数据状态，并为外部进程关闭设置明确时间上限。

### Details
两个配额窗口可以共享一次 `account/rateLimits/read` 查询，减少初次显示等待。单个窗口的数据错误应写入该窗口状态，不能阻止其他窗口显示有效数据。Colmon 查询进程、窗口宿主和后端退出流程都需要使用有时间上限的等待。

### Suggested Action
新增数据读取时，保留每个窗口的状态边界；新增外部进程关闭路径时，使用进程树关闭、限定等待时间和最终进程终止，并检查进程登记表是否清空。

### Metadata
- **Source**: user_feedback | verified_diagnostic
- **Related Files**: backend/process_manager.py, plugins/colmon/backend.py, plugins/colmon/native_host.py, plugins/colmon/taskbar.py, src-tauri/src/lib.rs
- **Tags**: colmon, quota, process-lifecycle, shutdown

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成共享查询、窗口级错误状态、任务栏窗口隐藏关闭、限定时长的进程清理，并通过真实开发环境与 portable 后端验证。

---

## [LRN-20261016-005] codex_versioned_command_discovery

**Logged**: 2026-10-16
**Priority**: critical
**Status**: resolved
**Area**: backend

### Summary
portable 程序启动时，Codex 可执行文件可能位于 `OpenAI/Codex/bin/<version>/codex.exe`，用户进程继承的 `PATH` 不一定包含该目录。

### Details
真实运行中的 Colpilot 能够读取 sessions 文件，却无法读取两个配额窗口；插件状态显示“没有找到 Codex App Server 可执行文件”。在去除 Codex 目录的 `PATH` 后，原命令定位返回空列表；系统安装文件位于版本目录中。

### Suggested Action
Codex 命令候选路径需要包含 `LOCALAPPDATA/OpenAI/Codex/bin` 下的版本目录，并按照文件更新时间优先选择候选文件。

### Metadata
- **Source**: user_feedback | verified_diagnostic
- **Related Files**: plugins/colmon/taskbar.py, scripts/build-client.ps1
- **Tags**: colmon, codex, portable, command-discovery

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已加入版本目录搜索；重新构建并启动 portable 客户端后，两个配额窗口与 token 窗口均返回有效数据。

---

## [LRN-20261016-006] tauri_frontend_backend_connection

**Logged**: 2026-10-16
**Priority**: critical
**Status**: resolved
**Area**: frontend

### Summary
桌面页面访问本地服务时，需要使用 Tauri 运行时提供的后端地址，并让请求头与请求内容保持一致。

### Details
Tauri 页面调用本地 FastAPI 服务时，页面来源、后端端口和服务启动时序都会影响请求结果。GET 请求附加 JSON 类型会触发 CORS 预检；WebView 访问回环地址时还可能发送私有网络预检；页面固定写入端口会让端口调整和多种运行方式缺少统一来源。

### Suggested Action
通过 `get_backend_url` 获取运行中的后端地址；只有存在请求体时设置 `Content-Type: application/json`；为本地 Tauri 页面来源启用完整 CORS 和私有网络预检；使用真实 HTTP 请求和预检请求验证页面访问链路。

### Metadata
- **Source**: user_feedback | verified_diagnostic
- **Related Files**: src/App.vue, backend/main.py, src-tauri/src/lib.rs
- **Tags**: tauri, frontend, backend, cors, fetch

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成前端请求地址动态获取、请求头调整、本地页面来源配置和私有网络预检配置，并通过 portable 客户端的接口请求与 CORS 预检检查。

---

## [LRN-20261016-007] sidebar_branding_position

**Logged**: 2026-10-16
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
Colpilot 程序名和设置入口需要固定放在左侧栏顶部，插件导航从其下方开始。

### Details
主界面采用单一仪表盘时，左侧栏承担程序识别和插件快速导航两项职责。品牌区域应位于侧栏顶部，设置按钮与程序名处于同一行，插件导航保持在下方。

### Suggested Action
将品牌标题和设置按钮放入 `.sidebar-header`，移除主内容区域的顶部标题栏，并通过侧栏间距保持品牌区域与插件导航之间的清晰层次。

### Metadata
- **Source**: user_feedback
- **Related Files**: src/App.vue, src/style.css
- **Tags**: frontend, sidebar, branding, navigation

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成左侧栏顶部品牌区域和设置按钮布局，并通过 Vite 与 portable 客户端构建检查。

---

## [LRN-20261016-008] pointer_drag_preview_in_webview

**Logged**: 2026-10-16
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
桌面 WebView 中的插件排序需要由指针事件直接维护拖拽状态、放置目标和跟随光标的预览元素。

### Details
浏览器原生拖拽会自行决定拖动光标和放置状态，按钮元素在桌面 WebView 中可能持续显示禁止光标，拖拽预览也无法稳定控制。指针事件可以在达到移动阈值后进入拖拽状态，按需切换 `grabbing` 光标，并使用克隆导航项作为跟随光标的预览元素。刷新列表需要在拖动期间暂停，避免更新列表状态影响目标判定。

### Suggested Action
使用 `pointerdown`、`pointermove`、`pointerup` 和 `pointercancel` 管理排序；为拖拽预览元素设置 `pointer-events: none`；保存顺序期间继续暂停插件列表刷新。

### Metadata
- **Source**: user_feedback | verified_diagnostic
- **Related Files**: src/App.vue, src/style.css, artifacts/test_plugin_drag.ps1
- **Tags**: frontend, pointer-events, drag-preview, webview, plugin-order

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成指针事件排序、拖拽预览、光标状态和拖动期间刷新暂停，并通过源码契约检查、Vite 构建和完整桌面客户端构建验证。

---

## [LRN-20261016-009] plugin_drop_gap_feedback

**Logged**: 2026-10-16
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
插件排序的拖拽目标应显示为插件之间的插入空隙。

### Details
拖拽中的插件按钮用于显示当前被抓取的项目。排序目标需要使用原始列表中的插入位置编号，界面在对应空隙显示高亮，覆盖首项之前、项目之间和末项之后的位置。保存顺序时，源项目移除后按照插入位置修正索引。

### Suggested Action
使用 `dropGapIndex` 管理插入位置；在侧栏项目之间渲染空隙元素；将高亮样式绑定到空隙元素，并让目标计算只读取侧栏中的实际插件按钮。

### Metadata
- **Source**: user_feedback | verified_diagnostic
- **Related Files**: src/App.vue, src/style.css, artifacts/test_plugin_drag.ps1
- **Tags**: frontend, drag-and-drop, drop-gap, plugin-order

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成插入空隙状态、空隙高亮和插入位置排序保存，并通过回归检查、Vite 构建和完整桌面客户端构建验证。

---

## [LRN-20261016-010] keep_local_plugin_out_of_main_sync

**Logged**: 2026-10-16
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
用户要求取消 `colmon` 与 Colpilot 主仓库同步，同时保留本地插件目录。

### Details
插件目录可以通过根目录 `.gitignore` 保持本地状态，同时从 Git 索引移除。构建脚本需要根据本地插件目录是否存在来处理对应的原生宿主文件，这样远程仓库可以独立构建，本地开发目录仍然可以继续构建和使用 `colmon`。

### Suggested Action
对于仅供本地使用的插件，提交前检查 Git 索引、远程目录和本地文件路径，并让构建流程支持插件目录缺失的情况。

### Metadata
- **Source**: user_feedback | verified_diagnostic
- **Related Files**: .gitignore, scripts/build-client.ps1, plugins/colmon
- **Tags**: git, plugin, local-only, packaging

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已从 Colpilot 主仓库提交和远程分支移除 `colmon`，本地目录仍然存在并由忽略规则保护；构建脚本已支持本地目录存在与缺失两种情况。

---

## [LRN-20261016-011] user_facing_readme_scope

**Logged**: 2026-10-16
**Priority**: high
**Status**: resolved
**Area**: docs

### Summary
根目录 README 面向最终用户，内容应集中在安装、使用、配置、退出和常见问题。

### Details
用户文档不应加入开发工具、依赖安装命令或具体插件清单。插件专属功能与配置说明继续放在各插件自己的 README 中，根目录文档只保留使用 Colpilot 所需的通用说明。

### Suggested Action
更新根目录 README 时检查用户操作路径，移除开发流程内容，并避免写入具体插件的产品说明。

### Metadata
- **Source**: user_feedback
- **Related Files**: README.md, plugins/*/README.md
- **Tags**: documentation, user-guide, plugin-boundary

### Resolution
- **Resolved**: 2026-10-16
- **Notes**: 已完成用户版 README 重写，并通过文本检查确认开发内容、具体插件名称和预装说明均已移除。

---

## [LRN-20261019-001] distribution_directory

**Logged**: 2026-10-19
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
构建输出统一为 `target/Colpilot`，用户将该目录中的内容直接覆盖到原程序目录完成更新。

### Details
发布目录包含主程序、运行环境和插件运行文件。构建时排除个人配置、运行数据、日志、缓存和开发文档；插件程序文件随主程序一起更新。

### Suggested Action
构建后使用旧程序目录的真实副本验证覆盖更新，核对配置和插件数据内容，并验证更新后的程序及窗口宿主能够启动。

### Metadata
- Source: user_feedback
- Related Files: scripts/build-client.ps1, README.md
- Tags: build, distribution, update

---

## [LRN-20261019-002] desc_authentication_verification

**Logged**: 2026-10-19
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
DESC 登录验证需要核对服务端响应和当前网站提交的请求内容。

### Details
当前网站通过 `POST /api/user/validate` 提交包含 `username`、`password` 的 JSON，密码直接使用输入内容。服务端拒绝登录信息时返回 HTTP 401，响应类型为 `text/plain`，内容为 `Authentication failed`。验证记录只保留状态和响应说明，不保存账号、密码和 token。

真实账号验证包含登录、用户信息、容器列表及剩余时间读取，全部请求返回 HTTP 200。安装目录中的账号设置通过程序设置接口保存，并检查保存内容与授权测试信息是否一致；验证输出仅记录比较结果。运行状态应为 `running`、认证状态应为成功、同步错误应为空，自动续约保持关闭。

### Suggested Action
登录诊断使用用户授权的真实账号，比较请求地址、字段和服务端响应。只有登录成功后才验证用户信息与容器读取，自动续约保持关闭。

### Metadata
- Source: verified_diagnostic
- Related Files: plugins/coldesc/backend.py
- Tags: desc, authentication, credentials

---

## [LRN-20261019-003] desc_refresh_and_account_controls

**Logged**: 2026-10-19
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
账号表单通过保存按钮提交；DESC 登录失败后保留修改与重试操作，资料获取与剩余时间获取分别调度。

### Details
容器资料默认每 259200 秒获取，剩余时间默认每 600 秒获取。页面依据服务端到期时间与本地经过时间，每秒显示倒计时。登录、重新登录、手动获取和续约触发相应信息更新。插件后端可用时，插件页面保持可操作。

### Suggested Action
使用真实服务检查登录拒绝与恢复、保存相同账号后的重新登录、两个间隔的独立请求次数和倒计时期间的请求次数。完整程序验证包含账号按钮、窗口控制及滚动条，原程序配置通过文件校验确认保持不变。

### Metadata
- Source: verified_diagnostic
- Related Files: plugins/coldesc/backend.py, plugins/coldesc/ui/ColdescView.vue, plugins/colszunet/ui/ColszunetView.vue, src/App.vue, src/WindowTitleBar.vue, src/style.css
- Tags: desc, refresh, countdown, credentials, window

---

## [LRN-20261024-001] best_practice

**Logged**: 2026-10-24
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
任务栏插件需要独立的窗口线程响应检查、持续保存的错误日志和 Windows 故障事件记录。

### Details
Colpilot 的桌面程序、Python 后端和 WinForms 窗口宿主分别保存轮换日志。窗口宿主使用独立线程检查 UI 响应，记录当前操作及耗时。定期检查同时读取接口状态、任务栏响应、数据更新时间、新增 Windows 故障事件和检查区间内的错误日志。

### Suggested Action
程序更新前后校验用户配置与运行数据，异常归档保存在 artifacts/monitoring；完成异常分析与修复后重新设置检查起点。

### Metadata
- Source: verified_diagnostic
- Related Files: backend/diagnostics.py, plugins/colmon/native/NativeDiagnostics.cs, scripts/check-colpilot.ps1, scripts/deploy-client.ps1
- Tags: colmon, diagnostics, taskbar, monitoring

## [LRN-20261027-001] best_practice

**Logged**: 2026-10-27
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
任务栏窗口线程提交输出消息时需要独立发送线程、队列容量限制和通信超时终止。

### Details
Windows 文件句柄占用可以阻止状态文件替换。输出处理失败时必须终止宿主，保留错误原因。真实文件占用与管道停止读取测试已经验证宿主及时终止，输出阻塞期间窗口线程保持响应。

### Suggested Action
涉及窗口宿主通信的修改执行 scripts/verify-colmon-communication.py 与 scripts/verify-native-diagnostics.py。

### Metadata
- Source: verified_diagnostic
- Related Files: plugins/colmon/native_host.py, plugins/colmon/native/Program.cs, plugins/colmon/native/NativeDiagnostics.cs, scripts/verify-colmon-communication.py
- Tags: colmon, communication, file-sharing, responsiveness

## [LRN-20261028-001] best_practice

**Logged**: 2026-10-28
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
可重新生成的窗口状态文件在同一把进程内锁中完成读写，并保留原文件。

### Details
真实 Windows 读取句柄持续打开测试验证了状态更新与并发接口查询正常；禁止写入共享的句柄验证了保存失败时宿主及时终止。对应验证保存在 scripts/verify-colmon-communication.py。

### Suggested Action
更改状态文件处理时执行真实文件共享、并发状态查询和管道通信验证。

### Metadata
- Source: verified_diagnostic
- Related Files: plugins/colmon/native_host.py, plugins/colmon/backend.py, scripts/verify-colmon-communication.py
- Tags: colmon, state-files, windows-sharing
