from cicd_log_analyzer.analyzer import analyze_lines


def test_detects_proxy_and_disk_space_issues():
    result = analyze_lines([
        "Started by user demo-user",
        "ProxyError: 407 Proxy Authentication Required while connecting to Artifactory",
        "docker: Error response from daemon: No space left on device",
    ])

    rule_ids = {finding.rule_id for finding in result.findings}
    assert "PROXY_407" in rule_ids
    assert "DISK_SPACE" in rule_ids
    assert result.status == "FAILED"
    assert result.highest_severity == "high"


def test_clean_log_passes():
    result = analyze_lines([
        "Checkout completed",
        "Build completed successfully",
        "Tests: 42 passed",
    ])

    assert result.findings == []
    assert result.status == "PASSED"
    assert result.highest_severity == "none"


def test_summary_by_category_is_calculated():
    result = analyze_lines([
        "Read timed out while downloading dependency",
        "FAILED tests/test_cli.py::test_main",
    ])

    assert result.summary_by_category["Timeout"] == 1
    assert result.summary_by_category["Tests"] == 1
