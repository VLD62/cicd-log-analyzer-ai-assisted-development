from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .rules import RULES, SEVERITY_SCORE, Rule


@dataclass
class Finding:
    rule_id: str
    category: str
    severity: str
    line_number: int
    line: str
    recommendation: str


@dataclass
class AnalysisResult:
    source_file: str
    total_lines: int
    findings: list[Finding]

    @property
    def status(self) -> str:
        if any(f.severity == "high" for f in self.findings):
            return "FAILED"
        if self.findings:
            return "WARNING"
        return "PASSED"

    @property
    def highest_severity(self) -> str:
        if not self.findings:
            return "none"
        return max(self.findings, key=lambda f: SEVERITY_SCORE.get(f.severity, 0)).severity

    @property
    def summary_by_category(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for finding in self.findings:
            summary[finding.category] = summary.get(finding.category, 0) + 1
        return dict(sorted(summary.items(), key=lambda item: item[0]))

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status
        data["highest_severity"] = self.highest_severity
        data["summary_by_category"] = self.summary_by_category
        return data


def analyze_lines(lines: Iterable[str], source_file: str = "<memory>") -> AnalysisResult:
    findings: list[Finding] = []
    total_lines = 0

    for line_number, raw_line in enumerate(lines, start=1):
        total_lines = line_number
        line = raw_line.rstrip("\n")
        for rule in RULES:
            if rule.pattern.search(line):
                findings.append(_finding_from_rule(rule, line_number, line))

    findings.sort(key=lambda f: (-SEVERITY_SCORE.get(f.severity, 0), f.line_number, f.rule_id))
    return AnalysisResult(source_file=source_file, total_lines=total_lines, findings=findings)


def analyze_file(path: str | Path) -> AnalysisResult:
    log_path = Path(path)
    if not log_path.exists():
        raise FileNotFoundError(f"Log file does not exist: {log_path}")
    with log_path.open("r", encoding="utf-8", errors="replace") as stream:
        return analyze_lines(stream, source_file=str(log_path))


def _finding_from_rule(rule: Rule, line_number: int, line: str) -> Finding:
    return Finding(
        rule_id=rule.rule_id,
        category=rule.category,
        severity=rule.severity,
        line_number=line_number,
        line=line.strip(),
        recommendation=rule.recommendation,
    )
