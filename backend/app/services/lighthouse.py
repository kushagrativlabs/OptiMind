import asyncio
import json
import os
from pathlib import Path


LIGHTHOUSE_MAX_PAGES = max(1, int(os.getenv("OPTIMIND_LIGHTHOUSE_MAX_PAGES", "10")))
LIGHTHOUSE_TIMEOUT_SECONDS = max(
    30, int(os.getenv("OPTIMIND_LIGHTHOUSE_TIMEOUT_SECONDS", "90"))
)
SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "run-lighthouse.mjs"


class LighthouseError(Exception):
    pass


async def run_lighthouse(url: str) -> dict[str, object]:
    """Run a local, read-only Lighthouse audit for one public URL."""
    try:
        process = await asyncio.create_subprocess_exec(
            "node",
            str(SCRIPT_PATH),
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=LIGHTHOUSE_TIMEOUT_SECONDS
        )
    except (OSError, asyncio.TimeoutError) as exc:
        raise LighthouseError("Local Lighthouse could not run.") from exc
    if process.returncode != 0:
        detail = stderr.decode(errors="replace").strip()
        raise LighthouseError(detail or "Local Lighthouse returned an error.")
    try:
        result = json.loads(stdout.decode())
    except (TypeError, ValueError) as exc:
        raise LighthouseError("Local Lighthouse returned invalid results.") from exc
    if not isinstance(result, dict):
        raise LighthouseError("Local Lighthouse returned invalid results.")
    return result
