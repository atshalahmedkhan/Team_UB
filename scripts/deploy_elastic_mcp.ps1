# Deploy Elastic MCP bridge to Cloud Run.
# Usage: .\scripts\deploy_elastic_mcp.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$gcloud = "$env:LOCALAPPDATA\Google\CloudSDK\google-cloud-sdk\bin\gcloud.cmd"
if (-not (Test-Path $gcloud)) { $gcloud = "gcloud" }

$Project = if ($env:GCP_PROJECT_ID) { $env:GCP_PROJECT_ID } else {
    & $gcloud config get-value project 2>$null
}
$Region = if ($env:GCP_LOCATION) { $env:GCP_LOCATION } else { "us-central1" }
$Service = if ($env:ELASTIC_MCP_SERVICE) { $env:ELASTIC_MCP_SERVICE } else { "quant-elastic-mcp" }

if (-not $Project -or $Project -eq "(unset)") {
    Write-Error "Set GCP_PROJECT_ID or run: gcloud config set project quant-hackathon"
}

$elasticUrl = $null
$elasticKey = $null
$elasticIndex = "market-states"
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*ELASTIC_URL=(.+)\s*$') { $elasticUrl = $matches[1].Trim() }
        if ($_ -match '^\s*ELASTIC_API_KEY=(.+)\s*$') { $elasticKey = $matches[1].Trim() }
        if ($_ -match '^\s*ELASTIC_INDEX=(.+)\s*$') { $elasticIndex = $matches[1].Trim() }
    }
}
if (-not $elasticUrl -or -not $elasticKey) {
    Write-Error "ELASTIC_URL and ELASTIC_API_KEY required in .env"
}

$envFile = Join-Path $env:TEMP "quant-elastic-mcp-env.yaml"
@"
ELASTIC_URL: "$elasticUrl"
ELASTIC_API_KEY: "$elasticKey"
ELASTIC_INDEX: "$elasticIndex"
"@ | Set-Content -Path $envFile -Encoding utf8

Write-Host "Deploying $Service to Cloud Run ($Region)..."
& $gcloud run deploy $Service --quiet `
    --source "$Root\mcp\elastic" `
    --region $Region `
    --project $Project `
    --port 8080 `
    --allow-unauthenticated `
    --memory 512Mi `
    --env-vars-file $envFile

$url = & $gcloud run services describe $Service --region $Region --project $Project --format "value(status.url)"
Write-Host ""
Write-Host "Elastic MCP bridge deployed."
Write-Host "Tools catalog: $url/tools"
Write-Host "kNN tool:      POST $url/tools/market_state_knn"
Write-Host ""
Write-Host "Add to .env:"
Write-Host "ELASTIC_MCP_URL=$url"
