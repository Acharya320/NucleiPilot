# E7 - Corpus curation: the one case where the LLM is clearly needed

*Where E1-E3 found the LLM only **ties** a rule, E7 finds a task on the **real** corpus where
it clearly **wins**. Read with `curation_summary.md` and `curation_results.json`.*

## The question

The toy experiment is small and fully labelled, so a rule ties the LLM on prioritization. The
honest follow-up: **does the LLM earn its place once you scale to the real 14,104-template
corpus?** Concretely - given a detected target (**Grafana 8.3.0**) and the Grafana-tagged CVE
templates a fair `-tags grafana` rule gathers, **which ones actually apply to 8.3.0?**

The candidate pool (`config/curation_corpus.json`) is **12 Grafana-tagged CVE templates**,
mechanically extracted from the real corpus by `scripts/build_curation_fixture.py` (not hand-picked).
Ground truth (`config/curation_ground_truth.json`): **only CVE-2021-43798 applies** to 8.3.0 - and
that is independently confirmed on the live container (`grafana_demo.json`).

## Result (measured, 3 LLM runs, stable)

| Method | Precision | Recall | F1 |
|---|---:|---:|---:|
| TAG rule (runs every grafana-tagged CVE) | 0.08 | 1.00 | 0.15 |
| VERSION rule (naive range parser) | 0.17 | 1.00 | 0.29 |
| **LLM** | **1.00** | **1.00** | **1.00** |

- **TAG rule** cannot read versions, so it "selects" all 12 - it would run **11 non-applicable
  checks** to find the 1 that matters.
- **VERSION rule** (treat the highest version mentioned as the upper bound) handles the explicit
  ranges but is fooled by the messy ones - it wrongly includes CVE-2025-3415 ("below or equals to
  12.0.1", which *literally* contains 8.3.0) and the recent CVEs whose descriptions carry no parseable
  range.
- **LLM** reads each description and selects exactly **CVE-2021-43798**, every run. Its stated reasons
  are coherent per CVE ("target newer than affected range" for the old ones, "within range" for
  43798, "older than affected range" for the 2024/2025 ones).

## Why this is a real LLM advantage (not a rigged one)

The affected-version information in real templates is **inconsistent free-text prose**: "8.0.0-beta1
through 8.3.0", "3.0.1-7.0.1", "up to 7.5.11 **and** 8.1.5" (dual-branch), "below or equals to
12.0.1" (misleading). There is **no machine-readable affected-range field**. Matching the target
against that prose is a reading/understanding task - exactly where keyword/tag rules and simple
parsers break and an LLM does well. This directly tests, and answers, the caveat in
`e6_generalization_note.md`: *"a parser fed machine-readable ranges could compete"* - the ranges are
**not** machine-readable, so in practice you either keep hand-coding parser special-cases or you read
the text (LLM).

## Honest limits (do not overclaim)

- **One product, one version.** This is a concrete demonstration that the gap is real, **not** a
  measurement of accuracy across many products/CVEs. That breadth is exactly what the Part 4 pilot
  must test.
- **Part of the LLM's edge is world knowledge, not just reading.** For the 2024/2025 CVEs it inferred
  "newer feature -> does not affect an older build" from its training priors, not from an explicit
  range in the text. That is a genuine advantage a parser lacks - but it also means the LLM can be
  **wrong when its priors are wrong**, so it is not infallible.
- **A sufficiently elaborate parser could approach this** on the explicit cases. The LLM's practical
  win is avoiding an open-ended, ever-growing parser for every new prose format - a maintenance
  argument, now shown with numbers on real data.
- **The LLM is a selector, not the authority.** Even here it only *proposes* which CVE to check;
  NucleiPilot still **validates by scanning** and lets code assign the verdict (E4 confirmed the
  selected CVE-2021-43798 on the live 8.3.0 container). A wrong selection wastes a scan; it cannot
  fabricate a finding.

## The combined, honest headline

> On the **small, clean toy**, the LLM **ties** a tuned rule - so for that task, you do not need it.
> On the **large, messy real corpus**, picking the version-applicable check is a reading problem the
> rule cannot do, and the LLM **clearly wins (F1 1.00 vs 0.15 / 0.29)**. The value of the agent scales
> with the **size and messiness** of the template space - which is the real-world condition.
