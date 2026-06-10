#!/usr/bin/env bash
# Deploy MongoDB MCP Server to Cloud Run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source <(grep -E '^MONGO_URI=' .env | sed 's/^/export /')
: "${MONGO_URI:?Set MONGO_URI in .env}"
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_LOCATION:-us-central1}"
SERVICE="${MONGODB_MCP_SERVICE:-quant-mongodb-mcp}"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project "$PROJECT_ID"
gcloud run deploy "$SERVICE" \
  --source "$ROOT/mcp/mongodb" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "MDB_MCP_TRANSPORT=http,MDB_MCP_HTTP_HOST=0.0.0.0,MDB_MCP_HTTP_PORT=8080,MDB_MCP_READ_ONLY=true,MDB_MCP_CONNECTION_STRING=${MONGO_URI}"
URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')"
echo "MONGODB_MCP_URL=${URL}/mcp"
