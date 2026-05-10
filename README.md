# Memory Lens MVP Backend

Minimal backend foundation for Memory Lens with local runtime and AWS ECS Fargate deployment.

## Architecture (MVP)

- **API**: FastAPI service handling session + audio chunk ingestion.
- **Storage**: local filesystem for chunk files (`data/uploads/...`) and SQLite for metadata.
- **Async placeholder pipeline**: uploaded chunk status flows `uploaded -> queued -> processed` using FastAPI background tasks.
- **Deployment**: GitHub Actions -> ECR (`memory-lens-api`) -> ECS Fargate service (`memory-lens-backend-service`) on cluster (`memory-lens-cluster`) in region `ap-south-1`.

## API Endpoints

- `GET /healthz` -> health response.
- `POST /v1/sessions` -> create session (`session_id`, `created_at`).
- `POST /v1/sessions/{session_id}/chunks` -> multipart chunk upload (`file`, `start_ms`, `end_ms`, `source`, `device_id?`).
- `GET /v1/sessions/{session_id}` -> session details + chunks.

## Local Development

### 1) Environment

```bash
cp .env.example .env
```

### 2) Run with Docker Compose

```bash
docker compose up --build
```

API will be available at `http://localhost:8000`.

Health check:

```bash
curl http://localhost:8000/healthz
```

### 3) Run tests/lint locally

```bash
make install
make lint
make test
```

## AWS ECS/Fargate Deployment Checklist (OIDC)

### Required fixed deployment values

- AWS Region: `ap-south-1`
- ECR Repository: `memory-lens-api`
- ECS Cluster: `memory-lens-cluster`
- ECS Service: `memory-lens-backend-service`
- Domain: none

### One-time AWS setup

- [ ] Create ECR repository `memory-lens-api` in `ap-south-1`.
- [ ] Create ECS cluster `memory-lens-cluster`.
- [ ] Create (or prepare) ECS Fargate service `memory-lens-backend-service` wired to target group/networking.
- [ ] Create CloudWatch log group `/ecs/memory-lens-backend-service`.
- [ ] Create task execution role (`ecsTaskExecutionRole`) and application task role.
- [ ] Update `.aws/task-definition.json` role ARNs and any env/logging values as needed.

### GitHub OIDC setup

1. In IAM, add GitHub OIDC provider (`token.actions.githubusercontent.com`) if not already present.
2. Create IAM role for GitHub Actions deployment (example trust policy below).
3. Attach permissions allowing ECR push and ECS deploy actions.
4. In GitHub repo secrets, set:
   - `AWS_ROLE_TO_ASSUME` = deployment role ARN.

Example trust policy (replace placeholders):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:dsr5k/memory-lens:*"
        }
      }
    }
  ]
}
```

## GitHub Actions Workflows

- **CI** (`.github/workflows/ci.yml`): lint, unit tests, Docker build.
- **Deploy** (`.github/workflows/deploy-ecs.yml`): OIDC auth -> build/push image to ECR -> render ECS task definition -> deploy to ECS service.

Deploy runs on push to `main` (or manually via `workflow_dispatch`).
