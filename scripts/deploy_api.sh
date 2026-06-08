#!/usr/bin/env bash
# Deploy Quant FastAPI to Google Cloud Run.
#
# Prerequisites:
#   gcloud auth login
#   gcloud config set project YOUR_PROJECT_ID
#   Secret Manager secret "mongo-uri" with MONGO_URI value
#   Service account with Vertex AI User + Secret Accessor roles
#
# Usage:
#   FRONTEND_ORIGIN=https://your-app.vercel.app ./scripts/deploy_api.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_LOCATION:-us-central1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-quant-api}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://localhost:3000}"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "ERROR: Set GCP_PROJECT_ID or run gcloud config set project"
  exit 1
fi

echo "Deploying $SERVICE_NAME to project $PROJECT_ID ($REGION)..."

gcloud run deploy "$SERVICE_NAME" \
  --source "$ROOT" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --timeout 300 \
  --memory 1Gi \
  --cpu 1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GCP_PROJECT_ID=${PROJECT_ID},GCP_LOCATION=${REGION},GEMINI_MODEL=gemini-2.5-flash-lite,FRONTEND_ORIGIN=${FRONTEND_ORIGIN}" \
  --set-secrets "MONGO_URI=mongo-uri:latest"

echo ""
echo "Done. Set NEXT_PUBLIC_API_URL on Vercel to the service URL above."
