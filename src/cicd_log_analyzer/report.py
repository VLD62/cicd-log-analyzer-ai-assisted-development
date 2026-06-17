from __future__ import annotations

import html
import json
from pathlib import Path

from .analyzer import AnalysisResult


def render_text(result: AnalysisResult) -> str:
    lines = [
        "CI/CD Log Analyzer Report",
        "===========================",
        f"Source file: {result.source_file}",
        f"Total lines: {result.total_lines}",
        f"Status: {result.status}",
        f"Highest severity: {result.highest_severity}",
        "",
        "Summary by category:",
    ]
    if result.summary_by_category:
        for category, count in result.summary_by_category.items():
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- No issues detected")

    lines.extend(["", "Findings:"])
    if not result.findings:
        lines.append("- No findings. Pipeline log looks clean.")
    for finding in result.findings:
        lines.extend(
            [
                f"- [{finding.severity.upper()}] {finding.category} / {finding.rule_id} at line {finding.line_number}",
                f"  Evidence: {finding.line}",
                f"  Recommendation: {finding.recommendation}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_json(result: AnalysisResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n"


def render_html(result: AnalysisResult) -> str:
    rows = "".join(
        f"""
        <tr>
          <td><span class="badge {html.escape(f.severity)}">{html.escape(f.severity.upper())}</span></td>
          <td>{html.escape(f.category)}</td>
          <td>{html.escape(f.rule_id)}</td>
          <td>{f.line_number}</td>
          <td><code>{html.escape(f.line)}</code></td>
          <td>{html.escape(f.recommendation)}</td>
        </tr>
        """
        for f in result.findings
    )
    if not rows:
        rows = "<tr><td colspan='6'>No findings. Pipeline log looks clean.</td></tr>"

    categories = "".join(
        f"<li><strong>{html.escape(category)}</strong>: {count}</li>"
        for category, count in result.summary_by_category.items()
    ) or "<li>No issues detected</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CI/CD Log Analyzer Report</title>
  <style>
    @page {{ size: A4 landscape; margin: 12mm; }}
    body {{ font-family: Arial, sans-serif; margin: 18px; background: #f7f8fa; color: #222; }}
    .card {{ background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px #0001; }}
    h1 {{ margin-top: 0; }}
    .status {{ font-size: 22px; font-weight: bold; }}
    .FAILED {{ color: #b00020; }}
    .WARNING {{ color: #9a6700; }}
    .PASSED {{ color: #137333; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 14px; table-layout: fixed; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid #ddd; padding: 6px; text-align: left; vertical-align: top; word-break: break-word; overflow-wrap: anywhere; }}
    th {{ background: #eef1f5; }}
    code {{ white-space: pre-wrap; font-family: Consolas, monospace; font-size: 11px; }}
    .badge {{ border-radius: 999px; padding: 4px 8px; font-size: 12px; font-weight: bold; }}
    .high {{ background: #fce8e6; color: #b00020; }}
    .medium {{ background: #fff4ce; color: #7a4d00; }}
    .low {{ background: #e8f0fe; color: #174ea6; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>CI/CD Log Analyzer Report</h1>
    <p class="status {result.status}">Status: {result.status}</p>
    <p><strong>Source:</strong> {html.escape(result.source_file)}</p>
    <p><strong>Total lines:</strong> {result.total_lines}</p>
    <p><strong>Highest severity:</strong> {html.escape(result.highest_severity)}</p>
    <h2>Summary by category</h2>
    <ul>{categories}</ul>
    <h2>Findings</h2>
    <table>
      <thead>
        <tr>
          <th style='width:9%'>Severity</th><th style='width:14%'>Category</th><th style='width:14%'>Rule</th><th style='width:6%'>Line</th><th style='width:32%'>Evidence</th><th style='width:25%'>Recommendation</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</body>
</html>
"""


def write_report(result: AnalysisResult, fmt: str, output: str | Path | None = None) -> str:
    if fmt == "text":
        content = render_text(result)
    elif fmt == "json":
        content = render_json(result)
    elif fmt == "html":
        content = render_html(result)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    if output:
        Path(output).write_text(content, encoding="utf-8")
    return content
