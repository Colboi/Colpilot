$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$outputRoot = Join-Path $projectRoot 'target'
$portableRoot = Join-Path $outputRoot 'Colpilot'
$releaseRoot = Join-Path $projectRoot 'src-tauri\target\release'
$runtimeSource = Join-Path $projectRoot '.venv'
$runtimeBuilderPython = Join-Path $runtimeSource 'Scripts\python.exe'
$pluginSourceRoot = Join-Path $projectRoot 'plugins'
$pluginPackageInitSource = Join-Path $pluginSourceRoot '__init__.py'
$backendScriptSource = Join-Path $projectRoot 'backend\main.py'
$backendConfigStoreSource = Join-Path $projectRoot 'backend\user_config.py'
$backendProcessManagerSource = Join-Path $projectRoot 'backend\process_manager.py'
$backendPluginManagerSource = Join-Path $projectRoot 'backend\plugin_manager.py'
$backendPluginRuntimeSource = Join-Path $projectRoot 'backend\plugin_runtime.py'
$backendSettingsSource = Join-Path $projectRoot 'backend\settings.py'
$backendDiagnosticsSource = Join-Path $projectRoot 'backend\diagnostics.py'
$backendRequirementsSource = Join-Path $projectRoot 'backend\requirements.txt'
$portableBackendRoot = Join-Path $portableRoot 'backend'
$portableRuntimeRoot = Join-Path $portableRoot 'runtime'
$portablePluginsRoot = Join-Path $portableRoot 'plugins'

function Assert-ProjectPath {
    param([string]$Path)
    $absolutePath = [System.IO.Path]::GetFullPath($Path)
    if (-not $absolutePath.StartsWith($projectRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "生成文件目录超出项目范围：$absolutePath"
    }
    if ((Get-Item -LiteralPath $absolutePath -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "生成文件目录包含链接：$absolutePath"
    }
}

function Copy-PluginFiles {
    param(
        [string]$SourceRoot,
        [string]$DestinationRoot,
        [string]$RelativeRoot = ''
    )

    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
    foreach ($item in (Get-ChildItem -LiteralPath $SourceRoot -Force)) {
        $relativePath = if ($RelativeRoot) { "$RelativeRoot/$($item.Name)" } else { $item.Name }
        if ($item.Name -in @('.git', '.learnings', '.vscode', '__pycache__', 'data', 'node_modules', '.venv')) {
            continue
        }
        if ($relativePath -in @('native/bin', 'native/obj', 'native/publish')) {
            continue
        }
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "插件发布文件不能包含链接：$($item.FullName)"
        }
        $destination = Join-Path $DestinationRoot $item.Name
        if ($item.PSIsContainer) {
            Copy-PluginFiles -SourceRoot $item.FullName -DestinationRoot $destination -RelativeRoot $relativePath
        } elseif (
            $item.Name -notin @('config.ini', 'settings.json', 'AGENTS.md', 'CLAUDE.md', '.gitignore', '.gitattributes') -and
            $item.Name -notlike '.env*' -and
            $item.Extension -notin @('.pyc', '.pyo', '.log', '.tmp')
        ) {
            Copy-Item -LiteralPath $item.FullName -Destination $destination
        }
    }
}

Set-Location -LiteralPath $projectRoot
& (Join-Path $projectRoot 'node_modules\.bin\tauri.cmd') build --no-bundle
if ($LASTEXITCODE -ne 0) {
    throw "客户端构建失败，退出代码为 $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $runtimeBuilderPython -PathType Leaf)) {
    throw "本地 Python 构建解释器不存在：$runtimeBuilderPython"
}

$baseRuntimeRootText = (& $runtimeBuilderPython -c "import sys; print(sys.base_prefix)").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($baseRuntimeRootText)) {
    throw "无法读取 Python 基础运行目录"
}
$baseRuntimeRoot = (Resolve-Path -LiteralPath $baseRuntimeRootText).Path
$baseRuntimeLibRoot = Join-Path $baseRuntimeRoot 'Lib'
$baseRuntimeDllRoot = Join-Path $baseRuntimeRoot 'DLLs'
$baseRuntimeLibraryBin = Join-Path $baseRuntimeRoot 'Library\bin'
$venvSitePackages = Join-Path $runtimeSource 'Lib\site-packages'
$portableLibraryDllNames = @(
    'libcrypto-3-x64.dll',
    'libssl-3-x64.dll',
    'ffi-7.dll',
    'ffi-8.dll',
    'ffi.dll',
    'sqlite3.dll',
    'zlib.dll',
    'libbz2.dll',
    'liblzma.dll',
    'libexpat.dll',
    'charset.dll',
    'iconv.dll',
    'libzstd.dll',
    'yaml-cpp.dll'
)
$portableLibraryDllSources = @(
    $portableLibraryDllNames | ForEach-Object { Join-Path $baseRuntimeLibraryBin $_ }
)

