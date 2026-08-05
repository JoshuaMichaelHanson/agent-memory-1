from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import ValidationError


@dataclass(frozen=True, slots=True)
class SensitiveFinding:
    label: str
    line_number: int


SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private key block",
        re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
    ),
    (
        "credentialed URL",
        re.compile(r"\b[a-z][a-z0-9+.-]{2,}://[^\s/:@]+:[^\s/@]+@", re.IGNORECASE),
    ),
    (
        "authorization bearer token",
        re.compile(r"\bauthorization\s*[:=]\s*bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    ),
    (
        "secret assignment",
        re.compile(
            r"\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret|connection[_-]?string)\b"
            r"\s*[:=]\s*['\"]?[^\s'\"]{8,}",
            re.IGNORECASE,
        ),
    ),
    (
        "AWS access key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "GitHub token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    ),
)


def find_sensitive_content(content: str) -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []
    for line_number, line in enumerate(content.splitlines() or [content], start=1):
        for label, pattern in SENSITIVE_PATTERNS:
            if pattern.search(line):
                findings.append(SensitiveFinding(label=label, line_number=line_number))
    return findings


def validate_no_sensitive_content(content: str, *, location: str, allow_sensitive: bool = False) -> None:
    if allow_sensitive:
        return
    findings = find_sensitive_content(content)
    if not findings:
        return
    summary = "; ".join(f"{finding.label} on line {finding.line_number}" for finding in findings[:3])
    if len(findings) > 3:
        summary += f"; {len(findings) - 3} more"
    raise ValidationError(
        f"Sensitive content detected in {location}: {summary}. "
        "Remove the sensitive value or rerun with --allow-sensitive for intentional local-only storage."
    )
