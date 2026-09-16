"""Optional data.gov.in fallback-key configurator for FarmDirect FINAL V15.

AGMARKNET 2.0 is the primary keyless source. This helper is only needed if the
user also wants the legacy data.gov.in source available as a secondary fallback.
"""
from __future__ import annotations

from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"
KEY = "DATA_GOV_IN_API_KEY"


def main():
    print("FarmDirect FINAL V15 — Resilient Official Mandi Sync")
    print("✓ AGMARKNET 2.0 primary sync requires NO API key.")
    print("Optional: paste a data.gov.in key to enable the legacy secondary fallback.")
    value = getpass("Optional data.gov.in API key (Enter to skip): ").strip()
    if not value:
        print("No key saved. FarmDirect will use AGMARKNET 2.0 + SQLite cache.")
        return
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    out=[]; replaced=False
    for line in lines:
        if line.strip().startswith(KEY + "="):
            out.append(f"{KEY}={value}"); replaced=True
        else:
            out.append(line)
    if not replaced:
        if out and out[-1].strip(): out.append("")
        out.extend(["# Optional legacy data.gov.in fallback", f"{KEY}={value}"])
    ENV.write_text("\n".join(out)+"\n",encoding="utf-8")
    print("✓ Optional fallback key saved. Restart FarmDirect.")


if __name__ == "__main__":
    main()
