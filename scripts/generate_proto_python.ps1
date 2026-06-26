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
Push-Location $repoRoot

try {
    New-Item -ItemType Directory -Force -Path "generated/python" | Out-Null
    $protoFiles = Get-ChildItem -Path "proto" -Filter *.proto | Sort-Object Name
    if ($protoFiles.Count -eq 0) {
        throw "No .proto files found under proto/"
    }

    $protoArgs = $protoFiles | ForEach-Object { "proto/$($_.Name)" }
    python -m grpc_tools.protoc -I proto --python_out=generated/python $protoArgs
    python scripts/generate_message_registry.py
    Update-AlpcomExports
    Write-Host ("Python protobuf generated: " + (($protoFiles | ForEach-Object { $_.Name }) -join ", "))
}
finally {
    Pop-Location
}
