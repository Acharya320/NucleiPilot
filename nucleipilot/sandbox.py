"""NucleiPilot toy sandbox target.

A tiny, fully self-contained HTTP server that listens on 127.0.0.1 ONLY.
It exposes a handful of endpoints whose responses encode *synthetic*
vulnerability indicators. Nothing here is a real vulnerability and no real
data is involved -- it exists only so we can test the agent against a known
answer key in an authorized, local sandbox.

Two kinds of endpoint per "issue":
  * an INDICATOR endpoint  -> a weak signal ("looks like X might be true")
  * a VALIDATION endpoint  -> stronger synthetic confirmation ("X is really true")

The distinction matters: a signal is not proof. The `benign` profile shows a
debug *indicator* but NO confirmed exposure, so an agent that reports it as a
real finding is producing a false positive -- exactly the behaviour we want to
measure.

The agent never sees the profile; it only sees HTTP responses, like a real scan.

Run directly:
    python -m nucleipilot.sandbox --profile admin --port 8765
Stop with Ctrl+C.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Ground truth ---------------------------------------------------------
# The set of synthetic conditions that are GENUINELY present for each profile.
# This is the independent "answer key" the experiment scores against. The
# agent's own output is NEVER used to decide ground truth.
PROFILES: dict[str, set[str]] = {
    "admin":  {"admin_auth_missing"},                      # one true condition
    "debug":  {"debug_exposed"},                           # a different true condition
    "benign": set(),            # a debug *indicator* shows, but exposure is NOT real
    "clean":  set(),            # negative control: nothing present
    "both":   {"admin_auth_missing", "debug_exposed"},     # both present
}


def ground_truth(profile: str) -> set[str]:
    """Return the set of synthetic conditions truly present for a profile."""
    if profile not in PROFILES:
        raise ValueError(
            f"unknown profile {profile!r}; choose from {sorted(PROFILES)}"
        )
    return set(PROFILES[profile])


# --- Which endpoints "fire" for a given profile ---------------------------
# Admin indicator/validation fire when an admin condition is present.
# Debug INDICATOR fires for debug, both, AND benign (benign is the misleading case).
# Debug VALIDATION fires only when the exposure is genuinely present.
def _flags(profile: str) -> dict[str, bool]:
    return {
        "admin_indicator":  profile in {"admin", "both"},
        "admin_validation": profile in {"admin", "both"},
        "debug_indicator":  profile in {"debug", "both", "benign"},
        "debug_validation": profile in {"debug", "both"},
    }


def _responses(profile: str) -> dict[str, dict]:
    """Map URL path -> JSON body to return for this profile."""
    f = _flags(profile)
    return {
        "/": {
            "service": "nucleipilot-toy-app",
            "profile_is_hidden_from_client": True,
            "note": "synthetic sandbox; 127.0.0.1 only; not a real application",
        },
        # --- admin "issue" ---
        "/metadata": (
            {"service": "toy-app", "management_surface": "present",
             "note": "synthetic admin indicator"}
            if f["admin_indicator"] else
            {"service": "toy-app", "management_surface": "absent"}
        ),
        "/management/status": (
            {"endpoint": "management", "authentication": "not-required",
             "synthetic": True}
            if f["admin_validation"] else
            {"endpoint": "management", "authentication": "required"}
        ),
        # --- debug "issue" ---
        "/debug/config": (
            {"debug": "true", "synthetic_indicator": True}
            if f["debug_indicator"] else
            {"debug": "false"}
        ),
        "/debug/confirm": (
            {"debug_exposure": "confirmed",
             "synthetic_secret": "TOY-DEBUG-TOKEN-DO-NOT-USE", "synthetic": True}
            if f["debug_validation"] else
            {"debug_exposure": "not-exposed"}
        ),
    }


def make_handler(profile: str):
    table = _responses(profile)

    class Handler(BaseHTTPRequestHandler):
        server_version = "NucleiPilotToy/0.1"

        def do_GET(self):  # noqa: N802 (http.server API)
            body_obj = table.get(self.path)
            status = 200 if body_obj is not None else 404
            if body_obj is None:
                body_obj = {"error": "not-found", "path": self.path}
            payload = json.dumps(body_obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):
            # concise one-line access log so you can watch scans arrive
            print(f"[sandbox:{profile}] {self.address_string()} {fmt % args}")

    return Handler


def serve(profile: str, port: int, host: str = "127.0.0.1") -> None:
    if host != "127.0.0.1":
        raise ValueError("sandbox refuses to bind anything other than 127.0.0.1")
    ground_truth(profile)  # validate profile name early
    httpd = ThreadingHTTPServer((host, port), make_handler(profile))
    print(f"Toy sandbox serving profile={profile!r} on http://{host}:{port}")
    print(f"Ground truth for this profile: {sorted(ground_truth(profile)) or '(none)'}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping sandbox.")
    finally:
        httpd.server_close()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="NucleiPilot toy sandbox target (localhost only).")
    ap.add_argument("--profile", default="admin", choices=sorted(PROFILES),
                    help="which synthetic conditions are present")
    ap.add_argument("--port", type=int, default=8765, help="localhost port")
    args = ap.parse_args(argv)
    serve(args.profile, args.port)


if __name__ == "__main__":
    main()
