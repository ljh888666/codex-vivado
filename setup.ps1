# machine=PC2; Windows PowerShell 5.1 requires this file's UTF-8 BOM.
[CmdletBinding()]
param(
    [string]$Python = 'D:/vivado-mcp/codex/.venv/Scripts/python.exe',
    [string]$Vivado = '',
    [string]$Part = 'xcku060-ffva1156-2-i',
    [switch]$SkipNative,
    [switch]$SkipMcp
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Set -Python to an interpreter with vivado-mcp installed.'
}
Push-Location -LiteralPath $PSScriptRoot
try {
    $configure = @('-B','-X','utf8','tools/configure.py','--python',$Python,'--part',$Part)
    if ($Vivado) { $configure += @('--vivado',$Vivado) }
    & $Python @configure
    if ($LASTEXITCODE -ne 0) { throw 'Configuration failed.' }
    & $Python -B -X utf8 tools/doctor.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment check failed.' }
    if (-not $SkipMcp) {
        & $Python -B -X utf8 tools/smoke_mcp.py
        if ($LASTEXITCODE -ne 0) { throw 'MCP smoke check failed.' }
    }
    if (-not $SkipNative) {
        & $Python -B -X utf8 tools/verify_native.py
        if ($LASTEXITCODE -ne 0) { throw 'Isolated native plugin check failed.' }
    }
    Write-Output 'machine=PC2 PREPARE_OK: local marketplace ready; daily CODEX_HOME unchanged.'
} finally {
    Pop-Location
}