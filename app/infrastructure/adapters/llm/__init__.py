"""LLM Gateway abstraction — pluggable AI backend for review and diagnostics.

Integrates patterns from:
- pr-agent: Jinja2 prompt templates, structured output schema, LiteLLM routing
- k8sgpt: "filter first, then AI" — pre-filter errors before LLM call
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReviewFinding:
    field: str
    severity: str  # high / medium / low
    issue: str
    recommendation: str


@dataclass
class ReviewResult:
    risk_level: str  # high / medium / low
    summary: str
    findings: List[ReviewFinding] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    prompt_hash: str = ""
    token_count: int = 0
    latency_ms: int = 0
    response_hash: str = ""
    raw_response: str = ""


@dataclass
class DiagnosticResult:
    root_cause: str
    remediation: str
    confidence: str  # high / medium / low
    model: str = ""
    provider: str = ""
    prompt_hash: str = ""
    token_count: int = 0
    latency_ms: int = 0
    raw_response: str = ""


class LLMGateway(ABC):
    """Abstract base for all LLM backends."""

    @abstractmethod
    async def review(self, prompt: str, context: Dict[str, Any]) -> ReviewResult:
        """Generate an AI Review artifact (read-only, no state transitions)."""

    @abstractmethod
    async def diagnose(self, error_text: str, context: Dict[str, Any]) -> DiagnosticResult:
        """Analyze execution failure, output root-cause + remediation."""

    @abstractmethod
    def get_name(self) -> str:
        """Return provider name (ollama, openai, azure_openai)."""
