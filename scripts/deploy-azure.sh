#!/usr/bin/env bash
# Run only after choosing the subscription, model configuration, and cost envelope.
set -euo pipefail
set +x
TASK_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
: "${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID to the intended subscription.}"
: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP to the intended resource group.}"
AZURE_LOCATION=${AZURE_LOCATION:-swedencentral}
AGORA_PARAMETERS_FILE=${AGORA_PARAMETERS_FILE:-$TASK_ROOT/infra/parameters.example.json}
command -v az >/dev/null || { echo 'Install the official Azure CLI first.' >&2; exit 1; }
command -v python >/dev/null || { echo 'Python 3 is required.' >&2; exit 1; }
[[ -z "$(git -C "$TASK_ROOT" status --porcelain)" ]] || { echo 'Commit source changes before deploying a reproducible image.' >&2; exit 1; }
az account show --output none || { echo 'Sign in with az login, then rerun.' >&2; exit 1; }
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
python "$TASK_ROOT/scripts/preflight.py" --parameters "$AGORA_PARAMETERS_FILE"
if [[ -n "${AGORA_IMAGE_ARCHIVE:-}" ]]; then
  command -v crane >/dev/null || { echo 'Install crane from google/go-containerregistry to push the tested image archive.' >&2; exit 1; }
  python "$TASK_ROOT/scripts/verify_image_archive.py" --archive "$AGORA_IMAGE_ARCHIVE" --source-sha "$(git -C "$TASK_ROOT" rev-parse HEAD)"
else
  AGORA_OFFER=$(az rest --method get --url "https://management.azure.com/subscriptions/$AZURE_SUBSCRIPTION_ID?api-version=2022-12-01" --query subscriptionPolicies.quotaId --output tsv)
  [[ "$AGORA_OFFER" != FreeTrial* ]] || { echo 'Trial credits cannot run ACR Tasks. Set AGORA_IMAGE_ARCHIVE to the tested CI image tar; see docs/azure-readiness.md.' >&2; exit 1; }
fi
az bicep build --file "$TASK_ROOT/infra/main.bicep" --stdout >/dev/null
mkdir -p "$TASK_ROOT/.azure"
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" --tags application=agora-match --output none
for provider in Microsoft.App Microsoft.ContainerRegistry Microsoft.CognitiveServices Microsoft.OperationalInsights Microsoft.Insights Microsoft.ManagedIdentity; do
  # ARM can use a provider once its target region is ready; waiting for global
  # registration can stall a new trial subscription for many minutes.
  az provider register --namespace "$provider" --output none
done
az deployment group create --name agora-foundation --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$TASK_ROOT/infra/main.bicep" --parameters "@$AGORA_PARAMETERS_FILE" deployApp=false location="$AZURE_LOCATION" \
  --query properties.outputs --output json > "$TASK_ROOT/.azure/foundation.json"
AGORA_REGISTRY=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["registryName"]["value"])' "$TASK_ROOT/.azure/foundation.json")
AGORA_LOGIN_SERVER=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["registryLoginServer"]["value"])' "$TASK_ROOT/.azure/foundation.json")
AGORA_TAG=$(git -C "$TASK_ROOT" rev-parse --short=12 HEAD)
if [[ -n "${AGORA_IMAGE_ARCHIVE:-}" ]]; then
  # Trial credits cannot currently run ACR Tasks. CI exports the exact image it
  # tested. Use an isolated, short-lived registry login and never print tokens.
  AGORA_AUTH_DIR=$(mktemp -d "$TASK_ROOT/.azure/registry-auth.XXXXXX")
  export DOCKER_CONFIG="$AGORA_AUTH_DIR"
  trap 'rm -rf -- "$AGORA_AUTH_DIR"' EXIT
  az acr login --name "$AGORA_REGISTRY" --expose-token --query accessToken --output tsv |
    crane auth login "$AGORA_LOGIN_SERVER" --username 00000000-0000-0000-0000-000000000000 --password-stdin
  crane push "$AGORA_IMAGE_ARCHIVE" "$AGORA_LOGIN_SERVER/agora-match:$AGORA_TAG"
  crane auth logout "$AGORA_LOGIN_SERVER"
else
  # ACR builds remotely on eligible subscriptions; Docker is not needed here.
  az acr build --registry "$AGORA_REGISTRY" --image "agora-match:$AGORA_TAG" --file "$TASK_ROOT/Dockerfile" "$TASK_ROOT" --no-logs --output none
fi
AGORA_DIGEST=$(az acr repository show --name "$AGORA_REGISTRY" --image "agora-match:$AGORA_TAG" --query digest --output tsv)
[[ "$AGORA_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo 'ACR did not return an immutable image digest.' >&2; exit 1; }
az deployment group create --name agora-application --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$TASK_ROOT/infra/main.bicep" --parameters "@$AGORA_PARAMETERS_FILE" deployApp=true location="$AZURE_LOCATION" \
  containerImage="$AGORA_LOGIN_SERVER/agora-match@$AGORA_DIGEST" \
  --query properties.outputs --output json > "$TASK_ROOT/.azure/application.json"
AGORA_URL=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["appUrl"]["value"])' "$TASK_ROOT/.azure/application.json")
python "$TASK_ROOT/scripts/smoke_azure.py" --url "$AGORA_URL" --require-ai
printf 'Verified Agora Match deployment: %s\n' "$AGORA_URL"
