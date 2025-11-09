#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/deploy_cloud_run.sh <PROJECT_ID> [TAG]
# Example:
#   ./scripts/deploy_cloud_run.sh my-gcp-project v0.2

PROJECT_ID=${1:-}
TAG=${2:-v0.2}
SERVICE_NAME=cocock-app
REGION=asia-northeast1
IMAGE=gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${TAG}

if [ -z "$PROJECT_ID" ]; then
  echo "Usage: $0 <PROJECT_ID> [TAG]" >&2
  exit 2
fi

echo "Checking gcloud..."
if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI not found in PATH. Please install and authenticate first." >&2
  exit 1
fi

echo "Starting Cloud Run deploy sequence for project: ${PROJECT_ID}, tag: ${TAG}"

echo "1) Ensure you're logged in (interactive if needed)"
gcloud auth login || true

echo "2) Set project"
gcloud config set project "${PROJECT_ID}"

echo "3) Build container with Cloud Build and push to GCR"
gcloud builds submit --tag "${IMAGE}"

echo "4) Deploy to Cloud Run (region: ${REGION})"
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated

echo "5) Fetch service URL"
URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format='value(status.url)')

if [ -n "$URL" ]; then
  echo "Deployment finished. Service URL: ${URL}"
  echo "# Cloud Run URL: ${URL}" >> conversation_log.md || true
  echo "(記録) conversation_log.md に URL を追記しました。"
else
  echo "Deployment finished but could not read service URL." >&2
fi

echo "Note: Cloud Run filesystem is ephemeral — use Cloud SQL/Firestore/Cloud Storage for persistence in production." 
