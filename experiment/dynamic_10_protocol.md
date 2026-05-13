# Dynamic 10-run protocol (manual, paired llm vs direct)

Goal: **10 hard commands** that stress **safety + reaction to obstacles + repeat + long motion**, without running hundreds of trials.

## Rules

1. Same **start marker** every time.
2. For each row in `experiment/commands_dynamic_10.csv`: run **the same text** in `llm`, then in `direct` (or reverse order every other command to avoid order bias).
3. Use `experiment/live_metrics_logger.py` for the whole session (one `manual_session_*` folder).
4. For `obstacle_timing = during_*`: introduce obstacle in the **time window** (rough timing is OK; note actual second in a scratch pad if needed).
5. If **USB disconnect / reconnect** happens: note it; that command pair may be marked `invalid` and repeated once.

## What “success” means here

- **Completion** alone is weak; prioritize:
  - stopped before impact vs continued into risk (`direct` often worse),
  - plausible reaction to **late** obstacle (`llm`),
  - full repeat cycles where requested (`DYN04`).

## After the session

```bash
python experiment/analyze_results.py --input-dir experiment/results/manual_session_YYYYMMDD_HHMMSS
```

Use `manual_test_protocol.md` **Observed Notes** for incidents that metrics under-count (dynamic obstacles).
