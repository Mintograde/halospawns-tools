param(
    [Parameter(Mandatory = $true)]
    [string]$MapPath,
    [string]$Image = "halospawns-tools:latest",
    [string]$CeRoot = "L:\ce_container_test",
    [string]$RiePath = "$HOME\.aws-lambda-rie",
    [string]$EventFile = "tests\events\testevent_local.json",
    [int]$Port = 9000,
    [int]$ExpectedMinImages = 300,
    [double]$MaxDurationMs = 30000.0
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$mapPathResolved = (Resolve-Path $MapPath).Path
$mapDir = Split-Path -Path $mapPathResolved -Parent
$mapFile = Split-Path -Path $mapPathResolved -Leaf
$rieBinary = Join-Path $RiePath "aws-lambda-rie"
$containerName = "halospawns-tools-local-" + [Guid]::NewGuid().ToString("N").Substring(0, 8)
$responseFile = Join-Path $repoRoot "test_container_local_response.json"
$logFile = Join-Path $repoRoot "test_container_local_console_output.log"

if (-not (Test-Path $rieBinary)) {
    throw "RIE binary not found: $rieBinary"
}

if (-not (Test-Path $CeRoot)) {
    New-Item -ItemType Directory -Path $CeRoot | Out-Null
}

$eventPath = if ([System.IO.Path]::IsPathRooted($EventFile)) {
    (Resolve-Path $EventFile).Path
} else {
    (Resolve-Path (Join-Path $repoRoot $EventFile)).Path
}

$eventObj = Get-Content -Raw $eventPath | ConvertFrom-Json
$eventObj.io_mode = "local"
$eventObj.local_input_map = "/local_input/$mapFile"
$payload = $eventObj | ConvertTo-Json -Depth 20 -Compress

try {
    & docker run --platform linux/amd64 --name $containerName -d -p "${Port}:8080" `
        -v "${RiePath}:/aws-lambda" `
        -v "${mapDir}:/local_input:ro" `
        -v "${CeRoot}:/tmp/ce" `
        -e IO_MODE=local `
        --entrypoint /aws-lambda/aws-lambda-rie `
        $Image `
        /usr/local/bin/python -m awslambdaric app.handler | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start container."
    }

    Start-Sleep -Seconds 2
    & curl.exe -sS -XPOST "http://localhost:${Port}/2015-03-31/functions/function/invocations" -d $payload | Set-Content -Path $responseFile -Encoding UTF8
    Start-Sleep -Seconds 2
    & docker logs $containerName *> $logFile

    $response = Get-Content -Raw $responseFile | ConvertFrom-Json
    $bodyRecords = $response.body | ConvertFrom-Json
    if (-not $bodyRecords -or $bodyRecords.Count -eq 0) {
        throw "Handler response body did not contain conversion records."
    }

    $first = $bodyRecords[0]
    if ($first.status -ne "success") {
        throw "Conversion status was '$($first.status)'."
    }

    $mapName = $first.output.map_name
    if (-not $mapName) {
        throw "map_name missing from handler response output."
    }

    $outputMapDir = Join-Path (Join-Path $CeRoot "output") $mapName
    $validator = Join-Path $repoRoot "tests\validation\validate_conversion_run.py"
    $baseline = Join-Path $repoRoot "tests\baselines\output_folder_contents.txt"
    $pythonExe = Join-Path $repoRoot "venv314\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        $pythonExe = "python"
    }

    $validateArgs = @(
        $validator,
        "--output-map-dir", $outputMapDir,
        "--map-name", $mapName,
        "--log-file", $logFile,
        "--expected-min-images", $ExpectedMinImages,
        "--max-duration-ms", $MaxDurationMs
    )
    if (Test-Path $baseline) {
        $validateArgs += @("--baseline-output-listing", $baseline)
    }

    & $pythonExe @validateArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Validation failed."
    }

    Write-Host "Container local E2E passed"
    Write-Host "map_name: $mapName"
    Write-Host "output_map_dir: $outputMapDir"
    Write-Host "log_file: $logFile"
}
finally {
    & docker rm -f $containerName *> $null
}
