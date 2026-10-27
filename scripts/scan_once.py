"""Run the REAL Nuclei binary (via the scope-guarded wrapper) against the toy
sandbox for one profile, all four templates, and save the evidence JSON.
    python scripts/scan_once.py --profile admin
Needs Nuclei on PATH (or NUCLEIPILOT_NUCLEI_BIN / --bin).
"""
import sys, os, json, threading, argparse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from http.server import ThreadingHTTPServer                      # noqa: E402
from nucleipilot.sandbox import make_handler, ground_truth       # noqa: E402
from nucleipilot import scanner, policy                          # noqa: E402

TEMPLATES = ["demo-admin-indicator", "demo-admin-validation",
             "demo-debug-indicator", "demo-debug-validation"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="admin",
                    choices=["admin", "debug", "benign", "clean", "both"])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--bin", default=None, help="path to nuclei binary")
    args = ap.parse_args()

    target = f"http://127.0.0.1:{args.port}"
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.profile))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"Sandbox up: profile={args.profile}  ground_truth={sorted(ground_truth(args.profile))}")

    saved = []
    try:
        for tid in TEMPLATES:
            res = scanner.run_template(target, policy.template_path(tid), nuclei_bin=args.bin)
            mark = "MATCH" if res.matched else "  -- "
            dur = f"{res.duration_s:.2f}s" if res.duration_s else "?"
            print(f"  [{mark}] {tid:24} sev={str(res.severity):6} at={res.matched_at} ({dur})"
                  + (f"  ERROR={res.error}" if res.error else ""))
            saved.append(res.to_dict())
    finally:
        httpd.shutdown(); httpd.server_close()

    out = os.path.join(REPO, "results", f"{args.profile}_scan.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"profile": args.profile, "target": target,
                   "ground_truth": sorted(ground_truth(args.profile)),
                   "results": saved}, fh, indent=2, default=str)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()
