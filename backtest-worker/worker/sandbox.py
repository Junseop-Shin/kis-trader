"""
Execute user-provided Python strategy code in ephemeral Docker container.
Container options: --network none --memory 512m --cpus 1 --read-only --rm
"""
import json
import logging
import os
import tempfile

import docker

logger = logging.getLogger(__name__)


def run_custom_code(code: str, prices_json: str, params: dict) -> dict:
    """
    1. Write user code + harness to temp file; prices passed via JSON file (not f-string)
    2. Run in Docker container with restrictions
    3. Capture output and return results (signal list)
    """
    client = docker.from_env()

    # prices_json is written to a separate file — never interpolated into Python source
    # to prevent triple-quote injection attacks
    harness = f'''
import pandas as pd
import numpy as np
import json
import sys

try:
    import pandas_ta as ta
except ImportError:
    ta = None

with open("/code/prices.json") as _f:
    prices = pd.DataFrame(json.load(_f))
prices["date"] = pd.to_datetime(prices["date"])
prices = prices.set_index("date").sort_index()

with open("/code/params.json") as _f:
    params = json.load(_f)

# === USER CODE START ===
{code}
# === USER CODE END ===

# User must define: generate_signals(df, params) -> pd.Series (1=BUY, -1=SELL, 0=HOLD)
if "generate_signals" not in dir():
    print(json.dumps({{"error": "Must define generate_signals(df, params)"}}))
    sys.exit(1)

signals = generate_signals(prices, params)
result = signals.fillna(0).astype(int).tolist()
print(json.dumps(result))
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "strategy.py"), "w") as f:
            f.write(harness)
        # Write data files separately — never interpolated into Python source
        with open(os.path.join(tmpdir, "prices.json"), "w") as f:
            f.write(prices_json)
        with open(os.path.join(tmpdir, "params.json"), "w") as f:
            json.dump(params, f)

        try:
            result = client.containers.run(
                image="python:3.12-slim",
                command=["python", "/code/strategy.py"],
                volumes={tmpdir: {"bind": "/code", "mode": "ro"}},
                network_disabled=True,
                mem_limit="512m",
                cpu_period=100000,
                cpu_quota=100000,
                pids_limit=64,
                user="nobody",
                read_only=True,
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                remove=True,
                stdout=True,
                stderr=True,
            )
            output = result.decode("utf-8").strip()

            # Check if output is an error dict
            try:
                parsed = json.loads(output)
                if isinstance(parsed, dict) and "error" in parsed:
                    return {"success": False, "error": parsed["error"]}
                return {"success": True, "signals": parsed}
            except json.JSONDecodeError:
                return {"success": False, "error": f"Invalid output: {output[:500]}"}

        except docker.errors.ContainerError as e:
            stderr = e.stderr.decode("utf-8") if e.stderr else str(e)
            logger.warning(f"Custom code container error: {stderr}")
            return {"success": False, "error": stderr[:1000]}
        except Exception as e:
            logger.exception("Custom code sandbox error")
            return {"success": False, "error": str(e)[:1000]}
