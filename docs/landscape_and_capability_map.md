# Agentic AI for Offensive Security — Landscape & Capability Map

*AMEX / Atos take-home, Part 1. Company names, products, and funding verified against
official sites and primary/reputable press as of **27 Oct 2026**. Evidence is labeled:
**[D]** documented (vendor or independent) · **[V]** vendor-reported claim, not independently
verified · **[A]** our assessment / hypothesis.*

---

## 1. Scope and definitions
- **Offensive security:** authorized, simulated attacks to find and validate weaknesses before adversaries do.
- **Agentic AI:** software that plans multi-step tasks, selects tools, acts, and adapts to results — an *observe → reason → act → reassess* loop.
- **This scan** covers firms at the intersection of **AI agents** and **offensive** security. We separate genuine **startups** from **scaled comparators**, and flag one **adjacent** market (security *for* AI) so the boundary stays honest.

---

## 2. Competitive landscape

### 2a. Genuine startups (AI-agent × offensive security)

**XBOW** — *autonomous offensive security platform.*
- **Does** [D]: AI agents test web apps/APIs like an attacker, **chain weaknesses, and report only issues they actually exploited** (each finding ships with the exploit + request/response + repro + re-test). Tagline: *"Every finding is a working exploit."*
- **Buyer** [A]: enterprise AppSec / security teams; bug-bounty-style continuous testing.
- **Money** [D]: commercial SaaS platform; ~**$237M** raised, **$1B+ valuation** (Series C, Mar 2026). Founded Jan 2024 by Oege de Moor (creator of GitHub Copilot). First AI to top HackerOne's global leaderboard.
- **Weakness** [A]: web-app/API–centric; weaker on non-web/backend/machine-to-machine assets; high autonomy concentrates trust in the model's own exploit judgments, raising oversight/false-positive governance questions at enterprise scale.

