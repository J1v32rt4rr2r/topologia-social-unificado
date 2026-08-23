$env:PYTHONIOENCODING = "utf-8"
$Ruta = $PSScriptRoot
Set-Location -LiteralPath $Ruta
$Log = "$Ruta\data\logs\supervision_diaria_$(Get-Date -Format 'yyyy-MM-dd').log"
$null = New-Item -ItemType Directory -Path (Split-Path $Log) -Force
& "C:\Python314\python.exe" scripts\supervisar_ciclo.py *>> $Log
exit $LASTEXITCODE