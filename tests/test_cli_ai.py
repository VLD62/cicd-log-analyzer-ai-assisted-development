from cicd_log_analyzer.analyzer import AnalysisResult
from cicd_log_analyzer.cli import main


def test_cli_ai_mode_invokes_ai_analyzer(monkeypatch, capsys):
    called = {}

    def fake_analyze_file_with_ai(path, config):
        called["path"] = path
        called["provider"] = config.provider
        return AnalysisResult(source_file=path, total_lines=1, findings=[])

    monkeypatch.setattr("cicd_log_analyzer.cli.analyze_file_with_ai", fake_analyze_file_with_ai)

    exit_code = main(["sample.log", "--mode", "ai", "--ai-provider", "openai"])

    assert exit_code == 0
    assert called["path"] == "sample.log"
    assert called["provider"] == "openai"
    out = capsys.readouterr().out
    assert "CI/CD Log Analyzer Report" in out


def test_cli_ai_mode_returns_nonzero_on_ai_error(monkeypatch, capsys):
    from cicd_log_analyzer.ai_analyzer import AIAnalysisError

    def fake_analyze_file_with_ai(path, config):
        raise AIAnalysisError("missing key")

    monkeypatch.setattr("cicd_log_analyzer.cli.analyze_file_with_ai", fake_analyze_file_with_ai)

    exit_code = main(["sample.log", "--mode", "ai"])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "AI ERROR:" in err