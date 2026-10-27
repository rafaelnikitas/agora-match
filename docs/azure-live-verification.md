# Azure and Foundry: live verification and completion plan

Verified on **27 October 2026** against the public [Azure application](https://agora-demo-d3ysdvzmwpuoi.orangewater-9594c3f1.swedencentral.azurecontainerapps.io/).

## Completed integration

- The UI and Python API run together on Azure Container Apps over HTTPS.
- The API invokes the deployed **GPT-OSS-120B, version 1** model in a Microsoft Foundry AIServices project, using managed identity. All three specialist roles share the `agora-chat` model deployment.
- The match analyst selects known fact IDs; the audience narrator writes for Fan, Analyst or Coach; the evidence reviewer checks the draft. Schemas and application code validate the handoffs.
- A rejected draft gets at most one narration correction and must pass the same validation and review. Otherwise the application returns its deterministic evidence fallback.
- A private Azure Container Registry supplies an immutable image. Model keys are excluded from the frontend; local model key authentication is disabled in the infrastructure.
- Application Insights and Log Analytics are configured. Application request metrics were observed in the Azure Portal during deployment; a retained query of individual agent spans is still a follow-up task.

Orchestration runs in application Python. This deployment uses **Foundry Models**; it does not deploy Foundry Agent Service or Microsoft Agent Framework.

## Fresh live acceptance results

Seven fixed scenarios were exercised for each of the three audiences, covering both synthetic fixtures.

| Measure | Observed result |
|---|---:|
| Requests | 21 |
| Expected topic and evidence-value checks passed | 21/21 |
| Fresh AI answers, without cached responses | 21/21 |
| Answers recovered after a rejected draft | 5 |
| Final deterministic fallbacks in this run | 0 |
| Median API response latency | 9,579 ms |
| p95 API response latency | 12,973 ms |
| Reported stage tokens | 60,456 |

Of the five recovered answers, two failed the code contract on their first narration and three were rejected by the reviewer. Their recorded stage paths show the correction and subsequent review.

These are **development acceptance cases used during hardening**, not an independent test set. They establish execution, expected evidence routing and recovery on this sample. They do not prove qualitative correctness, coaching usefulness, future reliability, or superiority over a single-agent approach. Token totals reflect reported model-stage usage and are not a billing ledger. Latencies exclude the deliberate pauses between requests and do not characterize cold starts.

- [Full per-request evaluation](evidence/azure-live-evaluation.json)
- [Runtime readiness and capability response](evidence/azure-runtime-status.json)
- [Fixed evaluation cases](../scripts/evaluation-cases.json)

### Recorded deployment provenance

- Runtime source commit: `30990917600ac7f02029596743892bd4f5d78a61`.
- Runtime image digest: `sha256:e0bb67da3c8fca730bc18e06dcddd4e0dd311fcbf54407a768d97f5affeae1f2`.
- Region: Sweden Central. Trial profile: GlobalStandard model capacity 50; container replicas 0–1.
- The deployment source passed the 67 unit/API tests and container/infrastructure CI checks.
- The trial spending limit was last verified **On** during deployment. No account upgrade was performed. Budget alerts and a cleanup date have not been configured as part of this verification.

The source commit and image record come from the completed deployment. This resumed session rechecked public readiness, managed-identity model execution and the acceptance suite; it did not perform a new authenticated Azure control-plane audit. Later documentation/workflow commits do not imply a new runtime deployment.

## Reproduce the public-app checks

No Azure keys, account access or Python dependencies are needed for these standard-library scripts:

```bash
python scripts/smoke_azure.py --url https://agora-demo-d3ysdvzmwpuoi.orangewater-9594c3f1.swedencentral.azurecontainerapps.io --require-ai
python scripts/evaluate.py --url https://agora-demo-d3ysdvzmwpuoi.orangewater-9594c3f1.swedencentral.azurecontainerapps.io --require-ai --pause-seconds 10 --output build/azure-live-evaluation.json
```

They consume the demo's model allowance and Azure credit. A failed gate stays failed; inspect its reported reason. The manual **Verify deployed Agora demo** GitHub workflow performs these same checks and preserves its report for 30 days. Its YAML is prepared; the workflow itself has not yet been run in GitHub.

## Remaining tasks, in recommended order

| Priority | Task | Completion evidence | Status |
|---|---|---|---|
| P1 | Human review of held-out Fan, Analyst and Coach questions | Reviewed outputs for support, uncertainty, usefulness, and language; include unsupported questions and multiple match clocks | Pending; runtime acceptance is complete |
| P1 | Refresh the submission video with the Azure-backed experience | Show a real Foundry answer, fact links and a rejected-draft correction; publish under two minutes on an accepted video platform | Updated Azure walkthrough recorded and captioned. [YouTube URL](https://youtu.be/nxC-Q8esbOQ) recorded; publication reported by entrant; final signed-out check pending. Actual three-stage trace shown; correction examples remain in the acceptance report. |
| P1 | Retain operational proof | Application Insights query/export showing the three agent spans, rejection/fallback reasons and latency | Request-metric ingestion observed; detailed export pending |
| P1 | Check costs and judging availability | Review remaining credit/expiry, set budget alerts, test a cold visit, and choose a cleanup date | Spending protection last checked On; operational review pending |
| P2 | Enable automated Azure deployment from GitHub | Federated credential scoped to this repo and protected environment; reviewed resource-group permissions; successful manual deployment run | Trial-compatible workflow prepared; Azure identity grants not created |
| P2 | Run direct single-versus-three-role comparison | Configure the separate evaluation identity/variables and retain outputs, tokens, latency and independent review | Harness prepared; comparison not run |
| Optional | Run a Foundry-hosted quality evaluation | Compatible judge-model access/quota, evaluation permissions, reviewed JSONL/CSV dataset, evaluation run ID and scored results | Not run; separate from the verified runtime calls |
| Optional | Adopt Foundry Agent Service or Microsoft Agent Framework | A purposeful migration with equivalent grounding, recovery and measured benefit | Not required to keep the current app working |

### GitHub permissions are still a deliberate setup step

The public-demo verification workflow needs no Azure identity. Direct model evaluation and infrastructure deployment are separate workflows with different permissions. The latter currently provisions the foundation and its listed role assignments, so it needs both resource-management and role-assignment rights in the isolated resource group. Prefer separating privileged bootstrap from routine app updates before enabling routine CD. No new CI identity or Azure role grants were made in this resumed work.

The deployment workflow now builds and exercises its image on the GitHub runner and pushes an archive to the private registry. It defaults to the trial parameter profile and avoids ACR Tasks. Its Azure login still requires environment configuration and authorization.

### Native Foundry evaluation

Microsoft's [portal evaluation guidance](https://learn.microsoft.com/en-us/azure/foundry/how-to/evaluate-generative-ai-app) distinguishes evaluation of an existing dataset from runtime inference. AI-assisted quality evaluation requires a compatible GPT judge-model connection and suitable project permissions. Check trial eligibility and quota before provisioning anything. The current working inference deployment does not by itself establish access to a judge model.

## Submission claims supported by this evidence

Use: **“Agora Match runs on Azure Container Apps and uses managed identity to invoke Microsoft Foundry models through three evidence-bounded specialist roles, with one controlled correction and a safe fallback.”**

Keep semantic accuracy percentages, production-readiness claims and multi-agent superiority claims conditional on further evaluation. All match data, history, tracking and wearable examples remain synthetic.
