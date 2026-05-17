#!/usr/bin/env python3
"""
Multi-Agent Task Automation System
Master entry point for orchestrating autonomous marketing agents.
"""

import asyncio
import logging
import sys

from src.agents import Task
from src.config.settings import AgentConfig, ProxyConfig, settings
from src.orchestrator import MasterOrchestrator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


async def demo():
    orchestrator = MasterOrchestrator()

    agent_1 = AgentConfig(
        agent_id="scraper_01",
        proxy=ProxyConfig(host="127.0.0.1", port=8080),
        timezone="America/New_York",
        locale="en-US",
    )
    agent_2 = AgentConfig(
        agent_id="analyst_01",
        timezone="Europe/London",
        locale="en-GB",
    )
    agent_3 = AgentConfig(
        agent_id="publisher_01",
        timezone="Asia/Dubai",
        locale="ar-AE",
    )

    orchestrator.add_agent(agent_1)
    orchestrator.add_agent(agent_2)
    orchestrator.add_agent(agent_3)

    tasks = [
        Task(
            id="scrape-1",
            agent_type="scraper",
            action="extract_content",
            params={"url": "https://example.com", "selector": "h1"},
            priority=1,
        ),
        Task(
            id="analyze-1",
            agent_type="analyst",
            action="keywords",
            params={"data": {"text": "Great product with amazing quality and excellent service"}},
            priority=2,
        ),
        Task(
            id="publish-1",
            agent_type="publisher",
            action="post_content",
            params={
                "content": "Check out our latest product!",
                "platform": "twitter",
            },
            priority=0,
        ),
    ]

    logger.info("=== Starting Multi-Agent Orchestrator Demo ===")
    await orchestrator.run_batch(tasks, concurrency=3)

    logger.info("\n=== Agent Stats ===")
    for aid, stats in orchestrator.get_agent_stats().items():
        logger.info(f"  {aid}: {stats}")

    logger.info("\n=== Results ===")
    for aid, results in orchestrator.get_results().items():
        for t in results:
            status = "OK" if t.result else f"FAIL: {t.error}"
            logger.info(f"  [{status}] {t.id} -> {t.result}")

    await orchestrator.stop()
    logger.info("=== Demo Complete ===")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo())
    else:
        print("Usage: python main.py demo")
        print("\nEnvironment variables:")
        print("  MAX_AGENTS  - Max concurrent agents (default: 10)")
        print("  HEADLESS    - Run browser headless (default: true)")
        print("  BROWSER_TYPE - Browser engine: chromium/firefox/webkit")
