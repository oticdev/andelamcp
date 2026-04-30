# GCP Deployment Issues

## Blockers

- [x] **1. No remote Terraform backend** — GCS backend added; bucket supplied via `-backend-config="bucket=<TF_STATE_BUCKET>"` in CI. One-time prereq: create the bucket manually.
- [x] **2. API secret in plaintext env var** — `OPENAI_API_KEY` stored in Secret Manager; Cloud Run service account granted `secretAccessor` role.
- [x] **3. GCP auth uses JSON key file** — switched to Workload Identity Federation (`workload_identity_provider` + `service_account`; `id-token: write` permission already present).
- [x] **4. Deploy runs without tests** — `test` job added to `deploy.yml`; `deploy` job has `needs: test`.

## Significant

- [x] **5. `image_tag` defaults to `"latest"`** — default removed from `variables.tf`; now a required variable.
- [x] **6. No resource limits on Cloud Run container** — `resources.limits` set to `cpu = "1"`, `memory = "512Mi"`.
- [x] **7. OpenAI client created per request** — client initialised once in FastAPI `lifespan` and injected via `get_openai_client` dependency.
- [x] **8. No error handling on OpenAI failures** — unhandled exceptions still return 500 but are now logged with full context; route-level guard returns clean 500 when API key is missing.
- [x] **9. No response model on `POST /chat`** — `ChatResponse` schema defined and wired to the route.

## Minor

- [x] **10. Gunicorn missing `--workers` flag** — `--workers 2 --timeout 120` added to Dockerfile CMD.
- [x] **11. No Cloud Run health check** — `startup_probe` and `liveness_probe` added to `main.tf`, both pointing at `/health`.
- [x] **12. CORS origins not injected by Terraform** — `BACKEND_CORS_ORIGINS` env var added to Cloud Run template; supplied via `vars.BACKEND_CORS_ORIGINS` in CI.
- [x] **13. CI doesn't run on `staging` branch** — `staging` added to `ci.yml` branch triggers.

## One-time bootstrap steps before first deploy

1. Create a GCS bucket for Terraform state and add its name as a **repository variable** `TF_STATE_BUCKET`.
2. Set up Workload Identity Federation in GCP; add the full provider resource name as **secret** `GCP_WORKLOAD_IDENTITY_PROVIDER` and the service account email as **secret** `GCP_SERVICE_ACCOUNT`.
3. Grant the service account these roles: Cloud Run Admin, Artifact Registry Writer, Secret Manager Admin, Service Account User, Storage Object Admin (for TF state bucket).
4. Add **secret** `OPENAI_API_KEY` and **variables** `BACKEND_CORS_ORIGINS` and `LOG_LEVEL` to the repository.
