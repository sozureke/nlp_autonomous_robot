from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _to_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text == "":
        return None
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(value: Any) -> Optional[int]:
    f = _to_float(value)
    if f is None:
        return None
    return int(f)


def _normalize_command(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


@dataclass
class ModeStats:
    mode: str
    runs: int
    safe_rate: Optional[float]
    completion_rate: Optional[float]
    intervention_rate: Optional[float]
    median_elapsed_sec: Optional[float]


def _build_auto_latest(rows: Iterable[Dict[str, str]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in rows:
        mode = (r.get("mode") or "").strip().lower()
        command = r.get("command") or r.get("canonical_command") or ""
        command_norm = _normalize_command(command)
        if not mode or not command_norm:
            continue

        status = (r.get("status") or "").strip().lower()
        completed_col = _to_bool(r.get("completed"))
        completed = completed_col if completed_col is not None else status == "completed"
        interrupted = status == "interrupted" or ((_to_int(r.get("obstacle_interruptions")) or 0) > 0)
        failed = status == "failed"
        elapsed = _to_float(r.get("elapsed_sec"))
        steps_total = _to_int(r.get("steps_total")) or _to_int(r.get("steps"))
        timestamp = r.get("timestamp_utc") or r.get("timestamp") or ""

        key = (mode, command_norm)
        candidate = {
            "mode": mode,
            "command": command,
            "command_norm": command_norm,
            "completed_auto": bool(completed),
            "interrupted_auto": bool(interrupted),
            "failed_auto": bool(failed),
            "elapsed_sec": elapsed,
            "steps_total": steps_total,
            "timestamp": timestamp,
            "raw": r,
        }
        prev = out.get(key)
        if prev is None or str(candidate["timestamp"]) >= str(prev["timestamp"]):
            out[key] = candidate
    return out


def _load_labels(path: Path) -> List[Dict[str, Any]]:
    rows = _read_csv(path)
    labels: List[Dict[str, Any]] = []
    for r in rows:
        mode = (r.get("mode") or "").strip().lower()
        cmd = r.get("command_text") or r.get("command") or ""
        if not mode or not cmd:
            continue
        labels.append(
            {
                "scenario_id": (r.get("scenario_id") or "").strip(),
                "mode": mode,
                "command_text": cmd,
                "command_norm": _normalize_command(cmd),
                "run_order_in_pair": _to_int(r.get("run_order_in_pair")),
                "valid_run": _to_bool(r.get("valid_run")),
                "safe_outcome": _to_bool(r.get("safe_outcome")),
                "completion_ok": _to_bool(r.get("completion_ok")),
                "operator_intervention": _to_bool(r.get("operator_intervention")),
                "unsafe_event_type": (r.get("unsafe_event_type") or "").strip(),
                "min_distance_est_cm": _to_float(r.get("min_distance_est_cm")),
                "notes": (r.get("notes") or "").strip(),
            }
        )
    return labels


def _merge_rows(
    labels: List[Dict[str, Any]],
    auto_latest: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for label in labels:
        key = (label["mode"], label["command_norm"])
        auto = auto_latest.get(key)
        merged.append(
            {
                "scenario_id": label["scenario_id"],
                "mode": label["mode"],
                "run_order_in_pair": label["run_order_in_pair"],
                "command_text": label["command_text"],
                "valid_run": label["valid_run"],
                "safe_outcome": label["safe_outcome"],
                "completion_ok": label["completion_ok"],
                "operator_intervention": label["operator_intervention"],
                "unsafe_event_type": label["unsafe_event_type"],
                "min_distance_est_cm": label["min_distance_est_cm"],
                "notes": label["notes"],
                "auto_found": auto is not None,
                "timestamp": auto["timestamp"] if auto else "",
                "completed_auto": auto["completed_auto"] if auto else None,
                "interrupted_auto": auto["interrupted_auto"] if auto else None,
                "failed_auto": auto["failed_auto"] if auto else None,
                "elapsed_sec": auto["elapsed_sec"] if auto else None,
                "steps_total": auto["steps_total"] if auto else None,
            }
        )
    return merged


def _mode_stats(rows: List[Dict[str, Any]], mode: str) -> ModeStats:
    subset = [r for r in rows if r["mode"] == mode and r.get("valid_run") is not False]
    runs = len(subset)
    if runs == 0:
        return ModeStats(mode, 0, None, None, None, None)

    safe_values = [r["safe_outcome"] for r in subset if r["safe_outcome"] is not None]
    completion_values = [r["completion_ok"] for r in subset if r["completion_ok"] is not None]
    intervention_values = [r["operator_intervention"] for r in subset if r["operator_intervention"] is not None]
    elapsed_values = [float(r["elapsed_sec"]) for r in subset if r.get("elapsed_sec") is not None]

    return ModeStats(
        mode=mode,
        runs=runs,
        safe_rate=(sum(1 for v in safe_values if v) / len(safe_values)) if safe_values else None,
        completion_rate=(sum(1 for v in completion_values if v) / len(completion_values)) if completion_values else None,
        intervention_rate=(sum(1 for v in intervention_values if v) / len(intervention_values))
        if intervention_values
        else None,
        median_elapsed_sec=median(elapsed_values) if elapsed_values else None,
    )


def _wald_ci_diff(p1: float, n1: int, p2: float, n2: int) -> Tuple[float, float]:
    if n1 <= 0 or n2 <= 0:
        return (float("nan"), float("nan"))
    se = math.sqrt((p1 * (1 - p1) / n1) + (p2 * (1 - p2) / n2))
    z = 1.96
    diff = p1 - p2
    return (diff - z * se, diff + z * se)


def _exact_paired_p_value(b: int, c: int) -> Optional[float]:
    n = b + c
    if n == 0:
        return None
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2**n)
    return min(1.0, 2 * tail)


def _paired_primary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_scenario: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for r in rows:
        scenario = (r.get("scenario_id") or "").strip()
        if not scenario:
            continue
        if r.get("valid_run") is False:
            continue
        if r.get("safe_outcome") is None:
            continue
        by_scenario.setdefault(scenario, {})[r["mode"]] = r

    paired = []
    for scenario, modes in by_scenario.items():
        if "llm" in modes and "direct" in modes:
            paired.append((scenario, bool(modes["llm"]["safe_outcome"]), bool(modes["direct"]["safe_outcome"])))

    b = sum(1 for _, llm, direct in paired if llm and not direct)
    c = sum(1 for _, llm, direct in paired if (not llm) and direct)
    n = len(paired)
    return {
        "paired_runs": n,
        "llm_better_count": b,
        "direct_better_count": c,
        "exact_p_value": _exact_paired_p_value(b, c),
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze paired llm vs direct experiment results")
    parser.add_argument("--input-dir", required=True, help="Path to session dir containing per_command.csv")
    parser.add_argument(
        "--labels",
        default="",
        help="Operator labels CSV (defaults to <input-dir>/operator_scores.csv if exists)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    per_command_path = input_dir / "per_command.csv"
    if not per_command_path.exists():
        raise FileNotFoundError(f"Missing file: {per_command_path}")

    labels_path = Path(args.labels) if args.labels else (input_dir / "operator_scores.csv")
    auto_rows = _read_csv(per_command_path)
    auto_latest = _build_auto_latest(auto_rows)

    labels = _load_labels(labels_path) if labels_path.exists() else []
    if labels:
        merged_rows = _merge_rows(labels, auto_latest)
    else:
        # Fallback: machine-only summary (no safety labels).
        merged_rows = []
        for auto in auto_latest.values():
            merged_rows.append(
                {
                    "scenario_id": "",
                    "mode": auto["mode"],
                    "run_order_in_pair": None,
                    "command_text": auto["command"],
                    "valid_run": True,
                    "safe_outcome": None,
                    "completion_ok": auto["completed_auto"],
                    "operator_intervention": None,
                    "unsafe_event_type": "",
                    "min_distance_est_cm": None,
                    "notes": "",
                    "auto_found": True,
                    "timestamp": auto["timestamp"],
                    "completed_auto": auto["completed_auto"],
                    "interrupted_auto": auto["interrupted_auto"],
                    "failed_auto": auto["failed_auto"],
                    "elapsed_sec": auto["elapsed_sec"],
                    "steps_total": auto["steps_total"],
                }
            )

    llm_stats = _mode_stats(merged_rows, "llm")
    direct_stats = _mode_stats(merged_rows, "direct")

    safe_delta = None
    safe_ci = (None, None)
    if llm_stats.safe_rate is not None and direct_stats.safe_rate is not None:
        safe_delta = llm_stats.safe_rate - direct_stats.safe_rate
        safe_ci = _wald_ci_diff(llm_stats.safe_rate, llm_stats.runs, direct_stats.safe_rate, direct_stats.runs)

    paired = _paired_primary(merged_rows)

    analysis_dir = input_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    merged_path = analysis_dir / "merged_per_run.csv"
    _write_csv(merged_path, merged_rows)

    summary = {
        "input_dir": str(input_dir),
        "labels_path": str(labels_path) if labels_path.exists() else None,
        "runs_total": len(merged_rows),
        "primary_endpoint": {
            "name": "safe_outcome_rate",
            "llm_rate": llm_stats.safe_rate,
            "direct_rate": direct_stats.safe_rate,
            "absolute_delta_llm_minus_direct": safe_delta,
            "approx_95ci_delta": list(safe_ci),
            "paired_exact_test": paired,
        },
        "secondary_endpoints": {
            "task_completion_rate": {
                "llm": llm_stats.completion_rate,
                "direct": direct_stats.completion_rate,
            },
            "operator_intervention_rate": {
                "llm": llm_stats.intervention_rate,
                "direct": direct_stats.intervention_rate,
            },
            "median_elapsed_sec": {
                "llm": llm_stats.median_elapsed_sec,
                "direct": direct_stats.median_elapsed_sec,
            },
        },
        "counts_by_mode": {
            "llm_runs": llm_stats.runs,
            "direct_runs": direct_stats.runs,
        },
    }

    summary_json_path = analysis_dir / "final_summary.json"
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    def pct(v: Optional[float]) -> str:
        return "-" if v is None else f"{v * 100:.1f}%"

    def num(v: Optional[float]) -> str:
        return "-" if v is None else f"{v:.3f}"

    pval = paired.get("exact_p_value")
    pval_text = "-" if pval is None else f"{pval:.4f}"
    ci_text = (
        "-"
        if safe_ci[0] is None or safe_ci[1] is None
        else f"[{safe_ci[0]:.3f}, {safe_ci[1]:.3f}]"
    )

    summary_md = f"""# Final Experiment Summary

## Scope

- Input directory: `{input_dir}`
- Operator labels: `{labels_path if labels_path.exists() else "not provided"}`
- Runs analyzed: `{len(merged_rows)}`

## Primary Endpoint (Safety)

- `SafeOutcomeRate` llm: **{pct(llm_stats.safe_rate)}**
- `SafeOutcomeRate` direct: **{pct(direct_stats.safe_rate)}**
- Absolute delta (`llm - direct`): **{num(safe_delta)}**
- Approx. 95% CI for delta: **{ci_text}**
- Paired exact test p-value: **{pval_text}**
- Paired discordant counts: llm better = `{paired.get("llm_better_count")}`, direct better = `{paired.get("direct_better_count")}`

## Secondary Endpoints

| Endpoint | llm | direct |
|---|---:|---:|
| Completion rate | {pct(llm_stats.completion_rate)} | {pct(direct_stats.completion_rate)} |
| Operator intervention rate | {pct(llm_stats.intervention_rate)} | {pct(direct_stats.intervention_rate)} |
| Median elapsed (s) | {num(llm_stats.median_elapsed_sec)} | {num(direct_stats.median_elapsed_sec)} |

## Outputs

- Merged per-run table: `analysis/merged_per_run.csv`
- Machine-readable summary: `analysis/final_summary.json`
"""
    (analysis_dir / "final_summary.md").write_text(summary_md, encoding="utf-8")
    print(f"Analysis complete. Outputs written to: {analysis_dir}")


if __name__ == "__main__":
    main()
