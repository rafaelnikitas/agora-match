# Azure readiness

Agora Match keeps its Fan, Analyst, and Coach workspaces. Azure runs the same UI and API together, with server-side model access. The existing public static demo remains a deterministic, synthetic-data experience until an Azure deployment is provisioned and verified.

## What Azure adds

| Capability | Implementation | Practical benefit |
|---|---|---|
| Audience-aware AI | Foundry Models with analyst, narrator, and evidence-reviewer roles | More natural explanations over the same verified facts |
| Keyless access | User-assigned managed identity and resource-scoped RBAC | No model key in the browser or application configuration |
| Managed hosting | Container Apps Consumption, health probes, bounded replicas | HTTPS, process recovery, and demand-based scaling |
| Diagnosis | Application Insights traces, stage latency, token usage, fallback reasons | Locate failures and slow model stages |
| Reproducibility | Hash-locked Python packages, Bicep, immutable image digest, CI | Rebuild and review the deployment from source |
| Honest degradation | Numeric checks, reviewer gate, bounded retries, circuit recovery, cached approved answers | Useful deterministic evidence remains available during AI failures |

Azure does not improve the underlying synthetic measurements. It enables the model, hosting, and operational capabilities around them. The workload remains a POC; this package is deployment preparation, not proof of production operation.

## Architecture boundaries

The browser uses one origin for the existing interface and FastAPI API. The API computes and retrieves evidence before calling Foundry. A reader ranks supplied fact IDs, a writer explains the selected evidence for the audience, and a reviewer can reject it. Schema-constrained outputs limit each role's fields and eligible fact IDs. One bounded narration correction is allowed after a contract or review rejection; the corrected draft must pass the same checks and reviewer. A failed correction falls back safely. Application validation remains mandatory: unknown IDs, duplicates, unselected facts, new numerical claims, and rejected reviews fall back safely. The writer receives the reader's validated subset; the reviewer can check the complete evidence bundle. All three roles may share one deployment; three roles do not imply three different models.

The application orchestrates the roles in Python. It does **not** deploy Foundry Agent Service or claim a Microsoft Agent Framework workflow. Calculations, ranking, player ratings, and geometry remain deterministic. Model review and numeric checks reduce errors but are not a proof that every qualitative statement is correct.

The Bicep template provisions:

- Container Apps Consumption environment and one UI/API container, with HTTPS ingress.
- Azure Container Registry Basic, admin login and anonymous pull disabled.
- An Azure OpenAI resource, or an AIServices Foundry account and project, with pinned model versions and local key authentication disabled.
- A user-assigned managed identity with resource-scoped model invocation, AcrPull, and Monitoring Metrics Publisher permissions. The OpenAI route uses Cognitive Services OpenAI User; the Foundry project route uses Cognitive Services User on the dedicated AI account.
- A Log Analytics workspace and workspace-based Application Insights with Entra-authenticated application telemetry.

The default is `gpt-5.4-mini`, version `2026-03-17`, GlobalStandard capacity `5`, in `swedencentral`. Region support, quota, model access, and version availability must be checked in the actual subscription. The model profile omits temperature and uses `max_completion_tokens` with low reasoning effort. Change the parameter file if your available deployment differs. The template does not silently select another model.

### Free-trial profile

`infra/parameters.trial.json` selects a Foundry AIServices account and `agora-match` project, with `gpt-oss-120b`, format `OpenAI-OSS`, version `1`, GlobalStandard capacity `50`. All three application roles share this deployment. The app uses the project's OpenAI-compatible v1 endpoint and Entra token audience `https://ai.azure.com/.default`. It allows one container replica, scales to zero, and uses a 15-second HTTP timeout and 45-second answer budget.

This profile was prepared after checking a free-trial subscription's actual Sweden Central quota and model catalog on 27 October 2026: GPT-OSS quota was positive while the checked GPT model quotas were zero. This is **not** a guarantee for other subscriptions or proof of a successful live model request. Recheck your own quota, regional policy, and model access. A trial profile still consumes credit for eligible services; it does not make ACR, inference, builds, or logs universally free. Keep the trial spending limit enabled; these scripts never upgrade the account or remove it.

The project/resource pattern follows Microsoft's [Foundry starter](https://github.com/Azure-Samples/ai-model-start) and [GPT-OSS deployment guidance](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/gpt-oss).

## 1. Run locally

Use Python 3.12 and Node.js for JavaScript syntax checks:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt
python -m unittest discover -s tests -q
node --check static/app.js
node --check static/experience.js
python -m agora_match.server
```

Open `http://localhost:8080`. No Azure account is required for deterministic mode. The server does not automatically load `.env`; export the variables you need. See `.env.example` for the supported settings. Local model access can use `AZURE_FOUNDRY_AUTH_MODE=default_credential` after `az login` and an explicit OpenAI User grant on the model resource. The Azure deployment uses managed identity instead.

In a second terminal:

