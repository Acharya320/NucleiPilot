"""Scope-enforcing wrapper around the real Nuclei binary.

Responsibilities (and safety properties):
  * refuse any target that is not an approved localhost address (SCOPE GUARD)
  * run exactly ONE template at a time (the planner chooses which)
  * build a FIXED command line -- callers cannot inject arbitrary nuclei flags
  * parse Nuclei's JSONL output into a small, stable `ScanResult`

Nothing here lets the model (or any caller) run free-form commands or reach
non-localhost hosts. Those limits live in code, not in a prompt.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import yaml

# --- Scope allowlist: localhost only --------------------------------------
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}

# Where `go install` placed the binary on this machine; overridable.
DEFAULT_NUCLEI_BIN = r"C:\Users\SUDIPTA\go\bin\nuclei.exe"


class ScopeError(Exception):
    """Raised when a target is outside the approved scope."""


def assert_in_scope(target: str) -> None:
    """Hard scope check. Raises ScopeError for anything but localhost."""
    host = urlparse(target).hostname
    if host not in ALLOWED_HOSTS:
        raise ScopeError(
            f"target host {host!r} is not in approved scope {sorted(ALLOWED_HOSTS)}; refusing to scan"
        )


def _resolve_bin(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    found = shutil.which("nuclei")
    if found:
        return found
    env = os.getenv("NUCLEIPILOT_NUCLEI_BIN")
    if env and os.path.exists(env):
        return env
    if os.path.exists(DEFAULT_NUCLEI_BIN):
        return DEFAULT_NUCLEI_BIN
    raise FileNotFoundError(
        "nuclei binary not found. Put it on PATH, set NUCLEIPILOT_NUCLEI_BIN, "
        "or pass --bin / nuclei_bin=..."
    )


def _template_id(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data.get("id") or os.path.splitext(os.path.basename(path))[0]
    except Exception:
        return os.path.splitext(os.path.basename(path))[0]


@dataclass
class ScanResult:
    template_id: str
    target: str
    matched: bool
    matched_at: str | None = None
    name: str | None = None
    severity: str | None = None
    matcher_name: str | None = None
    extracted: list = field(default_factory=list)
    raw: list = field(default_factory=list)   # raw nuclei JSONL objects
    error: str | None = None
    duration_s: float | None = None

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        return d


def run_template(
    target: str,
    template_path: str,
    *,
    nuclei_bin: str | None = None,
    rate_limit: int = 20,
    concurrency: int = 1,
    timeout: int = 10,
    overall_timeout: int = 60,
) -> ScanResult:
    """Run one template against one in-scope target and return a ScanResult."""
    assert_in_scope(target)                      # scope guard first, always
    bin_path = _resolve_bin(nuclei_bin)
    tid = _template_id(template_path)

    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.jsonl")
        cmd = [
            bin_path,
            "-u", target,
            "-t", template_path,
            "-jsonl-export", out,
            "-silent", "-nc", "-duc", "-ni",   # -ni: no interactsh -> no outbound OAST calls
            "-rl", str(rate_limit),
            "-c", str(concurrency),
            "-timeout", str(timeout),
        ]
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=overall_timeout
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                template_id=tid, target=target, matched=False,
                error=f"nuclei timed out after {overall_timeout}s",
                duration_s=float(overall_timeout),
            )
        dur = time.monotonic() - start

        objs: list[dict] = []
        if os.path.exists(out):
            with open(out, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        objs.append(json.loads(line))

    if not objs:
        err = None
        if proc.returncode != 0:
            err = (proc.stderr or "").strip() or f"nuclei exited {proc.returncode}"
        return ScanResult(
            template_id=tid, target=target, matched=False,
            raw=[], duration_s=dur, error=err,
        )

    first = objs[0]
    info = first.get("info", {})
    return ScanResult(
        template_id=first.get("template-id", tid),
        target=target,
        matched=True,
        matched_at=first.get("matched-at") or first.get("host"),
        name=info.get("name"),
        severity=info.get("severity"),
        matcher_name=first.get("matcher-name"),
        extracted=first.get("extracted-results", []),
        raw=objs,
        duration_s=dur,
    )


def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Run one Nuclei template against a localhost target.")
    ap.add_argument("target")
    ap.add_argument("template_path")
    ap.add_argument("--bin", default=None, help="path to nuclei binary")
    args = ap.parse_args(argv)
    res = run_template(args.target, args.template_path, nuclei_bin=args.bin)
    print(json.dumps(res.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
