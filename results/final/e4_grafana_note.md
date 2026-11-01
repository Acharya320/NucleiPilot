# E4 - NucleiPilot on live Grafana 8.3.0, using the real ~14k corpus

*The real-world counterpart to the toy (E1-E3). Same engine, a real app, and the actual
ProjectDiscovery template corpus. This is where the LLM earns its place -- and where
generalization is shown as **data, not code**. Read with `e4_grafana_summary.md` and
`e4_grafana_run.json`.*

## What it does (one run, four steps)

1. **Fingerprint** the live Grafana container via `/api/health` -> **8.3.0**.
2. **Curate** the candidate pool: the **12 grafana-tagged CVEs** a fair `-tags grafana` rule
   gathers from the real corpus (`config/grafana_corpus.json`, mechanically extracted by
   `scripts/build_grafana_fixture.py` -- not hand-picked).
3. **Select** which CVEs apply to 8.3.0: TAG rule vs a naive VERSION parser vs the LLM.
4. **Validate live**: the LLM's applicable pick, if on the **read-only safe allowlist**, is run
   against the container **through the same engine** (policy gate -> Nuclei -> code verdict).

## Result (measured; 3 stable LLM runs)

| Method | Precision | Recall | F1 |
|---|---:|---:|---:|
| TAG rule (runs every grafana CVE) | 0.08 | 1.00 | 0.15 |
| VERSION rule (naive parser) | 0.17 | 1.00 | 0.29 |
| **LLM** | **1.00** | **1.00** | **1.00** |

- The LLM selects exactly **CVE-2021-43798** every run, then the **real community template runs
  live and the code verdict is CONFIRMED** (file read of `/etc/passwd` via the plugin traversal).
- The TAG rule cannot read versions, so it would run all 12 (11 wasted). The VERSION parser is
  fooled by inconsistent/missing ranges ("up to 7.5.11 **and** 8.1.5"; "below or equals to 12.0.1").

## Why the LLM is genuinely needed here (not a rigged win)

Affected-version data in real templates is **inconsistent free-text prose**, with no
machine-readable range field. Matching the detected version against it is a reading task -
exactly where tag/keyword rules and simple parsers break and an LLM does well. On the small,
clean toy (E1-E3) the LLM only **ties** a rule; here, on the large messy corpus, it **clearly
wins**. The agent's value scales with the size and messiness of the template space.

## Generalization: data, not code

Running Grafana used the **same `profile -> decide -> authorize -> scan -> verify` engine** as the
toy. A new target + new CVEs plugged in as **catalog/registry data** (the corpus fixture), with
**zero CVE-specific decision code**. Honesty: a *generic* rules engine could also match versions
*if* the ranges were machine-readable - but in the real corpus they are not, which is precisely
why reading (the LLM) pays off. The durable value is **generalization without hand-written
per-CVE rules**.

## Safety: the read-only gate did real work

Several grafana-tagged CVEs here are **intrusive** (snapshot-creation DoS, auth bypass). The
executable allowlist is **read-only templates only** (`config/grafana_ground_truth.json` ->
`read_only_safe`), so the policy gate **refuses to run an intrusive pick even if proposed**. The
LLM happened to pick the read-only file-read CVE; the gate is the backstop that makes "the model
proposes, code authorizes" hold against a real corpus.

## Honest limits (do not overclaim)

- **One product, one version** - a concrete demonstration that the gap is real, **not** a
  measurement of accuracy across many products/CVEs. That breadth is the Part 4 pilot's job.
- **Part of the LLM's edge is world knowledge** (it infers "2024/2025 CVE -> newer feature ->
  does not affect 8.3.0"), not just the text - a real advantage a parser lacks, but one that can
  be **wrong if its priors are wrong**.
- **The LLM is a selector, not the authority.** It only proposes which check to run; code gates it
  and assigns the verdict. A wrong selection wastes a scan; it cannot fabricate a finding.

## Reproducing from the full corpus (the 14k is referenced, not bundled)

E4's candidate pool (`config/grafana_corpus.json`) reproduces the selection scores with **no
external files**. To regenerate it from the real corpus and verify it was not hand-picked:

- **Corpus:** ProjectDiscovery **nuclei-templates `v10.5.1`** - public, ~89 MB, 14,104 templates.
  Fetch with `nuclei -update-templates`, or
  `git clone --branch v10.5.1 https://github.com/projectdiscovery/nuclei-templates`.
- **Engine:** Nuclei **v3.11.1**.
- **Regenerate the fixture:** `python scripts/build_grafana_fixture.py --corpus <path>`.
- **Live run (step 4):** `python scripts/run_grafana.py --corpus <path>` (needs Docker; it uses the
  real community template `http/cves/2021/CVE-2021-43798.yaml` from the corpus).

The corpus is **not bundled** in the submission: it is a large, public, third-party set under
ProjectDiscovery's license. Pinning the version + committing the extractor and the small derived
fixture gives full reproducibility without vendoring 89 MB of someone else's templates.
