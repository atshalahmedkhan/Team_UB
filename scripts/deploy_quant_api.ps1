# Deploy quant-api FastAPI service to Cloud Run.
# Usage: .\scripts\deploy_quant_api.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$gcloud = "$env:LOCALAPPDATA\Google\CloudSDK\google-cloud-sdk\bin\gcloud.cmd"
if (-not (Test-Path $gcloud)) { $gcloud = "gcloud" }

$Project = if ($env:GCP_PROJECT_ID) { $env:GCP_PROJECT_ID } else {
    & $gcloud config get-value project 2>$null
}
$Region = if ($env:GCP_LOCATION) { $env:GCP_LOCATION } else { "us-central1" }
$Service = "quant-api"

if (-not $Project -or $Project -eq "(unset)") {
    Write-Error "Set GCP_PROJECT_ID or run: gcloud config set project quant-hackathon"
}

function Read-EnvValue($key) {
    $val = $null
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^\s*$key=(.+)\s*$") { $val = $matches[1].Trim() }
        }
    }
    return $val
}

$mongoUri = Read-EnvValue "MONGO_URI"
$elasticUrl = Read-EnvValue "ELASTIC_URL"
$elasticKey = Read-EnvValue "ELASTIC_API_KEY"
$elasticIndex = Read-EnvValue "ELASTIC_INDEX"
if (-not $elasticIndex) { $elasticIndex = "market-states" }
$fredKey = Read-EnvValue "FRED_API_KEY"
$mongoMcp = Read-EnvValue "MONGODB_MCP_URL"
$elasticMcp = Read-EnvValue "ELASTIC_MCP_URL"
$secAgent = Read-EnvValue "SEC_USER_AGENT"
if (-not $secAgent) { $secAgent = "QuantHackathon contact@example.com" }

if (-not $mongoUri) { Write-Error "MONGO_URI required in .env" }
if (-not $elasticUrl -or -not $elasticKey) { Write-Error "ELASTIC_URL and ELASTIC_API_KEY required in .env" }

$envFile = Join-Path $env:TEMP "quant-api-env.yaml"
@"
GOOGLE_GENAI_USE_VERTEXAI: "true"
GCP_PROJECT_ID: "$Project"
GCP_LOCATION: "$Region"
GEMINI_MODEL: "gemini-2.5-flash-lite"
USE_MCP_TOOLS: "true"
MONGO_URI: "$mongoUri"
MONGO_DB_NAME: "quant"
ELASTIC_URL: "$elasticUrl"
ELASTIC_API_KEY: "$elasticKey"
ELASTIC_INDEX: "$elasticIndex"
FRED_API_KEY: "$fredKey"
MONGODB_MCP_URL: "$mongoMcp"
ELASTIC_MCP_URL: "$elasticMcp"
SEC_USER_AGENT: "$secAgent"
FRONTEND_ORIGIN: "*"
"@ | Set-Content -Path $envFile -Encoding utf8

Write-Host "Deploying $Service to Cloud Run ($Region)..."
& $gcloud run deploy $Service --quiet `
    --source $Root `
    --region $Region `
    --project $Project `
    --port 8080 `
    --allow-unauthenticated `
    --memory 1Gi `
    --timeout 300 `
    --env-vars-file $envFile

$url = & $gcloud run services describe $Service --region $Region --project $Project --format "value(status.url)"
Write-Host ""
Write-Host "quant-api deployed."
Write-Host "Endpoint: $url"
Write-Host "Health:   $url/health"
Write-Host "Analyze:  POST $url/analyze/{ticker}"
