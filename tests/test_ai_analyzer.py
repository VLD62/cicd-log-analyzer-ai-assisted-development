import pytest

from cicd_log_analyzer.ai_analyzer import AIAnalysisError, AIConfig, analyze_text_with_ai
from cicd_log_analyzer.analyzer import analyze_lines


def test_analyze_text_with_ai_maps_findings(monkeypatch):
    def fake_request_findings(log_text, config):
        assert "ProxyError" in log_text
        assert config.provider == "openai"
        return [
            {
                "rule_id": "AI_PROXY_AUTH",
                "category": "Network / Proxy",
                "severity": "high",
                "line_number": 2,
                "line": "ProxyError: 407 Proxy Authentication Required",
                "recommendation": "Validate proxy credentials.",
            }
        ]

    monkeypatch.setattr("cicd_log_analyzer.ai_analyzer._request_findings", fake_request_findings)

    result = analyze_text_with_ai(
        "Build started\nProxyError: 407 Proxy Authentication Required\n",
        source_file="memory.log",
        config=AIConfig(),
    )

    assert result.source_file == "memory.log"
    assert result.total_lines == 3
    assert result.status == "FAILED"
    assert result.highest_severity == "high"
    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "AI_PROXY_AUTH"


def test_analyze_text_with_ai_rejects_invalid_severity(monkeypatch):
    def fake_request_findings(log_text, config):
        return [
            {
                "rule_id": "AI_UNKNOWN",
                "category": "Other",
                "severity": "critical",
                "line_number": 1,
                "line": "boom",
                "recommendation": "x",
            }
        ]

    monkeypatch.setattr("cicd_log_analyzer.ai_analyzer._request_findings", fake_request_findings)

    with pytest.raises(AIAnalysisError):
        analyze_text_with_ai("boom", source_file="x.log", config=AIConfig())

def test_docker_pull_failed_is_not_test_failure():
    result = analyze_lines([
        "ERROR: docker pull failed for registry.example.com/demo/build-image:3.5",
    ])

    rule_ids = {finding.rule_id for finding in result.findings}

    assert "DOCKER_DAEMON" in rule_ids
    assert "TEST_FAILURE" not in rule_ids