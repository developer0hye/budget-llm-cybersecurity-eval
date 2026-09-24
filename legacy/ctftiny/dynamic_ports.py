"""Dynamic host-port conflict resolution, shared by the eval driver scripts.

Background: an audit (2026-09-20) found ~24 of the 200 NYU CTF Bench
challenges hardcode host port 5000, which macOS's AirPlay Receiver occupies
by default -- the single largest cause of docker-compose failures across
every run in this project. The original fix remapped those 24 challenges'
docker-compose.yml files to host port 15000 by hand, one time.

That fix generalizes cleanly: the agent never touches a challenge's
host-published port at all -- it reaches challenge containers entirely
through the internal `ctfnet` Docker network's embedded DNS alias (verified
empirically by remapping 2021f-cry-interoperable from host port 5000 to
15000 and confirming a container on ctfnet could still resolve and connect
to it by alias:container-port, unaffected). So *any* host port conflict --
AirPlay, a leftover container from a crashed job, some unrelated local
service, a different machine's port assignments entirely -- is never a
reason to fail a job; it's purely a side effect of docker-compose's host
bind failing loudly for a value nobody actually needs. This module checks
each challenge's declared host ports right before a job runs and, if one is
occupied, rewrites that challenge's docker-compose.yml to a fresh
OS-assigned free port. The rewrite is permanent (safe, since the host port
is cosmetic) so a conflict is fixed once, for every future run of that
challenge on that machine -- not just the current job.
"""
import re
import socket
from pathlib import Path

_dataset = None


def _get_dataset():
    global _dataset
    if _dataset is None:
        from nyuctf.dataset import CTFDataset
        _dataset = CTFDataset(split="test")
    return _dataset


def _port_is_free(port) -> bool:
    """Directly test bindability rather than connect-probing for a listener.
    A connect probe answers "is something accepting connections here", which
    is the wrong question (a port can be bound but not yet accept()-ing, and
    -- found empirically while testing this module -- repeated connect
    probes against a small listen() backlog give inconsistent answers within
    the same process). A bind probe answers the actual question that
    matters: can docker-compose bind this host port right now.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", int(port)))
            return True
        except OSError:
            return False


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def ensure_dynamic_ports(challenge: str, ports: list) -> list:
    """Return `ports` unchanged if every one is free right now. Otherwise,
    for each occupied port, pick a free one and rewrite the challenge's
    docker-compose.yml host-side mapping in place, returning the updated
    port list (so callers lock on the port they'll actually use).
    """
    if not ports:
        return ports
    # Check each port's occupancy exactly once and reuse the result --
    # calling _port_is_free twice per port (a fast-path check, then a
    # per-port check) is both wasteful and, for a connect-style probe, can
    # give different answers on each call; a single pass avoids relying on
    # occupancy staying constant between two separate checks.
    free = {p: _port_is_free(p) for p in ports}
    if all(free.values()):
        return ports

    try:
        d = _get_dataset()
        c = d.get(challenge)
        compose_path = Path(d.basedir) / c["path"] / "docker-compose.yml"
    except Exception as e:
        print(f"[port] {challenge}: couldn't resolve compose path ({e}), leaving ports as-is", flush=True)
        return ports
    if not compose_path.exists():
        return ports

    text = compose_path.read_text()
    new_ports = []
    changed = False
    for port in ports:
        if free[port]:
            new_ports.append(port)
            continue
        new_port = _find_free_port()
        pattern = re.compile(rf'(?<!\d)({re.escape(str(port))})(:\d+)')
        new_text, n = pattern.subn(lambda m: f"{new_port}{m.group(2)}", text)
        if n == 0:
            # The port we were told to look for (from the caller's possibly
            # stale metadata) isn't literally in the file -- almost always
            # because a *previous* job already remapped this exact challenge
            # earlier in the same run. Returning the stale value anyway is a
            # real bug, not just a cosmetic one: every other job that also
            # (per the same stale metadata) thinks it needs this port would
            # then acquire a lock keyed on a port number nothing is actually
            # using, while the port genuinely in use right now has no lock
            # protecting it at all -- lock state and reality diverge, and
            # concurrent jobs pile up waiting on a lock whose corresponding
            # resource conflict no longer exists (found live during the
            # 2026-09-20 retry batch: worker concurrency collapsed to 1/6
            # for 15+ minutes after this exact situation recurred across
            # several of the 24 previously-remapped port-5000 challenges).
            # Recover by reading the port actually in the file right now.
            # Pick a port the file actually publishes that this challenge's
            # port list doesn't already cover. Without the `not in new_ports`
            # guard, a multi-port challenge whose metadata is stale for one
            # port resolves it to a port already in the list -- e.g.
            # 2019f-web-biometric is recorded as ['15000', '5001'] but the
            # file publishes 5001 and 49186, so 15000 recovered to 5001 and
            # the caller ended up locking the same port twice. Acquiring one
            # non-reentrant Lock twice is an immediate self-deadlock that
            # also strands every later job needing that port (found live
            # during the 2026-09-22 gap-fill: the whole pool went idle with
            # 8 jobs queued).
            actual_ports = re.findall(r'(?<!\d)(\d+):\d+', text)
            declared = {str(p) for p in ports}
            actual = next((p for p in actual_ports
                           if p not in declared and p not in new_ports), None)
            if actual and _port_is_free(actual):
                print(f"[port] {challenge}: stale port {port} not in file, using its actual "
                      f"current port {actual} instead (already free)", flush=True)
                new_ports.append(actual)
            elif actual:
                print(f"[port] {challenge}: stale port {port} not in file; its actual current "
                      f"port {actual} is also occupied, remapping that instead", flush=True)
                new_port2 = _find_free_port()
                pattern2 = re.compile(rf'(?<!\d)({re.escape(actual)})(:\d+)')
                new_text2, n2 = pattern2.subn(lambda m: f"{new_port2}{m.group(2)}", text)
                if n2:
                    text = new_text2
                    changed = True
                    new_ports.append(str(new_port2))
                else:
                    new_ports.append(actual)
            else:
                # Every port the file publishes is already covered by an
                # earlier entry, so this stale one names nothing real. Drop
                # it rather than keep a value that only creates false lock
                # contention.
                print(f"[port] {challenge}: stale port {port} not in {compose_path.name} and "
                      f"its other ports are already covered -- dropping it", flush=True)
            continue
        print(f"[port] {challenge}: host port {port} occupied, remapped to {new_port}", flush=True)
        text = new_text
        new_ports.append(str(new_port))
        changed = True
    if changed:
        compose_path.write_text(text)
    return new_ports
