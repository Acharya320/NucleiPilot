"""E4 -- real-app generalization: the SAME engine runs Grafana, not just the toy.

A new target is just another entry in the asset registry + catalog. The agent
fingerprints the running Grafana version; the planner reasons which CVE applies from
that version (the LLM does this from catalog descriptions with ZERO CVE-specific code);
code authorizes it; and the file-read is confirmed by retrieving a HARMLESS planted
marker file. /etc/passwd is read as a secondary proof of the real CVE primitive.

Authorized, localhost-only: this scans YOUR OWN local Grafana 8.3.0 container.

    python scripts/run_grafana.py

Starts grafana/grafana:8.3.0 on 127.0.0.1:3000 if it is not already up, plants the
marker, runs the demo, and leaves the container running (for the demo video).
Stop it with:  docker rm -f np-grafana
Needs: Docker, Nuclei v3, and an OpenRouter key in .env (method C reasons about the CVE).
"""
import os, sys, json, time, subprocess, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from nucleipilot import policy, registry, profiler, engine, planners, scanner, verifier  # noqa: E402

PORT = 3000
BASE = f"http://127.0.0.1:{PORT}"
NAME = "np-grafana"
MARKER_PATH = "/tmp/np-marker.txt"
MARKER = "NUCLEIPILOT-MARKER-7f3a-harmless-planted"
OUT = os.path.join(REPO, "results", "final")


def _health_version(timeout=2):
    try:
        with urllib.request.urlopen(BASE + "/api/health", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace")).get("version")
    except Exception:
        return None


def ensure_grafana():
    v = _health_version()
    if v:
        print(f"Grafana already running (version {v}).")
    else:
        print("Starting Grafana 8.3.0 container...")
        subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
        rc = subprocess.run(["docker", "run", "-d", "--name", NAME, "-p", f"127.0.0.1:{PORT}:3000",
                             "grafana/grafana:8.3.0"], capture_output=True, text=True)
        if rc.returncode != 0:
            print("Could not start Grafana via Docker:\n" + (rc.stderr or ""))
            print(f"Start it manually: docker run -d --name {NAME} -p 127.0.0.1:{PORT}:3000 grafana/grafana:8.3.0")
            sys.exit(2)
        for _ in range(40):
            v = _health_version()
            if v:
                break
            time.sleep(0.75)
        if not v:
            print("Grafana did not become healthy in time."); sys.exit(2)
        print(f"Grafana up (version {v}).")
    # plant the harmless marker (idempotent)
    subprocess.run(["docker", "exec", NAME, "sh", "-c", f'echo "{MARKER}" > {MARKER_PATH}'],
                   capture_output=True)
    return v


def main():
    os.makedirs(OUT, exist_ok=True)
    version = ensure_grafana()

    asset = registry.get_asset(registry.load_registry(), "grafana-local")
    cat = policy.load_catalog(registry.catalog_path(asset))

    # method C is required: the generalization/E6 point IS the LLM reasoning version->CVE
    try:
        from nucleipilot.llm_client import LLMClient
        client = LLMClient()
        if not client.api_key:
            print("No OpenRouter key in .env; method C is required for this demo. Aborting.")
            sys.exit(2)
    except Exception as e:
        print(f"LLM client unavailable: {e}"); sys.exit(2)

    scanner.assert_in_scope(BASE)
    prof = profiler.profile_grafana(asset, cat)
    print(f"\nProfiled: detected {prof.tech_facts}")
    print(f"Candidates offered to the agent: {prof.endpoints['/']['candidate_validations']}")

    result = engine.run(asset, cat, planners.LLMPlanner(client=client), profile=prof)
    chose = result["chosen_order"]
    print(f"\nLLM chose: {chose}")
    for e in result["trace"]:
        if e["step"] == "decision" and e["detail"].get("chosen"):
            print(f"  reason: {e['detail']['reason']}")

    # secondary proof: the real CVE primitive also reads /etc/passwd (harmless on a container)
    passwd_path = os.path.join(REPO, "templates", "grafana-cve-2021-43798-passwd.yaml")
    passwd = scanner.run_template(BASE, passwd_path)
    passwd_status = verifier.verdict(True, passwd)

    evidence = {
        "asset": asset["id"],
        "detected_version": version,
        "candidates": prof.endpoints["/"]["candidate_validations"],
        "llm_chose": chose,
        "findings": result["findings"],
        "marker_file": {"path": MARKER_PATH, "value": MARKER},
        "secondary_passwd_read": {"status": passwd_status, "matched_at": passwd.matched_at},
        "metrics": result["metrics"],
    }
    with open(os.path.join(OUT, "grafana_demo.json"), "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2)

    print(f"\nMarker-read finding(s): {[f['status'] for f in result['findings']]}")
    print(f"Secondary /etc/passwd read: {passwd_status}")
    print(f"\nSaved -> {os.path.join(OUT, 'grafana_demo.json')}")
    print(f"Container left running for the demo. Stop with:  docker rm -f {NAME}")


if __name__ == "__main__":
    main()
