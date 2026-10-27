# NucleiPilot — Failure & Safety Checks

Deterministic demonstrations (no Nuclei, no API) that the harness fails safe.

| Check | Result | Detail |
|---|---|---|
| Out-of-scope target rejected | PASS | ScopeError raised before any scan: target host 'example.com' is not in approved scope ['127.0.0.1', 'localhost']; refusing to scan |
| Invented template id blocked | PASS | guard blocked it=True; fabricated template executed=False |
| Malformed JSON -> safe stop | PASS | stopped safely=True; any validation executed=False; assessment={'admin': 'UNVERIFIED', 'debug': 'UNVERIFIED'} |
| STOP correct on clean target | PASS | assessment={'admin': 'CLEAN', 'debug': 'CLEAN'}; templates_run=2 (2 discovery, 0 follow-up) |
