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
az bicep build --file "$TASK_ROOT/infra/main.bicep" --stdout >/dev/null
mkdir -p "$TASK_ROOT/.azure"
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" --tags application=agora-match --output none
for provider in Microsoft.App Microsoft.ContainerRegistry Microsoft.CognitiveServices Microsoft.OperationalInsights Microsoft.Insights Microsoft.ManagedIdentity; do
  az provider register --namespace "$provider" --wait --output none
done
az deployment group create --name agora-foundation --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$TASK_ROOT/infra/main.bicep" --parameters "@$AGORA_PARAMETERS_FILE" deployApp=false location="$AZURE_LOCATION" \
  --query properties.outputs --output json > "$TASK_ROOT/.azure/foundation.json"
AGORA_REGISTRY=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["registryName"]["value"])' "$TASK_ROOT/.azure/foundation.json")
AGORA_LOGIN_SERVER=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["registryLoginServer"]["value"])' "$TASK_ROOT/.azure/foundation.json")
AGORA_TAG=$(git -C "$TASK_ROOT" rev-parse --short=12 HEAD)
# ACR builds the Dockerfile remotely; Docker is not required on the caller's machine.
az acr build --registry "$AGORA_REGISTRY" --image "agora-match:$AGORA_TAG" --file "$TASK_ROOT/Dockerfile" "$TASK_ROOT" --no-logs --output none
AGORA_DIGEST=$(az acr repository show --name "$AGORA_REGISTRY" --image "agora-match:$AGORA_TAG" --query digest --output tsv)
[[ "$AGORA_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo 'ACR did not return an immutable image digest.' >&2; exit 1; }
az deployment group create --name agora-application --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$TASK_ROOT/infra/main.bicep" --parameters "@$AGORA_PARAMETERS_FILE" deployApp=true location="$AZURE_LOCATION" \
  containerImage="$AGORA_LOGIN_SERVER/agora-match@$AGORA_DIGEST" \
  --query properties.outputs --output json > "$TASK_ROOT/.azure/application.json"
AGORA_URL=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["appUrl"]["value"])' "$TASK_ROOT/.azure/application.json")
python "$TASK_ROOT/scripts/smoke_azure.py" --url "$AGORA_URL" --require-ai
printf 'Verified Agora Match deployment: %s\n' "$AGORA_URL"
