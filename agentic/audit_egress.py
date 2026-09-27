#!/usr/bin/env python3
"""Build a reviewable index of every network access agents attempted.

Usage:
    python3 agentic/audit_egress.py agentic/logs            # writes agentic/audit/
    python3 agentic/audit_egress.py agentic/logs --out agentic/audit

The Inspect .eval logs under agentic/logs/<model>/ are the primary record:
they hold every tool call and its output, in order, for every sample. This
script does not replace them. It indexes them, so a reviewer can find the
calls worth reading and open them at their exact position.

Outputs:
  audit/egress_calls.jsonl  one row per tool call that names a host: model,
                            sample, epoch, event_index (position among the
                            sample's tool events in the .eval), log_file,
                            host, host_class, blocked_hint, command excerpt
  audit/summary.md          per model and host_class counts, plus every row
                            outside the challenge's own services, for review

host_class:
  challenge   the challenge's own services (victim, localhost, IP literals)
  mirror      an allowlisted package mirror (see run_cybench.py)
  code_host   a blocked code host (BLOCKED_DOMAINS) -- always review
  other       any other external host -- review

blocked_hint is True when the call's output shows a resolution or
connection failure. Egress policy is enforced by Cilium, so a blocked row
means the attempt was made and denied. Scoring never reads this file; it is
an audit record only.
"""

import argparse
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agentic"))
sys.path.insert(0, str(ROOT))

from inspect_ai.log import read_eval_log  # noqa: E402
from run_cybench import BLOCKED_DOMAINS, EXTRA_ALLOWED_DOMAINS  # noqa: E402

UPSTREAM_ALLOWED = {
    "pypi.org", "files.pythonhosted.org", "kali.download", "archive.ubuntu.com",
    "security.ubuntu.com", "mirror.vinehost.net", "x0.at",
}
WILDCARD_ALLOWED = (".debian.org", ".kali.org", ".rubygems.org")
HOST_RE = re.compile(r"(?:https?|git|ftp)://([A-Za-z0-9.\-]+)|git@([A-Za-z0-9.\-]+):")
BLOCKED_OUTPUT_RE = re.compile(
    r"(?i)could not resolve|temporary failure resolving|name or service not known|"
    r"failed to connect|connection refused|connection timed out|network is unreachable|"
    r"no address associated|getaddrinfo failed|resolve host"
)


def classify(host: str) -> str:
    h = host.lower().rstrip(".")
    if h in BLOCKED_DOMAINS or any(h.endswith("." + d) for d in BLOCKED_DOMAINS):
        return "code_host"
    if "." not in h or h in ("localhost",) or re.fullmatch(r"[\d.]+", h):
        return "challenge"
    if h in UPSTREAM_ALLOWED or h in EXTRA_ALLOWED_DOMAINS or h.endswith(WILDCARD_ALLOWED):
        return "mirror"
    return "other"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("log_root")
    p.add_argument("--out", default="agentic/audit")
    args = p.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for f in sorted(glob.glob(str(Path(args.log_root) / "**" / "*.eval"), recursive=True)):
        model = Path(f).parent.name
        log = read_eval_log(f)
        for s in log.samples or []:
            tools = [e for e in s.events if e.event == "tool"]
            for i, e in enumerate(tools):
                cmd = json.dumps(e.arguments, ensure_ascii=False)
                hosts = {a or b for a, b in HOST_RE.findall(cmd)}
                if not hosts:
                    continue
                result = str(e.result or "") + (str(e.error.message) if e.error else "")
                for h in sorted(hosts):
                    rows.append({
                        "model": model, "sample": str(s.id), "epoch": s.epoch,
                        "event_index": i, "log_file": str(Path(f).resolve().relative_to(ROOT)),
                        "host": h, "host_class": classify(h),
                        "blocked_hint": bool(BLOCKED_OUTPUT_RE.search(result)),
                        "command_excerpt": cmd[:300],
                    })

    with (out / "egress_calls.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    lines = ["# Egress audit", "", f"Generated from `{args.log_root}` by `agentic/audit_egress.py`.", "",
             "| model | challenge | mirror | code_host | other | code_host/other not blocked |",
             "|---|---|---|---|---|---|"]
    for model in sorted({r["model"] for r in rows}):
        c = Counter(r["host_class"] for r in rows if r["model"] == model)
        open_ = sum(1 for r in rows if r["model"] == model and r["host_class"] in ("code_host", "other")
                    and not r["blocked_hint"])
        lines.append(f"| {model} | {c['challenge']} | {c['mirror']} | {c['code_host']} | {c['other']} | {open_} |")
    lines += ["", "## Rows to review (code_host and other)", "",
              "| model | sample | epoch | event_index | host | class | blocked_hint | log_file |",
              "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["host_class"] in ("code_host", "other"):
            lines.append(f"| {r['model']} | {r['sample']} | {r['epoch']} | {r['event_index']} | {r['host']} | "
                         f"{r['host_class']} | {r['blocked_hint']} | {r['log_file']} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"{len(rows)} host-bearing tool calls -> {out}/egress_calls.jsonl, {out}/summary.md")


if __name__ == "__main__":
    main()
