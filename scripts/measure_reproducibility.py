#!/usr/bin/env python3
"""
Reproducibility Measurement Tool

Runs the knowledge gap assessor multiple times on the same input and measures
consistency of results. This prevents "it worked by chance" situations and
provides a quantitative measure of analysis reliability.

Usage:
    measure_reproducibility.py --text "task description" [--runs N] [--json]
    measure_reproducibility.py <task-file> [--runs N] [--json]

Output:
    Success rate, consistency metrics, and variance analysis for each
    analysis dimension (domains, ambiguity, red alerts, confidence).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

# Import the assessor
sys.path.insert(0, str(Path(__file__).resolve().parent))
from assess_knowledge_gaps import (
    DEFAULT_LANGUAGE,
    REPORT_SEPARATOR_WIDTH,
    AnalysisResult,
    analyze_text,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_RUNS: int = 10
MIN_RUNS: int = 2
MAX_RUNS: int = 1000


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DimensionReport(BaseModel):
    """Consistency report for a single analysis dimension."""
    dimension: str
    total_runs: int
    unique_outcomes: int
    most_common_outcome: str
    most_common_count: int
    consistency_rate: float = Field(
        description="Fraction of runs matching the most common outcome (0.0–1.0)"
    )
    all_outcomes: dict[str, int] = Field(
        description="Counter of all observed outcomes"
    )


class ReproducibilityReport(BaseModel):
    """Full reproducibility report across all dimensions."""
    input_text_preview: str = Field(
        description="First 80 chars of the input text"
    )
    total_runs: int
    overall_consistency: float = Field(
        description="Mean consistency rate across all dimensions"
    )
    dimensions: list[DimensionReport]
    fully_deterministic: bool = Field(
        description="True if all runs produced identical results"
    )


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def extract_dimension_values(
    results: list[AnalysisResult],
) -> dict[str, list[str]]:
    """Extract comparable string values for each analysis dimension."""
    dimensions: dict[str, list[str]] = {
        "confidence": [],
        "domains": [],
        "version_sensitive": [],
        "ambiguity_types": [],
        "red_alert_count": [],
        "proper_noun_count": [],
        "search_suggestion_count": [],
    }

    for r in results:
        dimensions["confidence"].append(r.confidence_assessment.value)
        dimensions["domains"].append(",".join(sorted(r.domains_detected)) or "(none)")
        dimensions["version_sensitive"].append(str(r.version_sensitive))
        dimensions["ambiguity_types"].append(
            ",".join(sorted(f.type.value for f in r.ambiguity_flags)) or "(none)"
        )
        dimensions["red_alert_count"].append(str(len(r.red_alerts)))
        dimensions["proper_noun_count"].append(str(len(r.proper_nouns)))
        dimensions["search_suggestion_count"].append(str(len(r.suggested_searches)))

    return dimensions


def measure_dimension(
    name: str,
    values: list[str],
) -> DimensionReport:
    """Measure consistency for a single dimension."""
    counter = Counter(values)
    most_common_val, most_common_count = counter.most_common(1)[0]

    return DimensionReport(
        dimension=name,
        total_runs=len(values),
        unique_outcomes=len(counter),
        most_common_outcome=most_common_val,
        most_common_count=most_common_count,
        consistency_rate=most_common_count / len(values),
        all_outcomes=dict(counter),
    )


def run_reproducibility_test(
    text: str,
    runs: int = DEFAULT_RUNS,
    lang: str = DEFAULT_LANGUAGE,
) -> ReproducibilityReport:
    """Run the analysis multiple times and measure consistency."""
    results: list[AnalysisResult] = []
    for _ in range(runs):
        results.append(analyze_text(text, lang))

    dimensions_data = extract_dimension_values(results)
    dimension_reports = [
        measure_dimension(name, values)
        for name, values in dimensions_data.items()
    ]

    overall = (
        sum(d.consistency_rate for d in dimension_reports) / len(dimension_reports)
        if dimension_reports
        else 0.0
    )

    fully_deterministic = all(d.consistency_rate == 1.0 for d in dimension_reports)

    return ReproducibilityReport(
        input_text_preview=text[:80],
        total_runs=runs,
        overall_consistency=overall,
        dimensions=dimension_reports,
        fully_deterministic=fully_deterministic,
    )


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

def format_reproducibility_report(report: ReproducibilityReport) -> str:
    """Format the reproducibility report for human reading."""
    sep = "=" * REPORT_SEPARATOR_WIDTH
    lines: list[str] = []

    lines.append(sep)
    lines.append("REPRODUCIBILITY MEASUREMENT REPORT")
    lines.append(sep)

    lines.append(f"\nInput: \"{report.input_text_preview}...\"")
    lines.append(f"Runs: {report.total_runs}")
    lines.append(f"Overall Consistency: {report.overall_consistency:.1%}")
    lines.append(
        f"Fully Deterministic: {'YES' if report.fully_deterministic else 'NO'}"
    )

    lines.append(f"\n{'Dimension':<28} {'Consistency':>12} {'Unique':>8} {'Most Common'}")
    lines.append("-" * REPORT_SEPARATOR_WIDTH)

    for d in report.dimensions:
        lines.append(
            f"  {d.dimension:<26} {d.consistency_rate:>11.1%} {d.unique_outcomes:>7}   "
            f"{d.most_common_outcome}"
        )

    # Flag any inconsistencies
    inconsistent = [d for d in report.dimensions if d.consistency_rate < 1.0]
    if inconsistent:
        lines.append(f"\nWARNING: {len(inconsistent)} dimension(s) showed variance:")
        for d in inconsistent:
            lines.append(f"  - {d.dimension}: {d.all_outcomes}")

    lines.append(f"\n{sep}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    runs = DEFAULT_RUNS
    json_mode = False
    text = None

    args = sys.argv[1:]
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == "--runs" and i + 1 < len(args):
            runs = max(MIN_RUNS, min(MAX_RUNS, int(args[i + 1])))
            i += 2
            continue

        if arg == "--json":
            json_mode = True
            i += 1
            continue

        if arg == "--text":
            remaining = [a for a in args[i + 1:] if a not in ("--runs", "--json")]
            # Also need to skip the value after --runs
            filtered = []
            j = i + 1
            while j < len(args):
                if args[j] == "--runs" and j + 1 < len(args):
                    runs = max(MIN_RUNS, min(MAX_RUNS, int(args[j + 1])))
                    j += 2
                    continue
                if args[j] == "--json":
                    json_mode = True
                    j += 1
                    continue
                filtered.append(args[j])
                j += 1
            text = " ".join(filtered) if filtered else sys.stdin.read()
            break

        # Assume file path
        file_path = Path(arg)
        if file_path.exists():
            text = file_path.read_text()
        else:
            print(f"Error: File not found: {arg}")
            sys.exit(1)
        i += 1

    if text is None:
        print("Usage:")
        print('  measure_reproducibility.py --text "task description" [--runs N] [--json]')
        print("  measure_reproducibility.py <task-file> [--runs N] [--json]")
        sys.exit(1)

    report = run_reproducibility_test(text, runs=runs)

    if json_mode:
        print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
    else:
        print(format_reproducibility_report(report))


if __name__ == "__main__":
    main()
