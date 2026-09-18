#!/usr/bin/env python3
"""Convert an nyuctf_agents *baseline* trajectory log into the shape
CTFJudge expects (which is tuned for D-CIPHER's planner/executor format).

Baseline trajectory (OpenAI chat-completions shape):
    {
      "solved": bool, "cost": float, "finish_reason": str,
      "runtime": {"total": float, ...},
      "messages": [[timestamp, {"role": ..., "content": ..., "tool_calls": [...]}], ...]
    }

CTFJudge/D-CIPHER trajectory (confirmed against CTFJudge/trajs/2023q-web-smug_dino.json):
    {
      "success": bool, "exit_reason": str, "time_taken": float, "total_cost": float,
      "planner": [{"role": "MessageRole.ASSISTANT", "index": 1, "content": ...,
                    "tool_call": {"name": ..., "parsed_args": {...}}}, ...],
      "executors": []
    }

Baseline has no separate planner/executor split, so the whole conversation
goes into "planner" and "executors" is left empty. A single baseline
assistant turn can carry multiple tool_calls (OpenAI parallel tool calling);
each is split into its own synthetic MessageRole.ASSISTANT entry so
CTFJudge's one-tool-call-per-entry formatter (see _format_tool_usage in
trajectory_summary_agent.py) doesn't silently drop the extras.

Usage:
    python3 adapt_baseline_trajectory.py <baseline_log.json> <output.json>
"""

import argparse
import json
import re
import sys

# r2/gdb/etc. emit ANSI color codes in their stdout; strip them so the judge
# LLM reads plain text instead of ~2-3x its content in escape sequences.
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(value):
    if isinstance(value, str):
        return ANSI.sub("", value)
    return value


def convert(raw: dict) -> dict:
    planner = []
    idx = 0
    for _timestamp, msg in raw.get("messages", []):
        role = msg.get("role")

        if role in ("system", "user"):
            planner.append({
                "role": f"MessageRole.{role.upper()}",
                "index": idx,
                "content": msg.get("content"),
            })
            idx += 1

        elif role == "assistant":
            tool_calls = msg.get("tool_calls") or []
            content = msg.get("content")
            if content is None:
                # Baseline puts the model's visible reasoning here when
                # content is null (common when the turn is pure tool calls).
                content = msg.get("reasoning") or ""
            if not tool_calls:
                planner.append({
                    "role": "MessageRole.ASSISTANT",
                    "index": idx,
                    "content": content,
                })
                idx += 1
            else:
                for i, tc in enumerate(tool_calls):
                    fn = tc.get("function", {})
                    try:
                        parsed_args = json.loads(fn.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        parsed_args = {"_raw_arguments": fn.get("arguments")}
                    planner.append({
                        "role": "MessageRole.ASSISTANT",
                        "index": idx,
                        # Only the first synthetic entry for this turn carries
                        # the reasoning text; repeating it on every split
                        # entry would render the same content N times in a
                        # row in CTFJudge's formatted log.
                        "content": content if i == 0 else "",
                        "tool_call": {
                            "name": fn.get("name", "unknown"),
                            "parsed_args": parsed_args,
                        },
                    })
                    idx += 1

        elif role == "tool":
            try:
                result = json.loads(msg.get("content") or "{}")
            except json.JSONDecodeError:
                result = {"stdout": msg.get("content"), "stderr": "", "returncode": None}
            if isinstance(result, dict):
                result = {k: _strip_ansi(v) for k, v in result.items()}
            planner.append({
                "role": "MessageRole.OBSERVATION",
                "index": idx,
                "content": None,
                "tool_result": {
                    "name": msg.get("name", "unknown"),
                    "result": result,
                },
            })
            idx += 1
        # any other role (e.g. hint) is dropped -- CTFJudge has no slot for it

    model = (raw.get("args") or {}).get("model", "unknown")
    return {
        "success": raw.get("solved", False),
        "exit_reason": raw.get("finish_reason", "unknown"),
        "time_taken": (raw.get("runtime") or {}).get("total", 0),
        "total_cost": raw.get("cost", 0),
        "autoprompter_model": model,
        "planner_model": model,
        "executor_model": model,
        "planner": planner,
        "executors": [],
        "debug_log": raw.get("debug_log", []),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to a baseline trajectory JSON (from run_baseline.py)")
    parser.add_argument("output", help="Path to write the CTFJudge-shaped trajectory JSON")
    args = parser.parse_args()

    with open(args.input) as f:
        raw = json.load(f)
    adapted = convert(raw)
    with open(args.output, "w") as f:
        json.dump(adapted, f, indent=2)
    print(f"Wrote {len(adapted['planner'])} planner entries to {args.output}")


if __name__ == "__main__":
    main()
