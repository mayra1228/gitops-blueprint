import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.api.deps import get_infra_registry
from app.api.github import _rescan_from_event
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("")
async def bitbucket_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature", "")

    infra = get_infra_registry()
    webhook = infra.get_webhook_adapter("bitbucket")
    if webhook is None:
        raise HTTPException(status_code=500, detail="bitbucket webhook adapter not registered")

    if not webhook.verify_signature(settings.bitbucket_webhook_secret, body, signature):
        raise HTTPException(status_code=401, detail="invalid signature")

    event = webhook.parse_event(body)

    if event.merged:
        logger.info("BitBucket webhook: PR merged for %s/%s, queueing re-scan", event.org, event.repo)
        background_tasks.add_task(_rescan_from_event, event)

    return {"received": True, "action": event.action, "pr_number": event.pr_number, "pr_merged": event.merged}
