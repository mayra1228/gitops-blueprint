import hashlib
import hmac
import json

from app.infrastructure.adapters.base import WebhookAdapter
from app.infrastructure.adapters.types import WebhookEvent


class GitHubWebhookAdapter(WebhookAdapter):
    name = "github"

    def verify_signature(self, secret: str, body: bytes, signature_header: str) -> bool:
        if not secret:
            return True
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature_header, expected)

    def parse_event(self, body: bytes) -> WebhookEvent:
        payload = json.loads(body)
        action = payload.get("action", "unknown")
        pr_data = payload.get("pull_request", {})
        base_repo = pr_data.get("base", {}).get("repo", {})
        return WebhookEvent(
            provider="github",
            event_type=payload.get("zen", "") or "pull_request",
            action=action,
            org=base_repo.get("owner", {}).get("login", ""),
            repo=base_repo.get("name", ""),
            branch=pr_data.get("head", {}).get("ref", ""),
            pr_number=pr_data.get("number"),
            merged=pr_data.get("merged", False),
            raw_payload=payload,
        )
