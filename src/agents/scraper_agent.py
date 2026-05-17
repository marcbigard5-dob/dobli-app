import logging
from typing import Any

from src.agents.base_agent import BaseAgent, Task


class ScraperAgent(BaseAgent):
    async def execute(self, task: Task) -> Any:
        self.logger.info(f"Scraping: {task.action} with params={task.params}")

        if not self._browser:
            raise RuntimeError("No browser attached to scraper agent")

        url = task.params.get("url")
        if not url:
            raise ValueError("Missing 'url' in task params")

        selector = task.params.get("selector", "body")

        try:
            import nodriver as nd
            if isinstance(self._browser, nd.Browser):
                page = await self._browser.get(url)
                await page.wait_for(selector)
                content = await page.evaluate(f"document.querySelector('{selector}')?.innerText")
                return {"url": url, "content": content, "status": "success"}
        except ImportError:
            pass

        try:
            from playwright.async_api import Page
            if isinstance(self._browser, Page):
                await self._browser.goto(url)
                await self._browser.wait_for_selector(selector)
                content = await self._browser.inner_text(selector)
                return {"url": url, "content": content, "status": "success"}
        except (ImportError, TypeError):
            pass

        self.logger.info(f"Falling back to HTTP fetch for {url}")

        try:
            import aiohttp
            headers = {"User-Agent": self.config.user_agent}
            proxy_url = self.config.proxy.url if self.config.proxy else None
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, proxy=proxy_url) as resp:
                    html = await resp.text()
                    return {"url": url, "status_code": resp.status, "content_length": len(html)}
        except ImportError:
            pass

        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": self.config.user_agent})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            return {"url": url, "status_code": resp.status, "content_length": len(html)}
