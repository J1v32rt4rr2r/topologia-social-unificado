$env:PYTHONIOENCODING = "utf-8"
$Ruta = $PSScriptRoot
$Log = "$Ruta\data\logs\ciclo_$(Get-Date -Format 'yyyy-MM-dd').log"
$null = New-Item -ItemType Directory -Path (Split-Path $Log) -Force
& "C:\Python314\python.exe" -m topologia.main daily *>> $Log
$Reportes = "$env:USERPROFILE\.local\share\topologia-social\data\reportes"
$Ultimo = Get-ChildItem "$Reportes\informe_*.html" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($Ultimo) {
    Copy-Item -LiteralPath $Ultimo.FullName -Destination "$([Environment]::GetFolderPath('Desktop'))\informe_topologia.html" -Force
}
