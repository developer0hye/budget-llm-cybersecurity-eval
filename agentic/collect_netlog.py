#!/usr/bin/env python3
"""Pull the node's Hubble flow export into the repo and summarise it.

Usage:
    python3 agentic/collect_netlog.py                 # copy + summarise
    python3 agentic/collect_netlog.py --summary-only

Cilium's Hubble flow exporter (enabled with hubble-export-file-path) writes
every network flow of every sandbox pod to a file on the minikube node,
including each DNS query and the policy verdict (FORWARDED / DROPPED). This
is an independent, network-layer record of what agents reached, separate
from the .eval trajectory: the trajectory shows what the agent tried, this
shows what the network actually allowed.

This copies the node file into agentic/netlog/events.log (plus rotated
backups) and writes agentic/netlog/dns_verdicts.md: per destination domain,
how many DNS queries from sandbox pods were forwarded vs dropped. Any
code-host row with a FORWARDED verdict is a policy breach and is called out.
Per-sample attribution is via the .eval trajectory (agentic/audit_egress.py);
the pod name here (agent-env-<release>-...) ties a flow to a sandbox but not
directly to a challenge.
"""

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agentic"))
sys.path.insert(0, str(ROOT))
from run_cybench import BLOCKED_DOMAINS  # noqa: E402
import gzip  # noqa: E402

# Code hosts and mirrors/proxies of them. BLOCKED_DOMAINS is what the policy
# removed from the allowlist; this wider set is what the audit checks, so a
# lookup of a mirror or proxy is flagged even though the policy never listed it.
CODE_HOST_SUFFIXES = sorted(set(BLOCKED_DOMAINS) | {
    "githubusercontent.com", "github.io", "gitlab.com", "ghproxy.com",
    "githack.com", "fastgit.org", "grep.app", "sourcegraph.com",
})
DNS_EXTRACT = "sandbox_dns.jsonl.gz"

NETLOG = ROOT / "agentic" / "netlog"
NODE_DIR = "/var/run/cilium/hubble"


def cilium_pod() -> str:
    out = subprocess.run(
        ["kubectl", "-n", "kube-system", "get", "pods", "-l", "k8s-app=cilium",
         "-o", "jsonpath={.items[0].metadata.name}"], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def collect() -> None:
    NETLOG.mkdir(parents=True, exist_ok=True)
    pod = cilium_pod()
    files = subprocess.run(
        ["kubectl", "-n", "kube-system", "exec", pod, "-c", "cilium-agent", "--",
         "sh", "-c", f"ls {NODE_DIR}"], capture_output=True, text=True, check=True).stdout.split()
    for fn in files:
        data = subprocess.run(
            ["kubectl", "-n", "kube-system", "exec", pod, "-c", "cilium-agent", "--",
             "cat", f"{NODE_DIR}/{fn}"], capture_output=True, text=True, check=True).stdout
        (NETLOG / fn).write_text(data)
    print(f"copied {files} from node pod {pod} into {NETLOG}")


def extract_dns() -> None:
    """Reduce the raw export (every flow, GBs) to sandbox DNS lookups only.

    Reads every exported file, including rotated ones (events-<timestamp>.log),
    and writes one line per sandbox-pod DNS query to sandbox_dns.jsonl.gz.
    The raw files are gitignored; this extract is what gets committed.
    """
    kept = 0
    with gzip.open(NETLOG / DNS_EXTRACT, "wt") as out:
        for f in sorted(NETLOG.glob("events*.log")):
            with f.open(errors="replace") as fh:
                for line in fh:
                    if '"dns"' not in line:
                        continue
                    try:
                        flow = json.loads(line).get("flow", {})
                    except json.JSONDecodeError:
                        continue
                    src = flow.get("source", {})
                    q = ((flow.get("l7") or {}).get("dns") or {}).get("query")
                    if not q or not src.get("namespace", "").startswith("default"):
                        continue
                    out.write(json.dumps({"time": flow.get("time"), "pod": src.get("pod_name"),
                                          "query": q.rstrip("."), "verdict": flow.get("verdict")}) + "\n")
                    kept += 1
    print(f"extracted {kept} sandbox DNS records -> {NETLOG / DNS_EXTRACT}")


def summarise() -> None:
    counts: dict[tuple[str, str], int] = collections.Counter()
    with gzip.open(NETLOG / DNS_EXTRACT, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            counts[(r["query"], r["verdict"])] += 1
    domains = sorted({d for d, _ in counts})

    def is_code_host(d: str) -> bool:
        d = d.lower()
        return any(d == b or d.endswith("." + b) for b in CODE_HOST_SUFFIXES)

    breaches = [d for d in domains if is_code_host(d) and counts.get((d, "FORWARDED"), 0)]
    lines = ["# Sandbox DNS verdicts (Cilium Hubble flow export)", "",
             "Per destination queried by a sandbox pod: forwarded vs dropped DNS lookups.",
             "A code host that was ever FORWARDED is a policy breach.", ""]
    if breaches:
        lines.append(f"**POLICY BREACH: code host(s) forwarded: {', '.join(breaches)}**")
    else:
        lines.append("**No code host was forwarded.** Every code-host lookup was dropped.")
    lines += ["", "| domain | forwarded | dropped | code host |", "|---|---|---|---|"]
    for d in domains:
        lines.append(f"| {d} | {counts.get((d, 'FORWARDED'), 0)} | {counts.get((d, 'DROPPED'), 0)} | "
                     f"{'yes' if is_code_host(d) else ''} |")
    (NETLOG / "dns_verdicts.md").write_text("\n".join(lines) + "\n")
    print(f"{len(domains)} domains, breaches: {breaches or 'none'} -> {NETLOG}/dns_verdicts.md")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summary-only", action="store_true")
    args = p.parse_args()
    if not args.summary_only:
        collect()
        extract_dns()
    summarise()


if __name__ == "__main__":
    main()
