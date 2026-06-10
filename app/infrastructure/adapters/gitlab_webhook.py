import hmac
import json

from app.infrastructure.adapters.base import WebhookAdapter
from app.infrastructure.adapters.types import WebhookEvent


class GitLabWebhookAdapter(WebhookAdapter):
    name = "gitlab"

    def verify_signature(self, secret: str, body: bytes, signature_header: str) -> bool:
        if not secret:
            return True
        return hmac.compare_digest(signature_header, secret)

    def parse_event(self, body: bytes) -> WebhookEvent:
        payload = json.loads(body)
        object_kind = payload.get("object_kind", "unknown")
        attrs = payload.get("object_attributes", {})
        project = payload.get("project", {})
        path = project.get("path_with_namespace", "")
        org, _, repo = path.partition("/") if path else ("", "", "")
        return WebhookEvent(
            provider="gitlab",
            event_type=object_kind,
            action=attrs.get("action", attrs.get("state", "unknown")),
            org=org,
            repo=repo,
            branch=attrs.get("source_branch", attrs.get("source", {}).get("name", "")),
            pr_number=attrs.get("iid"),
            merged=attrs.get("state") == "merged",
            raw_payload=payload,
        )