```bash
python scripts/smoke_azure.py --url http://127.0.0.1:8080
python scripts/evaluate.py --url http://127.0.0.1:8080
```

The evaluation makes 21 requests: seven evidence scenarios across three audiences. Its routing checks compare known facts, not writing quality. A local demo correctly reports a zero real-model rate.

## 2. Prepare an Azure subscription

Deployment requires an authenticated Azure CLI, an intended subscription and resource group, and permission to create resources and assign the listed roles. In a tightly controlled subscription, an administrator can pre-create a dedicated resource group and grant the deployment principal the required resource-management and role-assignment permissions there. Provider registration may require a subscription administrator. Do not give the application identity deployment privileges.

Before running the deployment:

1. Confirm model/version availability and deployment quota in the chosen region.
2. Review `infra/parameters.example.json`; copy it to an ignored `.azure/parameters.json` for local overrides if desired.
3. Agree a spending envelope and set Azure Cost Management budget alerts for the dedicated resource group. Budget alerts are not a hard spending cutoff.
4. Commit the reviewed source. The deployment script rejects a dirty checkout so the image tag identifies a reproducible commit.

Costs include model tokens, ACR Basic, container compute, image builds, and monitoring ingestion. Scale-to-zero affects container compute; it does not remove all other charges. Defaults cap the app at two replicas and the workspace at a 1 GB daily ingestion quota. Per-replica call limits and ingestion quotas are operational controls, not a guarantee of a fixed bill. Avoid repeatedly running the evaluation against paid models without checking its reported usage and latency.

## 3. Deploy the same app

```bash
az login
export AZURE_SUBSCRIPTION_ID="<intended-subscription-id>"
export AZURE_RESOURCE_GROUP="agora-match-demo"
export AZURE_LOCATION="swedencentral"
# Optional: export AGORA_PARAMETERS_FILE="$PWD/.azure/parameters.json"
# For the quota-checked GPT-OSS route:
# export AGORA_PARAMETERS_FILE="$PWD/infra/parameters.trial.json"
bash scripts/deploy-azure.sh
```

The script validates model wiring, compiles Bicep, creates the foundation, builds the container remotely in ACR, resolves an immutable image digest, and deploys that exact digest. Docker is not needed on the caller's machine. It then checks readiness and makes a fresh request that must complete all three AI roles. A static page or fallback answer cannot pass the real-AI gate. Deployment outputs are saved under ignored `.azure/`; no model keys are printed.

### Build route for trial credits

