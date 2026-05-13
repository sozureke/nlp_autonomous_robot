# Final Experiment Summary

## Dataset Scope

- Source session: `manual_session_20260508_140803`
- Selection rule: latest attempt per target command (`A01..D05`) and mode (`llm`, `direct`).
- Selected runs: `40` (expected 40).
- Missing pairs: `None`.

## Quantitative Results (Selected 20 Commands)

| Mode | Runs | Completion Rate | Avg Time (s) | Safety Violations | Obstacle Interruptions |
|---|---:|---:|---:|---:|---:|
| llm | 20 | 100.0% | 5.89 | 0 | 0 |
| direct | 20 | 100.0% | 5.70 | 0 | 0 |

## Figures

- Completion rate by mode: `analysis/chart_completion_rate.png`
- Average execution time by mode: `analysis/chart_avg_time.png`
- Completion by category (A/B/C/D): `analysis/chart_category_completion.png`

## Interpreted Findings (with operator notes)

- `llm` mode showed safer qualitative behavior in obstacle-sensitive scenarios (e.g., D04 stopped on detected object around second 8).
- In `direct` mode, obstacle non-reaction was observed (B04), consistent with direct no-safety design.
- Mechanical variance (wheel vibration / traction noise) is a known confounder and should be treated as hardware limitation, not pure control logic error.
- Category D should be interpreted from latest re-run attempts only (repeat logic patch applied).

## Important Metric Caveat

- Current numeric fields `safety_violations` and `obstacle_interruptions` may under-report dynamic obstacle events; use operator notes together with metrics for final discussion.