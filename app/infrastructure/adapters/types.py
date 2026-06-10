from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PRResult:
    url: str
    number: int
    branch: str
    status: str


@dataclass
class ExecutionResult:
    execution_id: str
    status: str
    external_url: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class ExecutionStatus:
    execution_id: str
    status: str
    logs_url: Optional[str] = None


@dataclass
class WebhookEvent:
    provider: str
    event_type: str
    action: str
    org: str
    repo: str
    branch: str = ""
    pr_number: Optional[int] = None
    merged: bool = False
    raw_payload: dict = field(default_factory=dict)
