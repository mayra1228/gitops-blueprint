import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.api.deps import get_infra_registry
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def _rescan_from_event(event):
    try:
        from app.domain.adapters.registry import build_default_registry
        from app.domain.inventory.service import InventoryService
        from app.domain.projects.service import ProjectService
        from app.infrastructure.database import async_session

        async with async_session() as db:
            proj_svc = ProjectService(db)
            projects = await proj_svc.list_projects()
            infra = get_infra_registry()
            for p in projects:
                git_cfg = p.get("git_config") or {}
                cfg_org = git_cfg.get("org", "")
                cfg_repo = git_cfg.get("repo", "")
                matches_legacy = (p["github_org"] == event.org and p["github_repo"] == event.repo)
                matches_cfg = (cfg_org == event.org and cfg_repo == event.repo)
                if matches_legacy or matches_cfg:
                    git_adapter = infra.get_git_adapter(p.get("git_adapter", "github"))
                    if git_adapter:
                        repo_path = await git_adapter.ensure_cloned(p.get("git_config", {}))
                        git_ref = await git_adapter.get_head_sha(p.get("git_config", {}))
                        svc = InventoryService(db, p["id"], build_default_registry())
                        await svc.scan(str(repo_path), git_ref=git_ref)
                        logger.info("Webhook: re-scan complete for project %s", p["id"])
    except Exception:
        logger.exception("Webhook: re-scan failed")


@router.post("")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    infra = get_infra_registry()
    webhook = infra.get_webhook_adapter("github")
    if webhook is None:
        raise HTTPException(status_code=500, detail="github webhook adapter not registered")

    if not webhook.verify_signature(settings.github_webhook_secret, body, signature):
        raise HTTPException(status_code=401, detail="invalid signature")

    event = webhook.parse_event(body)

    if event.action == "closed" and event.merged:
        logger.info("Webhook: PR merged for %s/%s, queueing re-scan", event.org, event.repo)
        background_tasks.add_task(_rescan_from_event, event)

    return {
        "received": True,
        "action": event.action,
        "pr_number": event.pr_number,
        "pr_state": event.raw_payload.get("pull_request", {}).get("state"),
        "pr_merged": event.merged,
    }
