"""Thin wrapper around the herdr CLI's JSON envelope."""

import json
import subprocess


class HerdrError(RuntimeError):
    pass


def herdr(*args: str) -> dict:
    result = subprocess.run(
        ["herdr", *args], text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise HerdrError(
            f"herdr {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}"
        )
    if not result.stdout.strip():
        return {}
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise HerdrError(
            f"herdr {' '.join(args)} returned invalid JSON: {result.stdout.strip()}"
        ) from error
    return envelope.get("result", {})
