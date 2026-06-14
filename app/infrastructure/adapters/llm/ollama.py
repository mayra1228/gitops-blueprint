"""Ollama LLM Gateway — local model backend (DeepSeek-R1, Llama3, etc.)."""

import hashlib
import json
import time
from typing import Any, Dict

import httpx

from app.infrastructure.adapters.llm import (
    DiagnosticResult,
    LLMGateway,
    ReviewFinding,
    ReviewResult,
)


class OllamaGateway(LLMGateway):

    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "deepseek-r1"):
        self.endpoint = endpoint.rstrip("/")
        self.model = model

    async def review(self, prompt: str, context: Dict[str, Any]) -> ReviewResult:
        start = time.monotonic()
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

        response_text = await self._generate(prompt)
        latency_ms = int((time.monotonic() - start) * 1000)
        response_hash = hashlib.sha256(response_text.encode()).hexdigest()[:16]

        findings = self._parse_review_findings(response_text)
        risk_level = self._determine_risk_level(findings)

        return ReviewResult(
            risk_level=risk_level,
            summary=self._extract_summary(response_text),
            findings=findings,
            model=self.model,
            provider="ollama",
            prompt_hash=prompt_hash,
            token_count=len(prompt.split()) + len(response_text.split()),
            latency_ms=latency_ms,
            response_hash=response_hash,
            raw_response=response_text,
        )

    async def diagnose(self, error_text: str, context: Dict[str, Any]) -> DiagnosticResult:
        start = time.monotonic()
        prompt_hash = hashlib.sha256(error_text.encode()).hexdigest()[:16]

        response_text = await self._generate(error_text)
        latency_ms = int((time.monotonic() - start) * 1000)

        return DiagnosticResult(
            root_cause=self._extract_section(response_text, "root cause", "error"),
            remediation=self._extract_section(response_text, "solution", "remediation"),
            confidence="medium",
            model=self.model,
            provider="ollama",
            prompt_hash=prompt_hash,
            token_count=len(error_text.split()) + len(response_text.split()),
            latency_ms=latency_ms,
            raw_response=response_text,
        )

    def get_name(self) -> str:
        return "ollama"

    async def _generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.endpoint}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    def _parse_review_findings(self, text: str) -> list:
        findings = []
        for line in text.split("\n"):
            line = line.strip()
            if "|" in line and line.count("|") >= 3:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3 and parts[0].lower() in ("high", "medium", "low"):
                    findings.append(ReviewFinding(
                        field="",
                        severity=parts[0].lower(),
                        issue=parts[1] if len(parts) > 1 else "",
                        recommendation=parts[2] if len(parts) > 2 else "",
                    ))
        return findings

    def _determine_risk_level(self, findings: list) -> str:
        if any(f.severity == "high" for f in findings):
            return "high"
        if any(f.severity == "medium" for f in findings):
            return "medium"
        return "low"

    def _extract_summary(self, text: str) -> str:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return lines[0][:300] if lines else "No summary available"

    def _extract_section(self, text: str, *keywords: str) -> str:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in keywords):
                section = "\n".join(lines[i:i+5]).strip()
                return section[:500]
        return text[:500]
