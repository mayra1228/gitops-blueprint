import hashlib
import hmac
import json

from app.infrastructure.adapters.base import WebhookAdapter
from app.infrastructure.adapters.types import WebhookEvent


class BitBucketWebhookAdapter(WebhookAdapter):
    name = "bitbucket"

    def verify_signature(self, secret: str, body: bytes, signature_header: str) -> bool:
        if not secret:
            return True
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if signature_header.startswith("sha256="):
            return hmac.compare_digest(signature_header, expected)
        return hmac.compare_digest("sha256=" + signature_header, expected)

    def parse_event(self, body: bytes) -> WebhookEvent:
        payload = json.loads(body)
        event_type = payload.get("event_type", "pullrequest")
        pr_data = payload.get("pullrequest", {})
        repo_data = payload.get("repository", {})
        full_name = repo_data.get("full_name", "")
        org, _, repo = full_name.partition("/") if full_name else ("", "", "")
        action = pr_data.get("state", "unknown")
        return WebhookEvent(
            provider="bitbucket",
            event_type=event_type,
            action=action,
            org=org,
            repo=repo,
            branch=pr_data.get("source", {}).get("branch", {}).get("name", ""),
            pr_number=pr_data.get("id"),
            merged=payload.get("pullrequest", {}).get("state") == "MERGED",
            raw_payload=payload,
        )
