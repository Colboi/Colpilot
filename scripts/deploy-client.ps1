param([string]$InstallRoot = 'C:\Users\10168\tools\Colpilot')

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$publishRoot = Join-Path $projectRoot 'target\Colpilot'
if (-not (Test-Path -LiteralPath (Join-Path $publishRoot 'colpilot.exe'))) {
    throw '发布目录缺少 colpilot.exe'
}
$installPath = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
$running = @(Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($installPath + '\', [System.StringComparison]::OrdinalIgnoreCase)
})
if ($running.Count -gt 0) { throw '运行目录仍有活动进程，请等待程序退出' }
New-Item -ItemType Directory -Path $installPath -Force | Out-Null
$backupRoot = Join-Path $projectRoot ('artifacts\deployments\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

# 更新前验证配置与日志文件，更新后验证内容保持一致。
$preserved = @{}
foreach ($file in (Get-ChildItem -LiteralPath $installPath -File -Recurse -Force)) {
    if ($file.Name -eq 'config.ini' -or $file.FullName -match '[\\/]data[\\/]') {
        $preserved[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
}
foreach ($relativePath in @('colpilot.exe', 'backend', 'plugins\colmon')) {
    $source = Join-Path $installPath $relativePath
    if (Test-Path -LiteralPath $source) {
        $destination = Join-Path $backupRoot $relativePath
        New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
    }
}
foreach ($file in (Get-ChildItem -LiteralPath $publishRoot -File -Recurse -Force)) {
    $relativePath = [System.IO.Path]::GetRelativePath($publishRoot, $file.FullName)
    if ($file.Name -eq 'config.ini' -or $relativePath -match '(^|[\\/])data([\\/]|$)') {
        throw "发布目录包含用户数据：$relativePath"
    }
    $destination = Join-Path $installPath $relativePath
    New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    if ((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath $destination).Hash) {
        throw "程序文件校验失败：$relativePath"
    }
}
foreach ($path in $preserved.Keys) {
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $preserved[$path]) {
        throw "用户数据校验失败：$path"
    }
}
Write-Output "程序更新完成，已经验证 $($preserved.Count) 个配置或数据文件，备份目录：$backupRoot"
