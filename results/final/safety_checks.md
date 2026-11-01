# NucleiPilot - Failure & Safety Checks (E4)

Deterministic demonstrations (no Nuclei, no API) that the engine fails safe: the model proposes, but code authorizes, bounds, and scopes every action.

| Check | Result | Detail |
|---|---|---|
| Out-of-scope target rejected | PASS | assert_in_scope raised=True; engine refused out-of-scope asset before scanning=True |
| Invented template id blocked | PASS | gate blocked it=True; fabricated template executed=False; rejections=1 |
| Malformed LLM JSON -> safe stop | PASS | stopped safely=True; any validation executed=False; confirmed findings=0 |
| Budget enforced (no over-budget execution) | PASS | eligible validations=4, budget=2, executed=2 (the remaining 2 stay UNVERIFIED -- the loop never exceeds the budget) |
