"""Command-line interface for AI Code Reviewer.

Usage:
    python cli/main.py --path ./examples --style google
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.parser.python_parser import PythonParser
from core.validator.validator import DocstringValidator
from core.reporter.coverage_reporter import CoverageReporter


def main() -> None:
    """Entry point for the CLI tool.

    Parses arguments, runs analysis, and prints a summary report
    to stdout. Exits with code 1 if any PEP 257 issues are found.
    """
    parser = argparse.ArgumentParser(
        description="AI Code Reviewer — analyse Python docstring quality."
    )
    parser.add_argument("--path", required=True, help="Project folder to scan.")
    parser.add_argument(
        "--style",
        default="google",
        choices=["google", "numpy", "rest"],
        help="Docstring style to validate against.",
    )
    parser.add_argument("--json", action="store_true", help="Output report as JSON.")
    args = parser.parse_args()

    if not os.path.isdir(args.path):
        print(f"ERROR: {args.path!r} is not a valid directory.", file=sys.stderr)
        sys.exit(2)

    # Parse
    analyses = PythonParser().parse_directory(args.path)
    reporter = CoverageReporter()
    coverage = reporter.build(analyses)

    # Validate
    validator = DocstringValidator()
    all_issues: dict[str, list] = {}
    for fa in analyses:
        if fa.syntax_error:
            continue
        try:
            with open(fa.file_path, encoding="utf-8") as fh:
                src = fh.read()
            issues = validator.validate_source(src)
            if issues:
                all_issues[fa.file_name] = [
                    {"code": i.code, "function": i.function, "line": i.line, "message": i.message}
                    for i in issues
                ]
        except OSError:
            pass

    if args.json:
        import json
        print(json.dumps({
            "coverage": {
                "total_files": coverage.total_files,
                "total_functions": coverage.total_functions,
                "documented": coverage.documented,
                "coverage_pct": coverage.coverage_pct,
            },
            "pep257_issues": all_issues,
        }, indent=2))
    else:
        print(f"\n{'='*52}")
        print(f"  AI Code Reviewer — {args.path}")
        print(f"{'='*52}")
        print(f"  Files scanned  : {coverage.total_files}")
        print(f"  Functions      : {coverage.total_functions}")
        print(f"  Documented     : {coverage.documented}")
        print(f"  Coverage       : {coverage.coverage_pct}%")
        total_pep = sum(len(v) for v in all_issues.values())
        print(f"  PEP 257 issues : {total_pep}")
        print(f"{'='*52}\n")

        if all_issues:
            for fname, issues in all_issues.items():
                print(f"  {fname}")
                for iss in issues:
                    print(f"    [{iss['code']}] line {iss['line']} — {iss['function']}: {iss['message']}")
            sys.exit(1)


if __name__ == "__main__":
    main()
