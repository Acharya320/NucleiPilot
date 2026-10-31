# E6 - Generalization / rule-maintenance cost (an honest taste)

*A small, concrete illustration of where the agentic layer's value actually sits - the
one thing the fully-labeled toy cannot show. Read with `docs/toy_spec.md` §7. This is a
**taste on one case, not a scale claim.***

## What happened (see `grafana_demo.json`)

Grafana was added to the system as **one more entry** in `config/asset_registry.json`
(+ a `config/grafana_catalog.json`). No engine code changed - the same
`profile -> decide -> authorize -> scan -> verify` loop that runs the toy ran Grafana.

The agent fingerprinted the running version (**8.3.0**), was offered **two** CVE
candidates, and the LLM picked the applicable one:

- `grafana-cve-2021-43798` - arbitrary file read, **affects 8.0.0-8.3.0** -> **chosen**
- `grafana-cve-2020-13379` - SSRF, **affects 3.0.1-7.0.1 (not 8.x)** -> correctly rejected

Confirmation was by retrieving a **harmless planted marker file** (read-only); `/etc/passwd`
was read as a secondary proof of the real primitive on our throwaway container.

## The point: where the matching logic lives

- **The LLM path reasoned version -> applicable CVE from the catalog descriptions, with
  ZERO CVE-specific decision code in NucleiPilot.** Extending to this new target + these
  new CVEs was **adding catalog/registry entries (data)**, not writing code.
- **A rules engine could also generalize here** - a generic version-range parser fed
  machine-readable affected-version ranges (which CVE feeds and many Nuclei templates already
  carry) would select the same CVE without per-CVE code. This is **not** something only an LLM
  can do; honesty requires saying so.
- **What plausibly differs is maintenance effort and where the logic sits.** The LLM reads the
  same human-readable catalog text an analyst would, so no range-parsing / version-normalization
  pipeline has to be built and kept correct across version-scheme quirks. That is a *possible*
  convenience, not a measured advantage.

So the honest framing is: the agent **extends to a new target through configuration**, which is
real and useful. Whether that saves meaningful maintenance versus a well-built rules pipeline is
**unproven** and only starts to matter where real estates live: **many assets, a constant stream
of new templates/CVEs**.

> **Now measured (E7).** `e7_curation_note.md` tests exactly this on the real 14,104-template corpus:
> picking the version-applicable Grafana CVE for 8.3.0. Because the affected-version data is
> inconsistent free-text prose (not machine-readable), the LLM selects it at **F1 1.00** vs a tag rule
> **0.15** and a naive version parser **0.29**. One product/version, but a *measured* case where the
> LLM clearly beats the rules - the complement to the toy's honest tie.

## Honest caveats

- This is **one case**, not a benchmark. A rule *can* do version-range matching; the
  **maintenance-burden** benefit is a hypothesis to be tested at scale, not something this one
  case measures.
- Reliability of LLM reasoning across many real CVEs/targets is **not** established here -
  that is exactly what the 90-day pilot in Part 4 is designed to measure.
- All testing was against our **own local, authorized** Grafana container (localhost only),
  read-only.
