"""Remove host Docker socket bind mounts from NYU CTF Bench challenge files.

Audit (2026-09-21): 63 of the 200 challenges in the test split bind-mount
`/var/run/docker.sock` into the challenge container, e.g.

    services:
      game-server:
        image: llmctf/2021q-cry-bits:latest
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock

A container holding the host's Docker socket can create further containers
with arbitrary mounts, which is equivalent to root on the host. That matters
here specifically because the whole point of the benchmark is to have an LLM
agent find and exploit a bug in those services: a successful exploit yields
code execution *inside* a container that can reach the host. Trajectory logs
from the 2026-09-18/21 runs show no agent ever did (the solves only read the
flag), but the path should not be open at all.

Upstream ships the mounts because the original CSAW challenges used
docker-in-docker to spawn per-player instances; the benchmark runs one
instance per challenge, so nothing here needs the socket. Removing it is a
local change to the downloaded dataset, and re-downloading restores it --
which is why the eval drivers call `strip_all()` at startup rather than
relying on this having been run once by hand.
"""
import re
import sys
from pathlib import Path

_SOCK_LINE = re.compile(r'^\s*-\s*["\']?/var/run/docker\.sock\s*:')
_VOLUMES_KEY = re.compile(r'^(\s*)volumes:\s*$')


def _dataset_basedir() -> Path:
    from nyuctf.dataset import CTFDataset
    return Path(CTFDataset(split="test").basedir)


def strip_file(path: Path, dry_run: bool = False) -> int:
    """Drop socket mounts from one compose file. Returns lines removed."""
    text = path.read_text()
    lines = text.splitlines(keepends=True)

    kept = [ln for ln in lines if not _SOCK_LINE.match(ln)]
    removed = len(lines) - len(kept)
    if not removed:
        return 0

    # A `volumes:` key whose only entry was the socket is now empty, which
    # docker compose rejects ("services.x.volumes must be a list"), so drop
    # the key too.
    out = []
    i = 0
    while i < len(kept):
        m = _VOLUMES_KEY.match(kept[i])
        if m:
            indent = len(m.group(1))
            j = i + 1
            while j < len(kept) and not kept[j].strip():
                j += 1
            nxt = kept[j] if j < len(kept) else ""
            nxt_indent = len(nxt) - len(nxt.lstrip())
            if not nxt.strip() or nxt_indent <= indent or not nxt.lstrip().startswith("-"):
                i += 1
                continue
        out.append(kept[i])
        i += 1

    if not dry_run:
        path.write_text("".join(out))
    return removed


def strip_all(basedir=None, dry_run: bool = False, quiet: bool = False) -> int:
    """Strip every challenge compose file under the dataset. Returns the
    number of files changed. Safe to call repeatedly -- it is a no-op once
    the mounts are gone."""
    base = Path(basedir) if basedir else _dataset_basedir()
    changed = 0
    for compose in sorted(base.rglob("docker-compose.yml")):
        if strip_file(compose, dry_run=dry_run):
            changed += 1
            if not quiet:
                rel = compose.relative_to(base)
                print(f"[docker.sock] {'would strip' if dry_run else 'stripped'} {rel}", flush=True)
    if changed and not quiet:
        print(f"[docker.sock] {changed} challenge compose file(s) "
              f"{'would be' if dry_run else ''} cleaned", flush=True)
    return changed


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    n = strip_all(dry_run=dry)
    if not n:
        print("[docker.sock] no host socket mounts found -- nothing to do")
