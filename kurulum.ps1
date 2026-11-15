# Yolla icin guvenlik duvari kuralini olusturur: yalnizca 8765 portu,
# yalnizca yerel agdan, yalnizca bu Python. Yonetici izni ister.
param([string]$Python, [int]$Port = 8765)

if (-not $Python) {
    $Python = (& python -c "import sys; print(sys.executable)" 2>$null)
    if (-not $Python) {
        Write-Host "Python bulunamadi. Once https://www.python.org/downloads/ adresinden kur."
        exit 1
    }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Yonetici izni isteniyor..."
    Start-Process powershell -Verb RunAs -Wait -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"",
        '-Python', "`"$Python`"", '-Port', $Port)
    exit
}

Get-NetFirewallRule -DisplayName "Yolla" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "Yolla" -Direction Inbound -Action Allow -Protocol TCP `
    -LocalPort $Port -RemoteAddress LocalSubnet -Program $Python -Profile Any | Out-Null

Write-Host ""
Write-Host "Tamam: $Python icin $Port portu yalnizca yerel aga acildi."
Write-Host "Wi-Fi agini 'Ozel' yapmana gerek yok."
Start-Sleep 3
