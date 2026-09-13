$env:PYTHONIOENCODING = "utf-8"
$Ruta = $PSScriptRoot
Set-Location -LiteralPath $Ruta

$ES_CONTINUOUS      = [uint32]2147483648
$ES_SYSTEM_REQUIRED = [uint32]1
$HoldActivo = $false
try {
    Add-Type -Namespace Win32 -Name Power -MemberDefinition '
[DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);' -ErrorAction Stop
    $Previo = [Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED)
    if ($Previo -ne 0) { $HoldActivo = $true }
} catch { }

try {
    $Log = "$env:USERPROFILE\.local\share\topologia-social\data\logs\ciclo_$(Get-Date -Format 'yyyy-MM-dd').log"
    $null = New-Item -ItemType Directory -Path (Split-Path $Log) -Force
    & "C:\Python314\python.exe" -m topologia.main daily *>> $Log
    $Reportes = "$env:USERPROFILE\.local\share\topologia-social\data\reportes"
    $Ultimo = Get-ChildItem "$Reportes\informe_*.html" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($Ultimo) {
        Copy-Item -LiteralPath $Ultimo.FullName -Destination "$([Environment]::GetFolderPath('Desktop'))\informe_topologia.html" -Force
    }
}
finally {
    if ($HoldActivo) {
        $null = [Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS)
    }
}