$artifactSources = @(
    (Join-Path $releaseRoot 'colpilot.exe')
)
$portableSources = @(
    $backendScriptSource,
    $backendConfigStoreSource,
    $backendProcessManagerSource,
    $backendPluginManagerSource,
    $backendPluginRuntimeSource,
    $backendSettingsSource,
    $backendDiagnosticsSource,
    $backendRequirementsSource,
    (Join-Path $baseRuntimeRoot 'python.exe'),
    (Join-Path $baseRuntimeRoot 'pythonw.exe'),
    $baseRuntimeLibRoot,
    $baseRuntimeDllRoot,
    $venvSitePackages,
    $portableLibraryDllSources,
    $pluginPackageInitSource
)

foreach ($sourcePath in @($artifactSources + $portableSources)) {
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "客户端文件不存在：$sourcePath"
    }
}

if (Test-Path -LiteralPath $outputRoot) {
    if ((Resolve-Path -LiteralPath $outputRoot).Path -ne (Join-Path $projectRoot 'target')) {
        throw '构建输出目录与项目 target 目录不一致'
    }
    foreach ($outputItem in (Get-ChildItem -LiteralPath $outputRoot -Force)) {
        Assert-ProjectPath $outputItem.FullName
        Remove-Item -LiteralPath $outputItem.FullName -Recurse -Force
    }
} else {
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
}

New-Item -ItemType Directory -Path $portableRoot,$portableBackendRoot,$portableRuntimeRoot,$portablePluginsRoot -Force | Out-Null
Copy-Item -LiteralPath $artifactSources[0] -Destination (Join-Path $portableRoot 'colpilot.exe')

Copy-Item -LiteralPath $backendScriptSource -Destination (Join-Path $portableBackendRoot 'main.py')
Copy-Item -LiteralPath $backendConfigStoreSource -Destination (Join-Path $portableBackendRoot 'user_config.py')
Copy-Item -LiteralPath $backendProcessManagerSource -Destination (Join-Path $portableBackendRoot 'process_manager.py')
Copy-Item -LiteralPath $backendPluginManagerSource -Destination (Join-Path $portableBackendRoot 'plugin_manager.py')
Copy-Item -LiteralPath $backendPluginRuntimeSource -Destination (Join-Path $portableBackendRoot 'plugin_runtime.py')
Copy-Item -LiteralPath $backendSettingsSource -Destination (Join-Path $portableBackendRoot 'settings.py')
Copy-Item -LiteralPath $backendDiagnosticsSource -Destination (Join-Path $portableBackendRoot 'diagnostics.py')
Copy-Item -LiteralPath $backendRequirementsSource -Destination (Join-Path $portableBackendRoot 'requirements.txt')
foreach ($runtimeFile in (Get-ChildItem -LiteralPath $baseRuntimeRoot -Filter '*.dll' -File)) {
    Copy-Item -LiteralPath $runtimeFile.FullName -Destination $portableRuntimeRoot -Force
}
foreach ($runtimeFile in (Get-ChildItem -LiteralPath $baseRuntimeRoot -Filter 'python*.exe' -File)) {
    Copy-Item -LiteralPath $runtimeFile.FullName -Destination $portableRuntimeRoot -Force
}
Copy-Item -LiteralPath $baseRuntimeDllRoot -Destination $portableRuntimeRoot -Recurse -Force
$portableRuntimeLibRoot = Join-Path $portableRuntimeRoot 'Lib'
New-Item -ItemType Directory -Path $portableRuntimeLibRoot -Force | Out-Null
foreach ($runtimeLibItem in (Get-ChildItem -LiteralPath $baseRuntimeLibRoot -Force | Where-Object { $_.Name -notin @('site-packages', '__pycache__') })) {
    Copy-Item -LiteralPath $runtimeLibItem.FullName -Destination $portableRuntimeLibRoot -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $portableRuntimeRoot 'Library\bin') -Force | Out-Null
