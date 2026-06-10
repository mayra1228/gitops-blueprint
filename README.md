# GitOps Platform — K8S Resource Change Management

Terraform GitOps Control Plane for K8S resource change lifecycle management. Submit Change Requests via a visual workflow with patch preview, validation, dry-run planning, approval, and execution — all tracked with a full audit trail.

## Quick Start

```bash
# 1. Start the platform
docker compose up -d

# 2. Seed demo data (project + inventory scan)
python3 scripts/seed.py

# 3. Run the demo workflow
bash scripts/demo.sh

# 4. Open in browser
open http://localhost:9090/
```

## API Overview

```
GET  /api/health
POST /api/auth/login

GET  /api/projects
POST /api/projects

GET  /api/{project}/inventory/summary
GET  /api/{project}/inventory/overview
GET  /api/{project}/inventory/objects
POST /api/{project}/inventory/scan

GET  /api/{project}/changes
POST /api/{project}/changes
POST /api/{project}/changes/draft-preview
GET  /api/{project}/changes/{id}
POST /api/{project}/changes/{id}/validate
POST /api/{project}/changes/{id}/plan
POST /api/{project}/changes/{id}/submit
POST /api/{project}/changes/{id}/approve
POST /api/{project}/changes/{id}/execute
POST /api/{project}/changes/{id}/refresh-inventory
GET  /api/{project}/changes/{id}/audit

GET  /api/{project}/templates
GET  /api/{project}/adapters

POST /api/webhooks/github
```

## Change Lifecycle

```
Draft → PatchGenerated → ValidationPassed → PlanReady
                                              ↓
                                         PendingApproval
                                        ↙              ↘
                                   Approved          Rejected
                                      ↓
                                 ExecutionReady
                                      ↓
                               InventoryRefreshed
```

## Architecture

```
Browser (Vanilla JS SPA)
    ↓ fetch()
FastAPI (Python async)
    ↓ SQLAlchemy async
PostgreSQL 14
    ↓ (Execute phase)
GitHub REST API (PR creation)
```

## Project Structure

```
gitops-platform/
├── app/
│   ├── main.py              # FastAPI entry point + lifespan
│   ├── config.py             # Settings (env-based)
│   ├── api/                  # Route handlers
│   │   ├── router.py
│   │   ├── deps.py           # Dependency injection
│   │   ├── inventory.py, changes.py, templates.py, ...
│   │   └── github.py         # Webhook receiver
│   ├── domain/               # Business logic
│   │   ├── changes/          # Change state machine
│   │   ├── inventory/        # YAML scanner + PostgreSQL repo
│   │   ├── adapters/         # Resource type adapters
│   │   ├── templates/        # Template registry
│   │   └── projects/         # Multi-project support
│   ├── infrastructure/
│   │   ├── database.py       # SQLAlchemy async engine
│   │   └── github_client.py  # GitHub REST client
│   └── ui/                   # Server-rendered SPA
├── demo_data/                # Sample YAML for scanner
├── scripts/
│   ├── seed.py               # Seed demo project + scan
│   └── demo.sh               # Full workflow demo
├── tests/                    # Integration tests
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://gitops:gitops_dev@db:5432/gitops_platform` | DB connection |
| `JWT_SECRET` | `dev-secret-change-in-production` | JWT signing key |
| `GITHUB_TOKEN` | (optional) | GitHub PAT for PR creation |
| `DEMO_DATA_ROOT` | `/demo_data` | Path to demo YAML files |

## Running Tests

```bash
# With Docker running
python3 -m pytest tests/ -v
```
# gitops-blueprint
