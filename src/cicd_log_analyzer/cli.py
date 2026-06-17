from __future__ import annotations

import argparse
import sys

from .ai_analyzer import AIAnalysisError, AIConfig, analyze_file_with_ai
from .analyzer import analyze_file
from .report import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze CI/CD logs and generate actionable reports.")
    parser.add_argument("log_file", help="Path to Jenkins/Bamboo/GitHub Actions log file")
    parser.add_argument("--format", choices=["text", "json", "html"], default="text", help="Output format")
    parser.add_argument("--output", help="Optional output file path")
    parser.add_argument("--mode", choices=["regex", "ai"], default="regex", help="Analysis mode")
    parser.add_argument("--ai-provider", choices=["openai", "anthropic"], default="openai", help="AI provider")
    parser.add_argument("--ai-model", default="gpt-4.1-mini", help="AI model name")
    parser.add_argument("--ai-api-key", help="Optional API key; defaults to provider environment variable")
    parser.add_argument("--ai-timeout", type=int, default=30, help="AI request timeout in seconds")
    parser.add_argument("--ai-max-input-chars", type=int, default=40000, help="Max characters sent to AI provider")
    parser.add_argument("--fail-on-high", action="store_true", help="Return exit code 2 when high severity findings exist")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.mode == "ai":
            ai_config = AIConfig(
                provider=args.ai_provider,
                model=args.ai_model,
                api_key=args.ai_api_key,
                timeout_seconds=max(1, args.ai_timeout),
                max_input_chars=max(5000, args.ai_max_input_chars),
            )
            result = analyze_file_with_ai(args.log_file, ai_config)
        else:
            result = analyze_file(args.log_file)

        content = write_report(result, args.format, args.output)
        if not args.output or args.format == "text":
            print(content, end="")
        elif args.output:
            print(f"Report written to {args.output}")

        if args.fail_on_high and result.highest_severity == "high":
            return 2
        return 0
    except AIAnalysisError as exc:
        print(f"AI ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - CLI safeguard
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
