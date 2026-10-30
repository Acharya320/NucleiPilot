"""NucleiPilot scaled toy app (v2 measurement bench).

A single small web app on 127.0.0.1 with FIVE components, each carrying its own
*synthetic* condition. Unlike the v1 profile sandbox (nucleipilot/sandbox.py),
all conditions are present AT ONCE -- this is one app with several endpoints,
and business importance is assigned PER ENDPOINT by configuration (the asset
registry, Phase 2), not by the server. See docs/toy_spec.md for the full design.

Nothing here is a real vulnerability and no real data is involved. Every
"secret" is an obvious planted marker. Localhost only.

Endpoints (see docs/toy_spec.md):
  /payments                     ISSUE-ADMIN indicator  -> "Admin Console" banner
  /payments/admin/config.json   ISSUE-ADMIN validation -> authentication disabled
  /docs                         ISSUE-DEBUG indicator  -> header X-Debug-Mode: enabled
  /docs/debug/vars              ISSUE-DEBUG validation -> stacktrace + internal path
  /account/export               ISSUE-PII  indicator   -> framework name (Jinja2)
  /account/export?id=..         ISSUE-PII  validation  -> traceback + planted secret
  /health                       TRAP indicator         -> header X-Debug-Mode: enabled (SAME as /docs)
  /health/debug/vars            TRAP validation        -> 404, no signature (benign)
  /home , /                     clean                  -> no signal

Run directly:
    python -m nucleipilot.toyapp --port 8777
Stop with Ctrl+C.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

# --- Answer key (ground truth) -------------------------------------------
# Which planted issues are GENUINELY present, and what confirms each. This is
# the independent answer key the experiment scores against; the agent's own
# output is NEVER used to decide ground truth. A machine-readable copy lives in
# config/toy_answer_key.json and a test asserts the two agree.
#
# Business importance is deliberately NOT here -- it is assigned per endpoint in
# the asset registry (Phase 2). This is only the vulnerability ground truth.
ANSWER_KEY: dict[str, dict] = {
    "ISSUE-ADMIN": {
        "endpoint": "/payments", "real": True, "tech_severity": "medium",
        "indicator": "toy-admin-indicator", "validation": "toy-admin-validation",
    },
    "ISSUE-DEBUG": {
        "endpoint": "/docs", "real": True, "tech_severity": "high",
        "indicator": "toy-debug-indicator", "validation": "toy-docs-debug-validation",
    },
    "ISSUE-PII": {
        "endpoint": "/account", "real": True, "tech_severity": "medium",
        "indicator": "toy-pii-indicator", "validation": "toy-pii-validation",
    },
    "TRAP-DEBUG": {
        "endpoint": "/health", "real": False, "tech_severity": None,
        "indicator": "toy-debug-indicator", "validation": "toy-health-debug-validation",
        "note": "shares the /docs debug indicator; its validation finds no signature -> NOT_CONFIRMED",
    },
}
CLEAN_ENDPOINTS = ["/home"]


def answer_key() -> dict:
    """Return a copy of the ground-truth answer key."""
    return json.loads(json.dumps(ANSWER_KEY))


# --- Planted response content --------------------------------------------
_DEBUG_HEADERS = {"X-Debug-Mode": "enabled"}

_ADMIN_BANNER = (
    "<html><body><h1>Payments</h1>"
    '<p>Internal tools: <a href="/payments/admin">Admin Console</a></p>'
    "</body></html>"
)
_ADMIN_CONFIG = {
    "service": "payments-admin",
    "authentication": "disabled",
    "note": "synthetic: authentication intentionally disabled on the toy",
}
_DOCS_DEBUG_VARS = {
    "stacktrace": ["at /srv/app/internal/handler.py line 42 in render()"],
    "vars": {"env": "debug", "build": "toy"},
    "synthetic": True,
}
_PII_INDICATOR = {
    "error": "missing id",
    "engine": "Jinja2",
    "hint": "template rendering failed; provide an id to export",
}
_PII_VALIDATION = (
    "Traceback (most recent call last):\n"
    '  File "/srv/app/internal/account.py", line 88, in export\n'
    "    render_user(id)\n"
    "RuntimeError: export failed\n"
    "TOY_SECRET_KEY=planted-marker\n"
)


def _json(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


def dispatch(path: str, query: dict) -> tuple[int, bytes, str, dict]:
    """Pure routing: (normalized path, parsed query) -> (status, body, content_type, extra_headers).

    Factored out of the handler so tests and the smoke script can call it directly.
    """
    if path in ("/", "/home"):
        return 200, _json({"page": "home", "content": "public landing page"}), "application/json", {}
    if path == "/payments":
        return 200, _ADMIN_BANNER.encode("utf-8"), "text/html", {}
    if path == "/payments/admin/config.json":
        return 200, _json(_ADMIN_CONFIG), "application/json", {}
    if path == "/docs":
        return 200, _json({"page": "docs", "content": "product documentation"}), "application/json", dict(_DEBUG_HEADERS)
    if path == "/docs/debug/vars":
        return 200, _json(_DOCS_DEBUG_VARS), "application/json", {}
    if path == "/account/export":
        if "id" in query:
            return 200, _PII_VALIDATION.encode("utf-8"), "text/plain", {}
        return 200, _json(_PII_INDICATOR), "application/json", {}
    if path == "/health":
        return 200, _json({"status": "ok"}), "application/json", dict(_DEBUG_HEADERS)
    if path == "/health/debug/vars":
        return 404, _json({"error": "not-found"}), "application/json", {}
    return 404, _json({"error": "not-found", "path": path}), "application/json", {}


def make_handler():
    class Handler(BaseHTTPRequestHandler):
        server_version = "NucleiPilotToyV2/0.1"

        def do_GET(self):  # noqa: N802 (http.server API)
            parts = urlsplit(self.path)
            path = parts.path.rstrip("/") or "/"
            query = parse_qs(parts.query)
            status, body, ctype, extra = dispatch(path, query)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in extra.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            print(f"[toyapp] {self.address_string()} {fmt % args}")

    return Handler


def serve(port: int = 8777, host: str = "127.0.0.1") -> None:
    if host != "127.0.0.1":
        raise ValueError("toy app refuses to bind anything other than 127.0.0.1")
    httpd = ThreadingHTTPServer((host, port), make_handler())
    print(f"Scaled toy app serving on http://{host}:{port}")
    print("Components: /payments /account /docs /health /home  (see docs/toy_spec.md)")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping toy app.")
    finally:
        httpd.server_close()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="NucleiPilot scaled toy app (localhost only).")
    ap.add_argument("--port", type=int, default=8777, help="localhost port")
    args = ap.parse_args(argv)
    serve(args.port)


if __name__ == "__main__":
    main()
