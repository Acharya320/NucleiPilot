"""Smoke test: start the toy sandbox for a few profiles and hit every endpoint,
to show indicator vs. validation behaviour (and the misleading 'benign' case).
Pure stdlib; no Nuclei, no API key. Run from anywhere:
    python scripts/smoke_sandbox.py
"""
import sys, os, json, threading, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from http.server import ThreadingHTTPServer                      # noqa: E402
from nucleipilot.sandbox import make_handler, ground_truth       # noqa: E402

PATHS = ["/metadata", "/management/status", "/debug/config", "/debug/confirm"]


def run(profile, port):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(profile))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    gt = sorted(ground_truth(profile)) or "(none)"
    print(f"\n=== profile={profile}   ground_truth={gt} ===")
    for p in PATHS:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{p}") as r:
            print(f"  {p:20} -> {json.dumps(json.loads(r.read()))}")
    httpd.shutdown(); httpd.server_close()


if __name__ == "__main__":
    for i, prof in enumerate(["admin", "benign", "clean"]):
        run(prof, 8800 + i)
    print("\nSmoke test OK.")
