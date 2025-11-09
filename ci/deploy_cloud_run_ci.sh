#!/usr/bin/env bash
set -euo pipefail

# CI-friendly deploy script for Cloud Run using a service account key.
# Supports two authentication methods (CI systems):
# 1) Provide SERVICE_ACCOUNT_KEY_BASE64 env var (base64-encoded JSON key) -> script decodes to a temp file
# 2) Provide GOOGLE_APPLICATION_CREDENTIALS pointing to a key file already present on the runner
#
# Usage (recommended, using base64 secret):
#   export PROJECT_ID=my-gcp-project
#   export SERVICE_ACCOUNT_KEY_BASE64="<base64 of service-account.json>"
#   export TAG=v0.2
#   ./ci/deploy_cloud_run_ci.sh
#
# Required env vars:
# - PROJECT_ID
# - Either SERVICE_ACCOUNT_KEY_BASE64 or GOOGLE_APPLICATION_CREDENTIALS (path)
# Optional:
# - TAG (default: v0.2)
# - REGION (default: asia-northeast1)
# - SERVICE_NAME (default: cocock-app)

PROJECT_ID=${PROJECT_ID:-}
TAG=${TAG:-v0.2}
REGION=${REGION:-asia-northeast1}
SERVICE_NAME=${SERVICE_NAME:-cocock-app}

if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: PROJECT_ID must be set" >&2
  exit 2
fi

if [ -z "${SERVICE_ACCOUNT_KEY_BASE64:-}" ] && [ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
  echo "ERROR: either SERVICE_ACCOUNT_KEY_BASE64 or GOOGLE_APPLICATION_CREDENTIALS must be provided" >&2
  exit 2
fi

echo "CI deploy: project=${PROJECT_ID}, service=${SERVICE_NAME}, tag=${TAG}, region=${REGION}"

# Authenticate
if [ -n "${SERVICE_ACCOUNT_KEY_BASE64:-}" ]; then
  echo "Using SERVICE_ACCOUNT_KEY_BASE64 to authenticate"
  TMP_KEY_FILE=$(mktemp)
  echo "$SERVICE_ACCOUNT_KEY_BASE64" | base64 -d > "$TMP_KEY_FILE"
  chmod 600 "$TMP_KEY_FILE"
  gcloud auth activate-service-account --key-file="$TMP_KEY_FILE"
  # ensure cleanup
  cleanup() {
    rm -f "$TMP_KEY_FILE"
  }
  trap cleanup EXIT
else
  echo "Using GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"
  gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
fi

gcloud config set project "$PROJECT_ID"

IMAGE=gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${TAG}

echo "Building and pushing image: ${IMAGE}"
gcloud builds submit --tag "$IMAGE"

echo "Deploying to Cloud Run"
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated

URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format='value(status.url)')

echo "Deployed: ${URL}"

# In CI we print URL; optionally CI can upload to artifact store
echo "CLOUD_RUN_URL=${URL}"