**RunSybil** — *AI offensive-security agent ("Sybil").*
- **Does** [D]: continuously tests apps + infrastructure for **exploitable** vulnerabilities, "reasoning like a skilled human researcher," running on each deployment. Lists "Autonomous Penetration Testing." Tagline: *"Attack is your best defense."*
- **Buyer** [D]: technology companies (named: Cursor, Notion, Baseten, Turbopuffer, Thinking Machines Lab).
- **Money** [D]: commercial; **$40M** (led by Khosla Ventures, Mar 2026). Founded 2023 by Ari Herbert-Voss (OpenAI's first security researcher) + Vlad Ionescu (ex-Meta offensive red-team lead).
- **Weakness** [A/V]: early-stage with a thin public track record; headline *"90% fewer false positives"* is **vendor-reported [V]**; investor (Khosla) concedes incumbents (e.g., Palo Alto) may enter the segment.

**Terra Security** — *agentic offensive-security platform (Terra Platform™).*
- **Does** [D]: continuous **agentic** pentesting across **AI systems, network infrastructure, and web apps**, with **human oversight at key decision points**; findings validated by real exploitation. Tagline: *"One Agentic Offensive Security Platform. Every Attack Vector. Continuously Validated."*
- **Buyer** [D]: enterprises incl. multiple Fortune 500; former Google CISO on its board.
- **Money** [D]: SaaS; **~$38M** total ($30M Series A led by Felicis, Sep 2025). Founded 2024 (Shahar Peled, Gal Malachi).
- **Weakness** [A]: young; human-in-the-loop by design (a strength for trust, but not "hands-off" autonomy); breadth is new and its depth per attack surface is unproven publicly.

**Hadrian** — *offensive-security platform: Atlas (exposure) + Nova (pentest).*
- **Does** [D]: **Atlas** = continuous external attack-surface discovery/monitoring (agentic AI, needs only your domain); **Nova** = on-demand **agentic pentesting** whose agents log in, map routes, and test within a customer-set scope. Tagline: *"Know your attack surface, pentest it continuously."*
- **Buyer** [D]: mid-sized and large enterprises.
- **Money** [D/A]: asset-based SaaS subscription + on-demand pentest fees [A]; ~**$13.9M** raised [D] (smaller than the others). Nova launched Mar 2026.
- **Weakness** [A]: internet-facing focus; internal-network and comprehensive business-logic testing still lean on human expertise; FP-elimination figures are **vendor-reported [V]**.

### 2b. Scaled comparators (past the startup stage; useful benchmarks)

**Horizon3.ai** — *NodeZero® autonomous pentesting.*
- **Does** [D]: autonomously runs real attack techniques against **production networks**, **chains an attack path**, prioritizes fixes, and **re-tests** to confirm them; "not a traditional scanner." Now also ships **NodeZero WebApp Pentesting**. Tagline: *"Go hack yourself. Before they do."*
- **Money/scale** [D]: ~**$428M** raised, **$2B+ valuation** (Series E, Aug 2026); 7,000+ organizations incl. NSA/CISA; ARR +120% YoY.
- **Weakness** [A]: historically network/infrastructure-centric — **web-app testing is newer and less battle-proven** (we deliberately do *not* assert a current gap, since the WebApp product is recent).

**Pentera** — *automated security / exposure validation.*
- **Does** [D]: runs attacks against live environments to show which exposures are **actually exploitable**, prioritizes, re-validates; "includes autonomous penetration testing but operates differently." Tagline: *"Validate your security controls with AI to fix what's exploitable."*
- **Money** [D/V]: quote-based annual subscription scaled by asset count; third-party estimates ~$35k (Core) to **$100k+** (full platform) per year [V].
- **Weakness** [D/A]: validates **infrastructure, not application business logic** [D]; often run **alongside** human-validated testing rather than replacing it.

### 2c. Boundary and open-source context (cited, not featured)
- **Mindgard** [D] — *"Attack-Led Security for AI Systems & Agents."* This is **security *for* AI** (red-teaming models/agents), a **distinct market** from *AI for offensive security*. ~$42M raised; Lancaster University spin-out. Cited to mark the boundary.
- **Open-source agentic tools** — **PentestGPT** (first-gen interactive LLM assistant), **Strix** (autonomous agents, PoC-verified, CI-friendly), **PentAGI** (MIT, multi-agent orchestrator+researcher+executor in Docker, 20+ tools incl. Nmap/Metasploit/sqlmap, local models via Ollama). These show the OSS frontier is **maximal autonomy over broad toolchains**. **Nuclei** (ProjectDiscovery) is the trusted template scanner our PoC extends.

---

## 3. Capability map

Legend: **Y** present · **P** partial · **Ltd** limited · **?** unclear from public info · **No** out of scope. Assessments [A] from public descriptions; verify against product docs.

| Capability | XBOW | RunSybil | Terra | Hadrian | Horizon3 | Pentera | **NucleiPilot (ours)** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Recon / attack-surface discovery | Y | P | P | **Y** | Y | Y | No |
| Vulnerability scanning | Y | Y | Y | Y | Y | Y | **Y** (Nuclei) |
| Autonomous exploitation / PoC validation | **Y** | **Y** | **Y** | Y | Y | Y | No (by design) |
| Attack-path chaining | Y | ? | P | P | **Y** | Y | No |
| Adaptive follow-up / test selection | Y | Y | Y | P | Y | P | **Y** |
| Business-*context*-aware triage | ? | ? | ? | ? | P | ? | **Y** |
| Human-in-the-loop / oversight | Ltd | Ltd | **Y** | **Y** | Ltd | Ltd | P* |
| Transparent, auditable decision trace | P | P | P | P | P | P | **Y** |
| Controlled vs non-AI baselines (published) | ? | ? | ? | ? | ? | ? | **Y** |
| Continuous (vs point-in-time) | Y | Y | Y | Y | Y | Y | P |

The right-most columns are where the field is **thin and where our PoC concentrates**: context-aware triage, transparent/auditable traces, and *published evidence against non-AI baselines*.

**Read the matrix as capability *dimensions and design intent*, not maturity or scale.** NucleiPilot's cells reflect a **PoC** (toy lab + one real CVE, two issue classes), not a production platform like XBOW or Horizon3. `P*` on human-in-the-loop means the review gate is *specified in the architecture* (Part 3), not yet a built UI. And "transparent decision trace" separates *finding* transparency (XBOW ships the exploit + request/response) from *decision-process* transparency (NucleiPilot logs **why** it chose each action) — the latter is the thin spot across the field.

---

## 4. Where an agentic layer adds value, by workflow stage

| Stage | What the agent adds | Representative players |
|---|---|---|
| Recon / attack-surface | Correlate OSINT, infer asset relationships, prioritize | Hadrian (Atlas), XBOW |
| Scanning / discovery | Choose relevant checks, interpret results, cut noise | Nuclei, **NucleiPilot** |
| Exploitation / **validation** | Chain findings, build **PoC** to confirm → fewer false positives | XBOW, RunSybil, Terra, Strix, PentAGI |
| Post-exploitation / attack-path | Reason about lateral movement & privilege escalation | Horizon3 NodeZero |
| **Triage / prioritization** | **Business-context-aware** severity, dedup, next-action choice | **NucleiPilot**, Hadrian |
| Reporting / re-test | Narrative + remediation guidance + confirm the fix | NodeZero, most |

---

## 5. Capabilities that define "agentic offensive security"
Grounded in the above, an offering is "agentic" (not just automated) when it has:
1. **Autonomous multi-step planning** — an observe→decide→act→reassess loop, not a fixed script.
2. **Tool orchestration / selection** — chooses *which* check/exploit to run next.
3. **Evidence-based validation via real exploitation (PoC)** — proof, not signature-only matches (the industry's core FP-reduction claim).
4. **Adaptive, context-aware test selection** — next action driven by accumulated evidence and target context.
5. **Attack-path chaining** — combining individual weaknesses into an exploit path.
6. **Continuous operation** — not point-in-time engagements.
7. **Human-in-the-loop + oversight** — increasingly table-stakes for enterprise trust (Terra, Hadrian lead here).
8. **Scope / safety controls** — customer-set scope, bounded actions.
9. **Reporting, remediation, and re-test** — close the loop and confirm fixes.

**Two senses of "validation" — and where NucleiPilot deliberately sits.** In the category above,
*validation* means **proving exploitability with a working PoC** (traits 3 and 5). NucleiPilot does
**not** do this. It occupies a narrower, complementary slice: an agentic **triage and
follow-up-orchestration** layer that has the planning traits (1, 2, 4, 7, 8) but treats "validation"
as *running an authorized follow-up template to confirm an indicator*, not as exploitation. So
NucleiPilot is agentic in its **decision loop**, but is **not** a full agentic *exploitation* platform —
and for a regulated buyer, that restraint is the selling point, not a gap.

---

## 6. The unclaimed ground (and where NucleiPilot fits)
The market splits into **closed full-stack autonomous platforms** (XBOW, RunSybil, NodeZero) and **maximally-autonomous OSS multi-agent systems** (PentAGI, Strix) wielding heavy toolchains (Metasploit, sqlmap). Four things stay thin:

1. **A transparent, policy-constrained agentic *layer* on a trusted open-source scanner** — not a new black-box exploitation engine. Most offerings are either closed-commercial or maximally-autonomous OSS; few sit in between with explicit, inspectable action controls.
2. **Published, controlled evidence** that the agent beats non-AI baselines. Vendors *claim* value (e.g., "90% fewer false positives" [V]); almost none publish a fixed-vs-rule-vs-LLM comparison with independent ground truth. **We do.**
3. **Governance for regulated orgs (e.g., a bank):** target allowlists, template allowlists, human approval, deterministic safety rails, full audit trace. Autonomous-Metasploit-in-Docker cannot offer this; commercial platforms vary and are opaque.
4. **Business-*context*-aware prioritization under budget** — most tools prioritize by CVSS/severity; our flip-test shows context-driven choice (6/6).

**NucleiPilot's honest niche:** *a lightweight, transparent, auditable agentic triage/follow-up layer on top of a trusted open-source scanner (Nuclei), with independent action controls and explicit benchmark comparisons, for approved internal sandboxes.* We do **not** claim to out-autonomy XBOW; we claim **transparency + evidence + governance** — the dimensions the leaders under-serve, and the ones a bank's security function cares about most.

---

## Sources
- XBOW — [official site](https://xbow.com) · [SecurityWeek: $120M / $1B](https://www.securityweek.com/autonomous-offensive-security-firm-xbow-raises-120m-at-1b-valuation/) · [HelpNetSecurity: $75M](https://www.helpnetsecurity.com/2025/06/25/xbow-ai-funding/)
- RunSybil — [official site](https://www.runsybil.com) · [Fortune: $40M / founders](https://fortune.com/2026/03/18/exclusive-ai-cybersecurity-startup-runsybil-founded-by-openais-first-security-hire-raises-40-million-led-by-khosla-ventures)
- Terra Security — [official site](https://www.terra.security) · [Terra: $30M Series A](https://www.terra.security/blog/terra-security-raises-30m-series-a-to-redefine-penetration-testing-with-agentic-ai)
- Hadrian — [official site](https://hadrian.io) · [Dealroom: Nova launch](https://app.dealroom.co/news/feed/hadrian-launches-nova-autonomous-pentesting-solution-that-replicates-elite-hackers-at-machine-speed)
- Horizon3.ai — [official site](https://horizon3.ai) · [SiliconANGLE: $250M / $2B](https://siliconangle.com/2026/08/03/horizon3-ai-raises-250m-2b-plus-valuation-autonomous-pentesting/)
- Pentera — [official site](https://pentera.io) · [Synack: pricing analysis](https://www.synack.com/?p=27334)
- Mindgard — [official site](https://mindgard.ai) · [SecurityWeek: $30M](https://www.securityweek.com/mindgard-raises-30-million-to-protect-ai-systems/)
- Open-source — [PentAGI (LinuxToday)](https://www.linuxtoday.com/blog/pentagi-open-source-autonomous-ai-penetration-testing-system/) · [SOCRadar: top AI pentest tools](https://socradar.io/blog/top-10-ai-pentest-tools-2025/)
