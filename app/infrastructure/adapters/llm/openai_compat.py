"""OpenAI-compatible LLM Gateway — supports OpenAI and Azure OpenAI."""

import hashlib
import time
from typing import Any, Dict

import httpx

from app.infrastructure.adapters.llm import (
    DiagnosticResult,
    LLMGateway,
    ReviewFinding,
    ReviewResult,
)


class OpenAICompatGateway(LLMGateway):

    def __init__(
        self,
        endpoint: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        api_key: str = "",
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key

    async def review(self, prompt: str, context: Dict[str, Any]) -> ReviewResult:
        system = context.get("system_prompt", "You are an IaC security auditor.")
        start = time.monotonic()
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

        resp_data = await self._chat(system, prompt)
        response_text = resp_data.get("content", "")
        usage = resp_data.get("usage", {})
        latency_ms = int((time.monotonic() - start) * 1000)
        response_hash = hashlib.sha256(response_text.encode()).hexdigest()[:16]

        findings = self._parse_findings(response_text)
        risk_level = "high" if any(f.severity == "high" for f in findings) else (
            "medium" if any(f.severity == "medium" for f in findings) else "low"
        )

        return ReviewResult(
            risk_level=risk_level,
            summary=response_text.split("\n")[0][:300] if response_text else "",
            findings=findings,
            model=self.model,
            provider="openai",
            prompt_hash=prompt_hash,
            token_count=usage.get("total_tokens", 0),
            latency_ms=latency_ms,
            response_hash=response_hash,
            raw_response=response_text,
        )

    async def diagnose(self, error_text: str, context: Dict[str, Any]) -> DiagnosticResult:
        system = "You are a DevOps expert. Analyze the error and provide root cause and remediation steps."
        start = time.monotonic()
        prompt_hash = hashlib.sha256(error_text.encode()).hexdigest()[:16]

        resp_data = await self._chat(system, error_text)
        response_text = resp_data.get("content", "")
        usage = resp_data.get("usage", {})
        latency_ms = int((time.monotonic() - start) * 1000)

        return DiagnosticResult(
            root_cause=response_text[:500],
            remediation=response_text[500:1000] if len(response_text) > 500 else "",
            confidence="medium",
            model=self.model,
            provider="openai",
            prompt_hash=prompt_hash,
            token_count=usage.get("total_tokens", 0),
            latency_ms=latency_ms,
            raw_response=response_text,
        )

    def get_name(self) -> str:
        return "openai"

    async def _chat(self, system: str, user: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data.get("choices", [{}])[0].get("message", {})
            return {"content": choice.get("content", ""), "usage": data.get("usage", {})}

    def _parse_findings(self, text: str) -> list:
        findings = []
        for line in text.split("\n"):
            line = line.strip()
            if "|" in line and line.count("|") >= 3:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3 and parts[0].lower() in ("high", "medium", "low"):
                    findings.append(ReviewFinding(
                        field="", severity=parts[0].lower(),
                        issue=parts[1], recommendation=parts[2] if len(parts) > 2 else "",
                    ))
        return findings
