# Deploy MongoDB MCP Server to Cloud Run (HTTP /mcp endpoint).
# Usage: .\scripts\deploy_mongodb_mcp.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$gcloud = "$env:LOCALAPPDATA\Google\CloudSDK\google-cloud-sdk\bin\gcloud.cmd"
if (-not (Test-Path $gcloud)) { $gcloud = "gcloud" }

$Project = if ($env:GCP_PROJECT_ID) { $env:GCP_PROJECT_ID } else {
    & $gcloud config get-value project 2>$null
}
$Region = if ($env:GCP_LOCATION) { $env:GCP_LOCATION } else { "us-central1" }
$Service = if ($env:MONGODB_MCP_SERVICE) { $env:MONGODB_MCP_SERVICE } else { "quant-mongodb-mcp" }

if (-not $Project -or $Project -eq "(unset)") {
    Write-Error "Set GCP_PROJECT_ID or run: gcloud config set project quant-hackathon"
}

# Load MONGO_URI from .env without printing it
$mongoUri = $null
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*MONGO_URI=(.+)\s*$') { $mongoUri = $matches[1].Trim() }
    }
}
if (-not $mongoUri) {
    Write-Error "MONGO_URI not found in .env"
}

Write-Host "Enabling Cloud Run + Cloud Build APIs on project $Project..."
& $gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project $Project

$envFile = Join-Path $env:TEMP "quant-mongodb-mcp-env.yaml"
@"
MDB_MCP_TRANSPORT: http
MDB_MCP_HTTP_HOST: 0.0.0.0
MDB_MCP_HTTP_PORT: "8080"
MDB_MCP_READ_ONLY: "true"
MDB_MCP_CONNECTION_STRING: "$mongoUri"
"@ | Set-Content -Path $envFile -Encoding utf8

Write-Host "Deploying $Service to Cloud Run ($Region)..."
& $gcloud run deploy $Service --quiet `
    --source "$Root\mcp\mongodb" `
    --region $Region `
    --project $Project `
    --port 8080 `
    --allow-unauthenticated `
    --memory 512Mi `
    --env-vars-file $envFile

$url = & $gcloud run services describe $Service --region $Region --project $Project --format "value(status.url)"
Write-Host ""
Write-Host "MongoDB MCP deployed."
Write-Host "MCP endpoint: $url/mcp"
Write-Host ""
Write-Host "Add to .env:"
Write-Host "MONGODB_MCP_URL=$url/mcp"
