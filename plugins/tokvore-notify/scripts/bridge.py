#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Agent hook -> tokvore /hooks forwarder.

Invoked from hooks.json:
    uv run bridge.py [--client claude|codex]

Reads one agent hook-event JSON on stdin and forwards it VERBATIM to
tokvore's loopback `/hooks` endpoint, wrapped in an envelope:

    { "client": "claude", "hook": <the raw hook event> }

The only field this bridge ADDS is `hook.pid` -- this bridge process's own pid --
when the payload lacks one. The bridge runs as a descendant of the agent process
and shares its console, so tokvore's host resolver can walk from this pid up to the
hosting terminal / IDE window and register the session for click-to-focus. Codex
hooks carry no pid and Codex exposes none via env, so without this a Codex session
is listed but not focusable; Claude ignores it (its own `~/.claude/sessions`
descriptor already carries the real pid).

Beyond that the bridge does NO interpretation: it does not pick which events matter,
does not extract sessionId/title/body, and does not build any notification text. All
of that lives in the tokvore backend's per-client interpreter, so behavior can change
without reinstalling the plugin and the backend can do richer parsing on the full
payload.

`client` defaults to "claude" and can be selected with `--client`. The backend
routes by this field to the matching interpreter; an unknown client is rejected
with 400.

The stdin JSON is parsed only to validate it is well-formed and to re-wrap it
cleanly (no semantics are read). Every failure is swallowed (exit 0) so a hook
can never disrupt the session.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

DEFAULT_CLIENT = "claude"
SUPPORTED_CLIENTS = ("claude", "codex")
DEFAULT_PORT = 6789  # control-api conventional default, used when settings absent

# Claude Code emits UTF-8 hook JSON; Windows defaults stdin to the OEM code page
# (CP950/CP936) and mangles non-ASCII before json.loads sees it. Force UTF-8.
for _stream in (sys.stdin, sys.stdout):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def api_port() -> int:
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    if home:
        try:
            path = Path(home) / ".config" / "tokvore" / "settings.json"
            port = json.loads(path.read_text("utf-8")).get("apiPort")
            if isinstance(port, int) and 0 < port < 65536:
                return port
        except Exception:
            pass
    return DEFAULT_PORT


def with_pid(hook: dict) -> dict:
    """Add this bridge process's pid to the hook (for tokvore focus registration),
    without clobbering an existing pid. The backend walks from this pid up to the
    hosting terminal/IDE. Non-dict payloads are returned unchanged."""
    if isinstance(hook, dict):
        hook.setdefault("pid", os.getpid())
    return hook


def envelope(hook: dict, client: str) -> dict:
    """Wrap a raw hook event in the {client, hook} forwarding envelope."""
    return {"client": client, "hook": hook}


def post_hook(hook: dict, client: str) -> None:
    req = urllib.request.Request(
        f"http://127.0.0.1:{api_port()}/hooks",
        data=json.dumps(envelope(hook, client)).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-TOKVORE-CLIENT": client},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=3).close()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--client", choices=SUPPORTED_CLIENTS, default=DEFAULT_CLIENT)
    parser.add_argument("--selftest", action="store_true")
    args, _ = parser.parse_known_args(argv)

    if args.selftest:
        return selftest()
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0  # nothing on stdin -> nothing to forward
        # Parse only to validate well-formed JSON and re-wrap cleanly; the only
        # mutation is adding this bridge's pid for focus registration -- no
        # semantics are extracted here, the backend does all interpretation.
        hook = with_pid(json.loads(raw))
        post_hook(hook, args.client)
    except Exception:
        pass  # never disrupt the session
    return 0


def selftest() -> int:
    env = envelope({"hook_event_name": "Stop", "session_id": "s1", "cwd": "/x/proj"}, "claude")
    assert env["client"] == "claude"
    assert env["hook"]["hook_event_name"] == "Stop"  # hook forwarded verbatim
    assert env["hook"]["session_id"] == "s1"
    assert set(env.keys()) == {"client", "hook"}  # envelope is exactly {client, hook}
    codex_env = envelope({"hook_event_name": "Stop"}, "codex")
    assert codex_env["client"] == "codex"
    # pid injection: added when absent, never clobbers an existing pid.
    assert with_pid({"hook_event_name": "Stop"})["pid"] == os.getpid()
    assert with_pid({"pid": 123})["pid"] == 123
    assert with_pid("not-a-dict") == "not-a-dict"  # non-dict passes through
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
