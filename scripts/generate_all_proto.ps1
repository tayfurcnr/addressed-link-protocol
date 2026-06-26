$ErrorActionPreference = "Stop"

& "$PSScriptRoot\generate_proto_python.ps1"

if ($env:NANOPB_GENERATOR) {
    & "$PSScriptRoot\generate_proto_c.ps1"
}
else {
    Write-Host "Skipping C generation. Set NANOPB_GENERATOR to enable nanopb output."
}
