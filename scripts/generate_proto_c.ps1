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

function Update-ArduinoExports {
    $srcDir = Join-Path $repoRoot "src"
    $generatedC = Join-Path $repoRoot "generated/c"
    $headerPath = Join-Path $srcDir "alpcom.h"

    New-Item -ItemType Directory -Force -Path $srcDir | Out-Null

    Get-ChildItem -Path $srcDir -Filter *.pb.h -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem -Path $srcDir -Filter *.pb.c -ErrorAction SilentlyContinue | Remove-Item -Force

    if (Test-Path $generatedC) {
        $generatedHeaders = Get-ChildItem -Path $generatedC -Filter *.pb.h | Sort-Object Name
        foreach ($header in $generatedHeaders) {
            $wrapperPath = Join-Path $srcDir $header.Name
            Set-Content -Path $wrapperPath -Value "#include ""../generated/c/$($header.Name)""" -NoNewline
        }

        $generatedSources = Get-ChildItem -Path $generatedC -Filter *.pb.c | Sort-Object Name
        foreach ($source in $generatedSources) {
            $wrapperPath = Join-Path $srcDir $source.Name
            Set-Content -Path $wrapperPath -Value "#include ""../generated/c/$($source.Name)""" -NoNewline
        }
    }

    $headerLines = @(
        "#ifndef ARDUINO_ALPCOM_H",
        "#define ARDUINO_ALPCOM_H",
        "",
        "#include ""pb.h""",
        "#include ""pb_encode.h""",
        "#include ""pb_decode.h""",
        "#include ""pb_common.h""",
        "",
        "#include ""../communication_protocol.h""",
        "#include ""../alp_stream_parser.h""",
        "#include ""../alpcom/alp_message_ids.h"""
    )

    if (Test-Path $generatedC) {
        $generatedHeaders = Get-ChildItem -Path $generatedC -Filter *.pb.h | Sort-Object Name
        foreach ($header in $generatedHeaders) {
            $headerLines += "#include ""$($header.Name)"""
        }
    }

    $headerLines += ""
    $headerLines += "#endif"

    Set-Content -Path $headerPath -Value ($headerLines -join "`r`n")
    Write-Host "Arduino exports updated: src/alpcom.h and src/*.pb.* wrappers"
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
    $protoFiles = Get-ChildItem -Path "proto" -Filter *.proto | Sort-Object Name
    if ($protoFiles.Count -eq 0) {
        throw "No .proto files found under proto/"
    }

    foreach ($protoFile in $protoFiles) {
        & $nanopbGenerator --output-dir=generated/c -I proto ("proto/" + $protoFile.Name)
    }

    Update-AlpcomExports
    Update-ArduinoExports
    Write-Host ("C protobuf generated: " + (($protoFiles | ForEach-Object { $_.Name }) -join ", "))
}
finally {
    Pop-Location
}
