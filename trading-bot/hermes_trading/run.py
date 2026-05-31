"""Entrypoint — runs the trading loop and web dashboard concurrently."""
import argparse
import asyncio
import logging
import os
from pathlib import Path

import uvicorn
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)


async def _run_server():
    from hermes_trading.server import app
    port = int(os.getenv("PORT", "8080"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def _main(asset: str):
    from hermes_trading.loop import run_loop
    await asyncio.gather(
        run_loop(asset),
        _run_server(),
    )


def main() -> None:
    state_dir = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
    goal_path = state_dir / "goal.yaml"

    with open(goal_path) as f:
        goal = yaml.safe_load(f) or {}

    parser = argparse.ArgumentParser(description="hermes-trading worker")
    parser.add_argument("--asset", default=goal.get("asset", "BTC/USDT"))
    args = parser.parse_args()

    asyncio.run(_main(args.asset))


if __name__ == "__main__":
    main()
