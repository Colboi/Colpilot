param(
    [string]$InstallRoot = 'C:\Users\10168\tools\Colpilot',
    [switch]$Initialize
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$monitorRoot = Join-Path $projectRoot 'artifacts\monitoring'
New-Item -ItemType Directory -Path $monitorRoot -Force | Out-Null
$checkpointPath = Join-Path $monitorRoot 'checkpoint.json'
$latestEvent = Get-WinEvent -LogName Application -MaxEvents 1
if ($Initialize) {
    @{ eventRecordId = $latestEvent.RecordId; timestamp = (Get-Date).ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath $checkpointPath -Encoding utf8
    Write-Output '已经设置 Windows 事件检查起点'
    exit 0
}
if (-not (Test-Path -LiteralPath $checkpointPath)) {
    throw '请使用 -Initialize 设置 Windows 事件检查起点'
}
$checkpoint = Get-Content -LiteralPath $checkpointPath -Raw | ConvertFrom-Json
$startedAt = (Get-Date).ToString('o')
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$captureRoot = Join-Path $monitorRoot $timestamp
New-Item -ItemType Directory -Path $captureRoot | Out-Null
$issues = [System.Collections.Generic.List[string]]::new()
$processes = @(Get-CimInstance Win32_Process |
    Where-Object { $_.Name -in @('colpilot.exe', 'ColpilotColmonWindows.exe', 'explorer.exe') } |
    Select-Object Name,ProcessId,ParentProcessId,ExecutablePath,CreationDate)
$processes | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $captureRoot 'processes.json') -Encoding utf8
$desktop = @($processes | Where-Object { $_.Name -eq 'colpilot.exe' -and $_.ExecutablePath -eq (Join-Path $InstallRoot 'colpilot.exe') })
if ($desktop.Count -ne 1) { $issues.Add("Colpilot 主程序数量异常：$($desktop.Count)") }

try {
    $health = Invoke-RestMethod 'http://127.0.0.1:37651/api/health' -TimeoutSec 8
    $health | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $captureRoot 'health.json') -Encoding utf8
    $status = Invoke-RestMethod 'http://127.0.0.1:37651/api/plugins/colmon/status' -TimeoutSec 8
    $status | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $captureRoot 'colmon-status.json') -Encoding utf8
    if ($status.runtime.status -ne 'running') { $issues.Add("持续监控状态异常：$($status.runtime.detail)") }
    if (@($status.windows).Count -ne 3) { $issues.Add('持续监控窗口数量异常') }
    foreach ($window in $status.windows) {
        if ($window.status -ne 'ready' -or -not $window.attached) { $issues.Add("窗口异常：$($window.id) $($window.detail)") }
        $maximumAge = [Math]::Max(180, 2 * $status.refresh_interval_seconds + 120)
        if ($null -eq $window.age_seconds -or $window.age_seconds -gt $maximumAge) { $issues.Add("窗口数据更新超时：$($window.id)") }
        if ($window.updated_at) {
            $dataAge = ([DateTimeOffset]::Now - [DateTimeOffset]::Parse($window.updated_at)).TotalSeconds
            if ($dataAge -gt $maximumAge) { $issues.Add("窗口读数更新超时：$($window.id)") }
        } else { $issues.Add("窗口缺少读数更新时间：$($window.id)") }
    }
} catch {
    $issues.Add("读取程序状态失败：$($_.Exception.Message)")
}

