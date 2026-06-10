#!/usr/bin/env bash
# Deploy Elastic MCP bridge to Cloud Run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
set -a && source .env && set +a
: "${ELASTIC_URL:?}" ; : "${ELASTIC_API_KEY:?}"
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_LOCATION:-us-central1}"
SERVICE="${ELASTIC_MCP_SERVICE:-quant-elastic-mcp}"
INDEX="${ELASTIC_INDEX:-market-states}"
gcloud run deploy "$SERVICE" \
  --source "$ROOT/mcp/elastic" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "ELASTIC_URL=${ELASTIC_URL},ELASTIC_API_KEY=${ELASTIC_API_KEY},ELASTIC_INDEX=${INDEX}"
URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')"
echo "ELASTIC_MCP_URL=${URL}"
