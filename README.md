# CI/CD Log Analyzer

Small Python CLI tool created for the AI-Assisted Development exam assignment.
It analyzes Jenkins/Bamboo/GitHub Actions logs and generates actionable reports in text, JSON, or HTML format.

## Why this project?

DevOps engineers often spend time reading long CI/CD logs. This tool detects common failure patterns such as proxy problems, DNS failures, disk space issues, Docker daemon problems, authentication errors, timeouts, compilation errors, and test failures.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest
python -m cicd_log_analyzer.cli sample_logs/jenkins_failed.log --format text
python -m cicd_log_analyzer.cli sample_logs/jenkins_failed.log --format html --output reports/report.html
pytest -q
```

## AI mode (cloud provider)

The tool now supports an AI-only analysis mode.

### Install optional AI dependencies

```bash
pip install -e .[ai]
```

### Configure API keys

```bash
export OPENAI_API_KEY="your-key"
# or
export ANTHROPIC_API_KEY="your-key"
```

### Run AI analysis

```bash
python -m cicd_log_analyzer.cli sample_logs/jenkins_failed.log --mode ai --ai-provider openai --ai-model gpt-4.1-mini --format text
python -m cicd_log_analyzer.cli sample_logs/jenkins_failed.log --mode ai --ai-provider anthropic --ai-model claude-3-5-sonnet-latest --format json --output reports/report.json
```

### Useful AI flags

- `--ai-timeout` request timeout in seconds (default: 30)
- `--ai-max-input-chars` maximum log text sent to provider (default: 40000)
- `--ai-api-key` override env-var based key lookup

## Architecture

The tool follows a modular three-layer design:

```
CLI (cli.py)
  ├─ Regex Analyzer (analyzer.py) ──┐
  └─ AI Analyzer (ai_analyzer.py) ──┼──> Report Writer (report.py)
       └─ OpenAI/Anthropic API ────┘
```

- **Regex mode (default)**: Fast, deterministic pattern matching against 8 hardcoded rules. Suitable for reproducible baseline and offline analysis.
- **AI mode**: Cloud LLM-based detection with structured JSON response parsing. Suitable for nuanced patterns and unknown issue types.
- **Output**: Both modes emit compatible `Finding` and `AnalysisResult` objects, so text/JSON/HTML rendering is consistent.

## Limitations

- **AI mode**: May produce false positives or miss subtle issues; non-deterministic output; requires valid API credentials and network.
- **Log size**: Large logs (>40KB) are truncated before sending to providers; only first 40,000 characters are analyzed in AI mode.
- **Regex mode**: Limited to 8 predefined rule patterns; cannot detect novel issue types.
- **Accuracy**: No learning or feedback loop; both modes should be validated against known test logs before production use.

## Security and Privacy

**Important**: In AI mode, log contents are sent to cloud AI providers (OpenAI/Anthropic). If your logs contain:
- Database credentials, API keys, or tokens
- Private IP addresses or internal hostnames
- Proprietary code or build outputs

**Recommendation**: Redact sensitive data before analysis in AI mode, or use regex mode (offline) for sensitive logs.

- API keys are read from environment variables and never logged.
- Logs are not cached or retained by the tool, but may be subject to provider data retention policies (check their terms).
- Use `--ai-api-key` flag to override env var lookup if needed (use with caution; prefer env vars in CI/CD).

## Error Handling and Troubleshooting

### Missing API key
```bash
$ python -m cicd_log_analyzer.cli log.txt --mode ai --ai-provider openai
AI ERROR: Missing API key for provider 'openai'
exit code: 1
```
**Fix**: Set `OPENAI_API_KEY` environment variable or use `--ai-api-key` flag.

### Provider timeout or connection error
```bash
$ python -m cicd_log_analyzer.cli log.txt --mode ai --ai-timeout 5
AI ERROR: AI provider connection failed: ...
exit code: 1
```
**Fix**: Increase timeout with `--ai-timeout` (seconds), check network/VPN, or use regex mode.

### Malformed AI response
```bash
AI ERROR: AI response is not valid JSON
exit code: 1
```
**Fix**: Likely a provider API issue or network interruption; try again or switch providers.

### Exit codes
- `0`: Success (no high-severity findings, or findings detected).
- `1`: Runtime error (file not found, missing API key, provider failure, malformed response).
- `2`: Success with high-severity findings found (if `--fail-on-high` is set).

## Accuracy and Validation

### Regex mode
- Deterministic: same log always produces same findings.
- Fast: suitable for CI/CD gate checks and offline analysis.
- Coverage: detects only predefined patterns (proxy, DNS, disk, auth, docker, timeout, tests, build errors).

### AI mode
- Flexible: can detect novel patterns and provide contextual explanations.
- Non-deterministic: same log may produce slightly different findings across requests due to LLM sampling.
- Validation: always test AI findings against a known set of representative logs before using in production.

### Comparing modes
To validate AI accuracy, run both modes on a sample log and inspect the difference:
```bash
# Regex baseline
python -m cicd_log_analyzer.cli sample_logs/jenkins_failed.log --mode regex --format json > regex_output.json

# AI analysis (after setting OPENAI_API_KEY)
python -m cicd_log_analyzer.cli sample_logs/jenkins_failed.log --mode ai --format json > ai_output.json

# Compare findings
diff regex_output.json ai_output.json
```

## Example output

The CLI prints a summary and actionable recommendations. The HTML report can be opened in a browser and attached as evidence in the assignment document.