if (-not ('ColpilotMonitor.NativeMethods' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace ColpilotMonitor {
    public static class NativeMethods {
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        public static extern IntPtr FindWindow(string className, string title);
        [DllImport("user32.dll")]
        public static extern IntPtr SendMessageTimeout(IntPtr window, uint message, UIntPtr wParam, IntPtr lParam, uint flags, uint timeout, out UIntPtr result);
    }
}
'@
}
$taskbar = [ColpilotMonitor.NativeMethods]::FindWindow('Shell_TrayWnd', $null)
$response = [UIntPtr]::Zero
if ($taskbar -eq [IntPtr]::Zero) {
    $issues.Add('找不到任务栏窗口')
} elseif ([ColpilotMonitor.NativeMethods]::SendMessageTimeout($taskbar, 0, [UIntPtr]::Zero, [IntPtr]::Zero, 2, 2000, [ref]$response) -eq [IntPtr]::Zero) {
    $issues.Add('任务栏超过两秒没有响应')
}

$xpath = "*[System[(EventRecordID > $($checkpoint.eventRecordId)) and (EventID=1000 or EventID=1001 or EventID=1002 or EventID=1026)]]"
$queryErrors = @()
$events = @(Get-WinEvent -LogName Application -FilterXPath $xpath -ErrorAction SilentlyContinue -ErrorVariable queryErrors)
foreach ($queryError in $queryErrors) {
    if ($queryError.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*') { throw $queryError }
}
$relatedEvents = @($events | Where-Object { $_.Message -match '(?i)explorer\.exe|colpilot|ColpilotColmonWindows' })
$relatedEvents | Select-Object TimeCreated,Id,RecordId,ProviderName,Message |
    ConvertTo-Json -Depth 5 | Set-Content (Join-Path $captureRoot 'windows-events.json') -Encoding utf8
foreach ($event in $relatedEvents) { $issues.Add("Windows 记录异常：$($event.TimeCreated) event=$($event.Id) record=$($event.RecordId)") }

# 检查期间出现的错误会触发日志归档。
foreach ($logDirectory in @('data\logs', 'plugins\colmon\data\logs')) {
    $source = Join-Path $InstallRoot $logDirectory
    if (Test-Path -LiteralPath $source) {
        foreach ($logFile in (Get-ChildItem -LiteralPath $source -File -Filter '*.log*')) {
            foreach ($line in (Get-Content -LiteralPath $logFile.FullName)) {
                if ($line -match '^(?<time>\d{4}-\d{2}-\d{2}T\S+) (?:(?:ERROR|CRITICAL)\b|.*\[(?:ERR|FTL|ERROR)\])') {
                    $loggedAt = [DateTimeOffset]::Parse($Matches.time)
                } elseif ($line -match '^\[(?<date>\d{4}-\d{2}-\d{2})\]\[(?<time>\d{2}:\d{2}:\d{2})\].*\[ERROR\]') {
                    $loggedAt = [DateTimeOffset]::Parse("$($Matches.date)T$($Matches.time)+08:00")
                } else { continue }
                if ($loggedAt -gt [DateTimeOffset]::Parse($checkpoint.timestamp)) {
                    $issues.Add("日志记录异常：$($logFile.Name) $line")
                }
            }
        }
    }
}
if ($issues.Count -gt 0) {
    foreach ($logDirectory in @('data\logs', 'plugins\colmon\data\logs', 'plugins\colmon\data\artifacts')) {
        $source = Join-Path $InstallRoot $logDirectory
        if (Test-Path -LiteralPath $source) {
            $destination = Join-Path $captureRoot $logDirectory
            New-Item -ItemType Directory -Path $destination -Force | Out-Null
            foreach ($file in (Get-ChildItem -LiteralPath $source -File)) {
                Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
            }
        }
    }
}
$result = [ordered]@{
    timestamp = (Get-Date).ToString('o')
    healthy = $issues.Count -eq 0
    issues = @($issues.ToArray())
    captureRoot = $captureRoot
    previousEventRecordId = $checkpoint.eventRecordId
    latestEventRecordId = $latestEvent.RecordId
}
$result | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $captureRoot 'result.json') -Encoding utf8
$result | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $monitorRoot 'latest.json') -Encoding utf8
if ($issues.Count -eq 0) {
    @{ eventRecordId = $latestEvent.RecordId; timestamp = $startedAt } |
        ConvertTo-Json | Set-Content -LiteralPath $checkpointPath -Encoding utf8
}
$result | ConvertTo-Json -Depth 8
if ($issues.Count -gt 0) { exit 1 }
