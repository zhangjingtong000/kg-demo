param(
  [int]$DurationSeconds = 10,
  [int[]]$TestProcessIds = @()
)

$logicalProcessors = [Environment]::ProcessorCount
$autoTestProcessIds = Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
  Where-Object { $_.CommandLine -match 'playwright_chromiumdev_profile' } |
  Select-Object -ExpandProperty ProcessId
$allTestProcessIds = @($TestProcessIds + $autoTestProcessIds | Sort-Object -Unique)
$before = @{}
Get-Process | ForEach-Object {
  $before[$_.Id] = @{ Name = $_.ProcessName; Cpu = $_.CPU; WorkingSet = $_.WorkingSet64 }
}

$cpuCounter = Get-Counter '\Processor Information(_Total)\% Processor Utility' -SampleInterval 1 -MaxSamples $DurationSeconds
$availableMemory = (Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue
$gpuCounter = Get-Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -MaxSamples 3

$processes = Get-Process | ForEach-Object {
  if (!$before.ContainsKey($_.Id) -or $null -eq $_.CPU -or $null -eq $before[$_.Id].Cpu) { return }
  $deltaCpu = $_.CPU - $before[$_.Id].Cpu
  if ($deltaCpu -le 0) { return }
  [pscustomobject]@{
    Process = $_.ProcessName
    Id = $_.Id
    CpuPercent = [math]::Round(($deltaCpu / ($DurationSeconds * $logicalProcessors)) * 100, 2)
    WorkingSetMB = [math]::Round($_.WorkingSet64 / 1MB, 1)
  }
} | Sort-Object CpuPercent -Descending | Select-Object -First 30

$gpuEngines = $gpuCounter.CounterSamples | Where-Object { $_.CookedValue -gt 0.1 } | Group-Object InstanceName | ForEach-Object {
  $pidMatch = [regex]::Match($_.Name, 'pid_(\d+)_')
  $processId = if ($pidMatch.Success) { [int]$pidMatch.Groups[1].Value } else { -1 }
  [pscustomobject]@{
    ProcessId = $processId
    PeakPercent = [math]::Round((($_.Group | Measure-Object CookedValue -Maximum).Maximum), 1)
  }
}

$nonTestGpuPeak = ($gpuEngines | Where-Object { $allTestProcessIds -notcontains $_.ProcessId } | Measure-Object PeakPercent -Maximum).Maximum
if ($null -eq $nonTestGpuPeak) { $nonTestGpuPeak = 0 }

[pscustomobject]@{
  CapturedAt = (Get-Date).ToString('o')
  DurationSeconds = $DurationSeconds
  LogicalProcessors = $logicalProcessors
  CpuPercent = [math]::Round((($cpuCounter.CounterSamples | Measure-Object CookedValue -Average).Average), 1)
  AvailableMemoryMB = [math]::Round($availableMemory, 0)
  NonTestGpuPeakPercent = $nonTestGpuPeak
  TestProcessIds = $allTestProcessIds
  Processes = $processes
} | ConvertTo-Json -Depth 5
