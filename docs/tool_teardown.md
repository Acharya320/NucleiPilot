# Tool Teardown — Nuclei (the tool NucleiPilot extends)

*Part 2 lead-in. NucleiPilot takes **Path A** (extend an existing tool): it keeps Nuclei as the
detection engine and adds a governed, evidence-driven **agentic layer** on top. This page is the
short teardown of Nuclei itself — what it is, how it works, who uses it, where its workflow falls
short, and why the agentic layer earns its place.*

## What exists today
[Nuclei](https://github.com/projectdiscovery/nuclei) (ProjectDiscovery) is an open-source,
template-driven vulnerability scanner written in Go. Its detection logic lives in **YAML templates**,
not in code: each template declares one or more requests (HTTP / DNS / TCP / headless / …) and
**matchers** — status code, word, regex, or DSL expressions — that decide whether a target is
affected. ProjectDiscovery maintains a large community template library (thousands of templates, many
mapped to specific CVEs), and users can write their own. The PoC uses **Nuclei v3.11.1** with custom
templates. Nuclei is listed in the assignment's "foundational tools — add an agentic layer."

## How it works
You point Nuclei at a target (or a target list) plus a set of templates; it runs them concurrently
and prints each match with the matched URL and the matcher that fired. It is fast, scriptable, and
CI-friendly, and emits JSON for downstream tooling. The flags NucleiPilot relies on keep it safe and
deterministic: `-ni` (no interactsh/OAST — **no outbound callbacks**), `-duc` (no auto-update),
`-silent`, and JSON output. The Nuclei command line itself is built in NucleiPilot's code, so a
caller cannot inject flags or redirect it off-scope.

## Who uses it
AppSec and security-engineering teams, penetration testers and red teams, bug-bounty researchers, and
automated security pipelines — CI/CD security gates and attack-surface-management (ASM) platforms that
run Nuclei at scale across large asset inventories.

## Where the current workflow falls short
1. **No prioritization under a budget.** Nuclei runs whatever template set you give it, in no business
   order. When scan time/budget is tight and many signals compete, it has no notion of *which* check
   matters most.
2. **A match is a signal, not a verdict.** A template fires on an indicator (a header, a banner);
   turning that into a confirmed, de-duplicated, false-positive-free finding is manual triage.
3. **Technical severity ≠ business impact.** Ranking is by severity (CVSS-style), not by what the
   asset is worth to the organization. A medium-severity flaw on a payments service can matter far
   more than a high-severity one on a docs page — Nuclei cannot know that.
4. **No governance around *which* checks run and why.** It executes what it is told; there is no
   built-in scope allowlist, approved-template list, budget, or audit trail — the controls a regulated
   buyer (e.g. a bank) asks for first.

## Why the agentic capability is useful (what NucleiPilot adds)
NucleiPilot keeps Nuclei as the detection engine and adds a thin layer that:
- **Triages on evidence** — an *indicator* is only a hint; a *validation* confirms it by matching a
  content signature, so false positives are rejected on evidence (the `/docs` vs `/health` trap).
- **Prioritizes by business context under a hard budget** — it validates the business-critical issues
  first, which a severity-only pass misses.
- **Stays governed** — the model only *proposes*; code authorizes every scan (scope + approved
  catalog + budget) and records a full trace. The invariant is *"model proposes, code authorizes."*
- **Generalizes without new code** — a new target is one more asset-registry + catalog entry, shown
  live on Grafana (version → applicable CVE with zero CVE-specific decision code).

See the [README](../README.md) to run it, and [analysis.md](analysis.md) for the honest evaluation of
what the agentic layer did and did not improve.
