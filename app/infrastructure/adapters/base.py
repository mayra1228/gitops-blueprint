from abc import ABC, abstractmethod
from pathlib import Path

from app.infrastructure.adapters.types import ExecutionResult, ExecutionStatus, PRResult, WebhookEvent


class GitAdapter(ABC):
    name: str = "generic"

    @abstractmethod
    async def ensure_cloned(self, config: dict) -> Path:
        ...

    @abstractmethod
    async def create_feature_branch(self, config: dict, branch: str, base: str = "main") -> Path:
        ...

    @abstractmethod
    async def apply_and_commit(self, config: dict, branch: str, file_path: str, content: str, message: str) -> str:
        ...

    @abstractmethod
    async def push(self, config: dict, branch: str) -> None:
        ...

    @abstractmethod
    async def get_head_sha(self, config: dict) -> str:
        ...

    @abstractmethod
    async def create_pr(self, config: dict, branch: str, title: str, body: str, base_branch: str = "main") -> PRResult:
        ...

    async def close(self) -> None:
        pass


class ExecutionAdapter(ABC):
    name: str = "generic"

    @abstractmethod
    async def trigger(self, config: dict, params: dict) -> ExecutionResult:
        ...

    @abstractmethod
    async def get_status(self, config: dict, execution_id: str) -> ExecutionStatus:
        ...


class WebhookAdapter(ABC):
    name: str = "generic"

    @abstractmethod
    def verify_signature(self, secret: str, body: bytes, signature_header: str) -> bool:
        ...

    @abstractmethod
    def parse_event(self, body: bytes) -> WebhookEvent:
        ...