foreach ($libraryDllSource in $portableLibraryDllSources) {
    Copy-Item -LiteralPath $libraryDllSource -Destination (Join-Path $portableRuntimeRoot 'Library\bin') -Force
}
$portableSitePackagesRoot = Join-Path $portableRuntimeLibRoot 'site-packages'
New-Item -ItemType Directory -Path $portableSitePackagesRoot -Force | Out-Null
foreach ($sitePackageItem in (Get-ChildItem -LiteralPath $venvSitePackages -Force | Where-Object { $_.Name -ne '__pycache__' })) {
    Copy-Item -LiteralPath $sitePackageItem.FullName -Destination $portableSitePackagesRoot -Recurse -Force
}
Copy-Item -LiteralPath $pluginPackageInitSource -Destination (Join-Path $portablePluginsRoot '__init__.py')
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination $portableRoot

# 最终发布目录只保留插件包入口，不打包任何具体插件。开发联调可另行复制插件到验证目录。

$portablePythonCacheDirectories = @(
    Get-ChildItem -LiteralPath $portableRuntimeRoot -Directory -Recurse -Force -Filter '__pycache__' |
        Sort-Object { $_.FullName.Length } -Descending
)
foreach ($cacheDirectory in $portablePythonCacheDirectories) {
    Assert-ProjectPath $cacheDirectory.FullName
    Remove-Item -LiteralPath $cacheDirectory.FullName -Recurse -Force
}
$portablePythonCacheFiles = @(
    Get-ChildItem -LiteralPath $portableRuntimeRoot -File -Recurse -Force -Filter '*.pyc'
)
foreach ($cacheFile in $portablePythonCacheFiles) {
    Remove-Item -LiteralPath $cacheFile.FullName -Force
}

$legacyColmonFiles = @(
    Get-ChildItem -LiteralPath $portableRoot -File -Recurse -Force |
        Where-Object { $_.Name -in @('Colmon.exe', 'colmon.ico') }
)
if ($legacyColmonFiles.Count -gt 0) {
    $legacyColmonPaths = $legacyColmonFiles.FullName -join ', '
    throw "发布目录包含旧的 Colmon 运行文件：$legacyColmonPaths"
}

$portableConfigFiles = @(
    Get-ChildItem -LiteralPath $portableRoot -File -Recurse -Force |
        Where-Object { $_.Name -eq 'config.ini' }
)
if ($portableConfigFiles.Count -gt 0) {
    $configPaths = $portableConfigFiles.FullName -join ', '
    throw "发布目录包含个人配置文件：$configPaths"
}

foreach ($generatedPath in @(
    (Join-Path $projectRoot 'dist'),
    (Join-Path $projectRoot 'src-tauri\target'),
    (Join-Path $projectRoot 'backend\__pycache__'),
    (Join-Path $projectRoot 'plugins')
)) {
    if (Test-Path -LiteralPath $generatedPath) {
        if ($generatedPath -eq (Join-Path $projectRoot 'plugins')) {
            foreach ($cacheDirectory in (Get-ChildItem -LiteralPath $generatedPath -Directory -Recurse -Filter '__pycache__')) {
                Assert-ProjectPath $cacheDirectory.FullName
                Remove-Item -LiteralPath $cacheDirectory.FullName -Recurse -Force
            }
        } else {
            Assert-ProjectPath $generatedPath
            Remove-Item -LiteralPath $generatedPath -Recurse -Force
        }
    }
}

$targetFiles = @(Get-ChildItem -LiteralPath $portableRoot -Recurse -File)
$targetSize = ($targetFiles | Measure-Object -Property Length -Sum).Sum
Write-Output ("Colpilot 已经生成：{0} 个文件，{1} MB，目录：{2}" -f $targetFiles.Count, [math]::Round($targetSize / 1MB, 1), $portableRoot)
