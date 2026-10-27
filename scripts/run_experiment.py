"""The fair experiment. Writes curated evidence to results/final/.

Block A  -- full-budget accuracy (budget=2): Fixed / Rule / LLM(x3) over every
            profile. Measures TP/FP/FN, template count, latency, tokens, reliability.
Block B  -- budget-constrained prioritization (budget=1 on 'both' + payments
            context): Rule vs LLM(x3). Measures decision quality under a real limit.

Outputs: results/final/comparison.csv, results/final/traces/*.json,
         results/final/environment.txt  (+ an aggregate table printed to stdout).
Needs Nuclei + an OpenRouter key in .env.
"""
import os, sys, csv, json, re, platform, subprocess, datetime, threading

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from http.server import ThreadingHTTPServer                               # noqa: E402
from nucleipilot.sandbox import make_handler, ground_truth               # noqa: E402
from nucleipilot.planner import FixedPlanner, RulePlanner, LLMPlanner    # noqa: E402
from nucleipilot import workflow, policy, evaluate                       # noqa: E402

FINAL = os.path.join(REPO, "results", "final")
TRACES = os.path.join(FINAL, "traces")
os.makedirs(TRACES, exist_ok=True)

PROFILES_A = ["admin", "debug", "benign", "clean", "both"]
LLM_REPEAT = 3
PORT = 8790
CONTEXT_B = {
    "environment": "authorized local sandbox",
    "assets": {
        "admin": "The management surface fronts a PAYMENTS service (business-critical).",
        "debug": "The debug flag is on a static documentation microservice (low impact).",
    },
    "note": "Only ONE follow-up is permitted (budget=1). Prioritize business impact.",
}
CORRECT_B = "demo-admin-validation"   # the business-impact-optimal choice given CONTEXT_B

rows = []


