"""Smoke test for the scaled toy app (nucleipilot/toyapp.py).

Starts the app on localhost and checks that every endpoint serves the exact
signature its template keys on -- header or body -- including the benign trap
(/health shows the debug header, but /health/debug/vars carries no signature).
Pure stdlib; no Nuclei, no API key. Run from anywhere:

    python scripts/smoke_toyapp.py
"""
import sys, os, threading, urllib.request, urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from http.server import ThreadingHTTPServer                 # noqa: E402
from nucleipilot.toyapp import make_handler                 # noqa: E402

PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"


def fetch(path):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


# (path, expected_status, (header_name, header_substr) | None, [body_substrings])
CHECKS = [
    ("/payments",                    200, None,                       ["Admin Console"]),
    ("/payments/admin/config.json",  200, None,                       ["authentication", "disabled"]),
    ("/docs",                        200, ("X-Debug-Mode", "enabled"), []),
    ("/docs/debug/vars",             200, None,                       ["stacktrace", "/srv/app/internal"]),
    ("/account/export",              200, None,                       ["Jinja2"]),
    ("/account/export?id=../",       200, None,                       ["Traceback (most recent call last)", "TOY_SECRET_KEY=planted-marker"]),
    ("/health",                      200, ("X-Debug-Mode", "enabled"), []),
    ("/health/debug/vars",           404, None,                       []),   # trap: no signature
    ("/home",                        200, None,                       []),   # clean
]


def main():
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler())
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"Toy app on {BASE}\n")
    ok = True
    for path, exp_status, hdr, body_subs in CHECKS:
        status, headers, body = fetch(path)
        problems = []
        if status != exp_status:
            problems.append(f"status {status} != {exp_status}")
        if hdr is not None:
            name, val = hdr
            got = headers.get(name)
            if got is None or val.lower() not in got.lower():
                problems.append(f"header {name}={got!r} lacks {val!r}")
        for sub in body_subs:
            if sub not in body:
                problems.append(f"body missing {sub!r}")
        # the trap must NOT carry the debug stack-trace signature
        if path == "/health/debug/vars" and ("stacktrace" in body or "/srv/app/internal" in body):
            problems.append("trap leaked a debug signature!")
        mark = "OK  " if not problems else "FAIL"
        if problems:
            ok = False
        print(f"  [{mark}] {path:34} {'; '.join(problems)}")
    httpd.shutdown()
    httpd.server_close()
    print("\nSmoke test", "PASSED." if ok else "FAILED.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
