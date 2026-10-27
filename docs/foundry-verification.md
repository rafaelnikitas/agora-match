# Verify real Microsoft Foundry execution

There are three separate checks. Passing one does not establish the others.

| Check | What it establishes | Current status |
|---|---|---|
| Regression and container CI | The app builds, starts, and preserves the synthetic evidence contract | Local checks pass after the rename; GitHub Actions records container and infrastructure results |
| Live Foundry integration | Real model calls complete, facts survive, and the configured roles hand off successfully | Not run: Azure identity and endpoint are not configured in this workspace |
| Answer quality | Explanations are useful, supported, and appropriate for each role | Requires live output review; no accuracy percentage claimed |

## Fastest path: use an existing deployment

An authorized Azure user needs an existing compatible Foundry/Azure OpenAI model deployment, its resource endpoint, and permission to invoke it. For this adapter, use the Azure OpenAI v1 endpoint ending in `/openai/v1`. A project URL alone is not the model endpoint.

Sign in with the official Azure CLI in your own development environment, install the application requirements, and export:

```bash
az login
export AZURE_FOUNDRY_BASE_URL="https://<resource>.openai.azure.com/openai/v1"
export AZURE_FOUNDRY_AUTH_MODE="default_credential"
export AZURE_FOUNDRY_READER_DEPLOYMENT="<deployment-name>"
export AZURE_FOUNDRY_WRITER_DEPLOYMENT="<deployment-name>"
export AZURE_FOUNDRY_REVIEWER_DEPLOYMENT="<deployment-name>"
# For a reasoning-model deployment, also set its supported profile:
# export AZURE_FOUNDRY_REASONING_DEPLOYMENTS="<deployment-name>"
# export AZURE_FOUNDRY_REASONING_EFFORT="low"
python scripts/evaluate_models.py --run-live --mode compare \
  --pause-seconds 8 --output build/live-model-evaluation.json
```

The roles can share one model deployment. Comparison runs six cases against the single-role and three-role paths. It records actual output, evidence, stage/deployment traces, token usage, latency, contract checks, reviewer approval, and empty fields for human review. A fallback or missing configuration produces a nonzero exit status. Twelve answers normally involve up to 24 model requests before retries, so confirm available quota and usage costs first.

Do not paste credentials into issues, chat, source, or the browser app. Identity-based access avoids distributing an API key.

## Run from this GitHub repository

The manual workflow is **Verify live Foundry (model calls)**. It invokes an existing resource and does not deploy Azure infrastructure.

1. Configure a GitHub environment named `azure-verification`.
2. Configure an Entra federated identity for `repo:rafaelnikitas/agora-match:environment:azure-verification`. Give that identity the resource-scoped role needed to invoke your deployed Azure OpenAI model; the application runbook uses Cognitive Services OpenAI User. It needs no deployment or resource-creation role for this workflow.
3. Set environment variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_FOUNDRY_BASE_URL`, and `AZURE_FOUNDRY_DEPLOYMENT`. Role-specific deployment variables can override the shared deployment. Set the reasoning profile variables when required by the chosen model.
4. Open Actions, choose the verification workflow, and run it. Download the `agora-foundry-evaluation` artifact. Failed execution must remain failed; inspect its fallback reasons.

This workflow is separate from the manual Azure deployment workflow. Merely adding its YAML does not prove a live run. The evidence artifact is retained for 30 days; preserve a reviewed release copy if needed for judging.

## Show the same capability in the actual app

After configuring identity in a development environment:

```bash
python -m agora_match.build_static
python -m agora_match.server
python scripts/smoke_azure.py --url http://127.0.0.1:8080 --require-ai
```

The smoke check must show `model_used: true` and all three stages. Then ask questions in the UI for Fan, Analyst, and Coach and inspect their source facts and real stage traces. For a public AI demo, deploy the same UI/API container using [the Azure runbook](azure-readiness.md), then run the smoke check against its HTTPS URL.

The existing static public site cannot run the Python backend or acquire an Azure managed identity. Adding a key to its frontend would expose it and is not the deployment path. It stays available as a synthetic-data UI demo until an AI-backed application host is configured.

## Optional Foundry portal evaluation

Our script exercises the application against Foundry model endpoints. It is not a Foundry portal evaluation job or a hosted Foundry Agent Service workflow. For additional quality assessment, export the real outputs with query, response, retrieved context, and expected facts to JSONL, then run an existing-dataset evaluation in your Foundry project. Groundedness and relevance scores should accompany human review, with the model, dataset, and evaluation version recorded.

Official guidance: [Foundry evaluations](https://learn.microsoft.com/en-us/azure/foundry/how-to/evaluate-generative-ai-app) and [observability](https://learn.microsoft.com/en-us/azure/foundry/concepts/observability).
