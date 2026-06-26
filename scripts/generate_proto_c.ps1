$ErrorActionPreference = "Stop"

function Update-AlpcomExports {
    $alpcomDir = Join-Path $repoRoot "alpcom"
    $generatedC = Join-Path $repoRoot "generated/c"
    $headerPath = Join-Path $alpcomDir "alpcom.h"

    New-Item -ItemType Directory -Force -Path $alpcomDir | Out-Null

    $headerLines = @(
        "#ifndef ALPCOM_H",
        "#define ALPCOM_H",
        "",
        "#include ""../communication_protocol.h""",
        "#include ""../alp_stream_parser.h""",
        "#include ""../alpcom/alp_message_ids.h"""
    )

    if (Test-Path $generatedC) {
        $protoHeaders = Get-ChildItem -Path $generatedC -Filter *.pb.h | Sort-Object Name
        foreach ($header in $protoHeaders) {
            $headerLines += "#include ""../generated/c/$($header.Name)"""
        }
    }

    $headerLines += ""
    $headerLines += "#endif"

    Set-Content -Path $headerPath -Value ($headerLines -join "`r`n")
    Write-Host "C umbrella header updated: alpcom/alpcom.h"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$nanopbGenerator = $env:NANOPB_GENERATOR

if (-not $nanopbGenerator) {
    $candidate = Join-Path (Split-Path (Get-Command python | Select-Object -ExpandProperty Source)) "Scripts\nanopb_generator.exe"
    if (Test-Path $candidate) {
        $nanopbGenerator = $candidate
    }
}

if (-not (Test-Path $nanopbGenerator)) {
    throw "Nanopb generator not found. Set NANOPB_GENERATOR to nanopb_generator.py or nanopb_generator.exe."
}

Push-Location $repoRoot

try {
    New-Item -ItemType Directory -Force -Path "generated/c" | Out-Null
    & $nanopbGenerator --output-dir=generated/c -I proto proto/example.proto
    Update-AlpcomExports
    Write-Host "C protobuf generated: generated/c/example.pb.h and generated/c/example.pb.c"
}
finally {
    Pop-Location
}