Microsoft currently [pauses ACR Tasks runs on free credits](https://microsoftlearning.github.io/mslearn-azure-ai/instructions/container-hosting/01-acr-tasks.html). A trial subscription can use a container built elsewhere and pushed to its private registry. CI exports the Docker image **after** its HTTP smoke test as the `agora-match-container` artifact, retained for three days. No Azure credentials or package-publishing permissions are added to CI.

Download the artifact from a successful main-branch CI run. Check out that run's full source SHA, verify the supplied checksum, and decompress the image with `gzip -dk agora-match-image.tar.gz`. Install Google's official [crane](https://github.com/google/go-containerregistry/tree/main/cmd/crane) CLI, then set `AGORA_IMAGE_ARCHIVE` to the absolute path of the uncompressed `.tar` before running the deploy script. Also select `infra/parameters.trial.json`. The script checks the image's source label and platform, uses the current Azure login to push it, removes its temporary registry credentials, and deploys by digest. It does not enable registry admin passwords or change the trial spending limit.

For a local Docker build, use `docker build --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" -t agora-match:local .` and `docker save -o agora-match-image.tar agora-match:local`, then pass the resulting archive through the same route.

RBAC propagation, image availability, cold starts, quota, and provider policy can cause a first deployment to fail. Read the failure and the Container Apps revision logs before changing settings. If resources are healthy and only a new role grant is still propagating, wait for that grant to take effect and rerun the smoke command below. Re-running the deploy script is intended to update the same resources; it does not delete the resource group.

## 4. Verify the actual Azure deployment

```bash
python scripts/smoke_azure.py --url https://<container-app-host> --require-ai
python scripts/evaluate.py --url https://<container-app-host> \
  --require-ai --pause-seconds 8 --output build/azure-evaluation.json
```

The pause respects the default per-replica model call allowance for three calls per answer under otherwise idle traffic. Retries and other visitors consume the same allowance. Inspect failures rather than treating a fallback as AI success.

Check both matches and each role in the browser. Confirm that chat shows AI versus fallback, retains evidence, and exposes actual stage execution. `GET /api/capabilities` reports the hosting/data modes and connection state. `GET /health/ready` validates startup data and required configuration without calling a paid model. Only a successful model request changes connection status from configured/unverified to verified. A later provider failure changes it to degraded. This state is held per replica and is not a global service-health measure.

Before calling this deployment verified, retain:

- The successful real-AI smoke output and evaluation report.
- A healthy Container Apps revision and its deployed image digest.
- Application Insights traces showing the three stages, latency, and token counts.
- A browser check of Fan, Analyst, and Coach with evidence and failure messaging.

### Monitoring

Application spans are `agora.answer`, `agora.agent.match_analyst`, `agora.agent.audience_narrator`, and `agora.agent.evidence_reviewer`. Azure Monitor also captures request/dependency telemetry. Structured application logs allowlist operational fields and omit questions, prompt bodies, model responses, and credentials. Do not enable SDK HTTP body/header debug logging in production. Trace sampling defaults to two traces per second; offline telemetry storage and live metrics are disabled.

Example query in the Application Insights Logs context:

```kusto
dependencies
| where timestamp > ago(1h)
| where name startswith "agora.agent."
| summarize calls=count(), p95_ms=percentile(duration, 95) by name
```

Also inspect `traces` for `agent_stage` and `answer_fallback` messages and the Container Apps console logs. Table names differ in the linked workspace context (`AppDependencies`, `AppTraces`). Logs and traces are sampled/diagnostic records, not a billing ledger. Telemetry ingestion must be verified after deployment; a configured connection string is not proof of delivery.

### Recovery

The service uses one active revision and retains three inactive revisions. To roll back, inspect revisions in the Azure portal and activate a previously healthy revision, or redeploy the previous known-good source commit and immutable image. Confirm its model configuration still exists, then rerun the smoke gate. Do not remove the current revision until the replacement is healthy. Decide retention/cleanup explicitly after the demonstration; the scripts never delete resources automatically.

## 5. GitHub Actions with OIDC

The included CI validates Python, JavaScript, static builds, parameters, and Bicep, then builds and exercises the actual Docker image. It needs no Azure credentials. The Azure deployment workflow is manual (`workflow_dispatch`) and targets an `azure-production` environment.

An administrator must configure an Entra application or deployment identity with a GitHub federated credential matching this repository and the `azure-production` environment. Set these GitHub environment variables:

| Variable | Value |
|---|---|
| `AZURE_CLIENT_ID` | Deployment principal client ID, separate from the app's runtime identity |
| `AZURE_TENANT_ID` | Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Intended subscription |
| `AZURE_RESOURCE_GROUP` | Dedicated resource group |
| `AZURE_LOCATION` | Confirmed model-supported region |

Use environment protection for the production workflow as appropriate. No long-lived Azure credential secret is required. The Azure deployment workflow requires this identity setup; adding YAML alone does not establish a successful Azure deployment. Ordinary application/container and Bicep validation jobs have passed in the public GitHub repository.

## Runtime controls and limits

- Strict JSON schemas, 16 KB request bodies, bounded question/history lengths, trusted hosts, same-origin POSTs, and restrictive browser content policy.
- Up to two model calls in flight and 24 model attempts/minute per process by default. POST admission is 60/minute per process. Each replica has its own counters; these are not a distributed abuse-control system.
- Two bounded attempts for transient provider failures, a shared answer deadline checked between operations, and a circuit that admits one recovery probe after cooldown. Transport timeouts apply to HTTP operations; they are not a hard wall-clock guarantee for the entire chain or credential acquisition.
- Only successful approved model answers enter the bounded 60-second in-memory cache. Cache hits are marked and do not claim new model executions.
- Public anonymous access is appropriate to the synthetic demo only. Real customer deployments need authentication, tenant separation, shared quotas/state, private-network review, retention policy, and security/load testing.
- Default minimum replicas is zero, so the first visit can have a cold start. Set minimum one for a scheduled judging demo after reviewing the additional cost.
- The SSE endpoint supports ordered replay and reconnect cursors. It is not wired into the existing browser playback and is not an Event Hubs consumer. Analytics now use the selected event-time prefix. Static views are precomputed at event/snapshot boundaries; the API computes the same projection for explicit analysis_time_seconds.

## Hackathon alignment and remaining evidence

All live fixtures, histories, tracking, wearables, teams, and players remain synthetic. Azure adds a concrete Microsoft AI and cloud integration path while preserving explainability and audience personalization. The three specialized roles have real shared evidence, handoffs, rejection, and failure recovery. This strengthens the technical and operational story; the judges still need a compelling working demonstration and measured value from orchestration.

Local tests and Bicep compilation have been performed in the development environment. Container build/run and Bicep compilation have passed in GitHub CI. Azure control-plane deployment, managed-identity permissions, model availability, cloud latency, and telemetry ingestion still require execution in the target Azure account. For submission, also provide the public GitHub repository and a public video under two minutes. Keep a private working repository if desired, then review and publish the submission source separately.

## Updated verification path

See [accuracy-and-evaluation.md](accuracy-and-evaluation.md) for the stricter fact-ID model contract, reproducible synthetic checks and live single-versus-three-role evaluation. The UI's verification report describes local deterministic checks. It must not be presented as an LLM accuracy percentage.