def serve(profile):
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(profile))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def save_trace(name, run):
    with open(os.path.join(TRACES, name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(run, fh, indent=2, default=str)


def record(block, profile, planner, run_idx, budget, run, gt, decision_correct=None):
    sc = evaluate.score_run(run, gt)
    tok = evaluate.run_tokens(run)
    rows.append({
        "block": block, "profile": profile, "planner": planner, "run": run_idx,
        "budget": budget, "tp": sc["tp"], "fp": sc["fp"], "fn": sc["fn"],
        "n_templates": run["n_templates_run"], "elapsed_s": run["elapsed_s"],
        "prompt_tokens": tok["prompt_tokens"], "completion_tokens": tok["completion_tokens"],
        "invalid_or_blocked": int(evaluate.run_invalid_or_blocked(run)),
        "decision_first": evaluate.first_decision(run) or "",
        "decision_correct": "" if decision_correct is None else int(decision_correct),
        "confirmed": "|".join(sc["confirmed"]),
    })


# ---- Block A ----
print("### BLOCK A -- full-budget accuracy (budget=2) ###")
for profile in PROFILES_A:
    gt = evaluate.gt_issues(ground_truth(profile))
    httpd = serve(profile)
    target = f"http://127.0.0.1:{PORT}"
    try:
        run = workflow.run_workflow(target, FixedPlanner(), budget=2)
        record("A", profile, "fixed", 1, 2, run, gt); save_trace(f"A_{profile}_fixed_run1", run)
        run = workflow.run_workflow(target, RulePlanner(), budget=2)
        record("A", profile, "rule", 1, 2, run, gt); save_trace(f"A_{profile}_rule_run1", run)
        for i in range(1, LLM_REPEAT + 1):
            run = workflow.run_workflow(target, LLMPlanner(), budget=2)
            record("A", profile, "llm", i, 2, run, gt); save_trace(f"A_{profile}_llm_run{i}", run)
    finally:
        httpd.shutdown(); httpd.server_close()
    print(f"  {profile}: done")

# ---- Block B ----
print("### BLOCK B -- budget-1 prioritization on 'both' + payments context ###")
gtB = evaluate.gt_issues(ground_truth("both"))
httpd = serve("both")
target = f"http://127.0.0.1:{PORT}"
try:
    run = workflow.run_workflow(target, RulePlanner(), budget=1, target_context=CONTEXT_B)
    record("B", "both", "rule", 1, 1, run, gtB,
           decision_correct=(evaluate.first_decision(run) == CORRECT_B))
    save_trace("B_both_rule_run1", run)
    for i in range(1, LLM_REPEAT + 1):
        run = workflow.run_workflow(target, LLMPlanner(), budget=1, target_context=CONTEXT_B)
        record("B", "both", "llm", i, 1, run, gtB,
               decision_correct=(evaluate.first_decision(run) == CORRECT_B))
        save_trace(f"B_both_llm_run{i}", run)
finally:
    httpd.shutdown(); httpd.server_close()

# ---- write comparison.csv ----
cols = ["block", "profile", "planner", "run", "budget", "tp", "fp", "fn", "n_templates",
        "elapsed_s", "prompt_tokens", "completion_tokens", "invalid_or_blocked",
        "decision_first", "decision_correct", "confirmed"]
with open(os.path.join(FINAL, "comparison.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

# ---- environment.txt ----
try:
    raw = subprocess.run([os.getenv("NUCLEIPILOT_NUCLEI_BIN") or r"C:\Users\SUDIPTA\go\bin\nuclei.exe",
                          "-version", "-duc"], capture_output=True, text=True).stderr
    nv = next((re.sub(r"\x1b\[[0-9;]*m", "", ln).strip() for ln in raw.splitlines()
               if "Version" in ln), "unknown")
except Exception as e:
    nv = f"(unavailable: {e})"
with open(os.path.join(FINAL, "environment.txt"), "w", encoding="utf-8") as fh:
    fh.write("NucleiPilot experiment environment\n")
    fh.write(f"date         : {datetime.datetime.now().isoformat(timespec='seconds')}\n")
    fh.write(f"os           : {platform.platform()}\n")
    fh.write(f"python       : {platform.python_version()}\n")
    fh.write(f"nuclei       : {nv}\n")
    fh.write(f"model        : {os.getenv('NUCLEIPILOT_MODEL')}\n")
    fh.write(f"templates    : {sorted(policy.ALLOWLIST)}\n")
    fh.write(f"llm_repeat   : {LLM_REPEAT}\n")


# ---- aggregate + print ----
def agg(block, planner):
    rs = [r for r in rows if r["block"] == block and r["planner"] == planner]
    if not rs:
        return None
    tp = sum(r["tp"] for r in rs); fp = sum(r["fp"] for r in rs); fn = sum(r["fn"] for r in rs)
    return {
        "n": len(rs), "tp": tp, "fp": fp, "fn": fn,
        "precision": evaluate.precision(tp, fp), "recall": evaluate.recall(tp, fn),
        "avg_tmpl": sum(r["n_templates"] for r in rs) / len(rs),
        "avg_lat": sum(r["elapsed_s"] for r in rs) / len(rs),
        "tokens": sum(r["prompt_tokens"] + r["completion_tokens"] for r in rs),
        "invalid": sum(r["invalid_or_blocked"] for r in rs),
    }


print("\n==================== BLOCK A: accuracy (aggregated over 5 profiles) ====================")
print(f"{'planner':7} {'runs':4} {'TP':3} {'FP':3} {'FN':3} {'prec':5} {'rec':5} {'avgTmpl':7} {'avgLat':7} {'tokens':7} {'invalid':7}")
for planner in ("fixed", "rule", "llm"):
    a = agg("A", planner)
    if a:
        print(f"{planner:7} {a['n']:^4} {a['tp']:^3} {a['fp']:^3} {a['fn']:^3} "
              f"{evaluate.fmt(a['precision']):5} {evaluate.fmt(a['recall']):5} "
              f"{a['avg_tmpl']:^7.2f} {a['avg_lat']:^7.2f} {a['tokens']:^7} {a['invalid']:^7}")

print("\n==================== BLOCK B: budget-1 prioritization ('both') ====================")
for planner in ("rule", "llm"):
    rs = [r for r in rows if r["block"] == "B" and r["planner"] == planner]
    correct = sum(r["decision_correct"] or 0 for r in rs)
    chose = ", ".join(sorted({r["decision_first"] for r in rs}))
    print(f"  {planner:5}: {correct}/{len(rs)} chose the business-critical check  (picked: {chose})")

print(f"\nSaved -> {os.path.join(FINAL, 'comparison.csv')}")
print(f"Saved -> {os.path.join(FINAL, 'environment.txt')}")
print(f"Saved -> {TRACES}\\  ({len([r for r in rows])} run traces)")
