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

## The point: data vs code

- **The LLM path reasoned version -> applicable CVE from the catalog descriptions, with
  ZERO CVE-specific decision code in NucleiPilot.** Extending to this new target + these
  new CVEs was **adding catalog/registry entries (data)**, not writing code.
- **To make a rule do the same**, you hand-write version-range logic per CVE: parse
  `8.0.0-8.3.0`, test `8.3.0 in range`; parse `3.0.1-7.0.1`, exclude; and repeat the
  pattern for every new CVE and every version-scheme quirk. That is **explicit code that
  grows with coverage**.

So the agent's durable value is **generalization without hand-written rules**: new targets
and new CVEs plug in as data. On a small, fully-labeled toy this advantage is invisible
(a 5-line rule ties the LLM - see §7); it starts to matter exactly where real estates
live: **many assets, a constant stream of new templates/CVEs**.

## Honest caveats

- This is **one case**, not a benchmark. A rule *can* do version-range matching; the claim
  is about **maintenance burden**, which only pays off at scale.
- Reliability of LLM reasoning across many real CVEs/targets is **not** established here -
  that is exactly what the 90-day pilot in `docs/build_decision.md` is designed to measure.
- All testing was against our **own local, authorized** Grafana container (localhost only),
  read-only.
