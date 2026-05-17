import asyncio
import logging
from typing import Optional

from src.config.settings import AgentConfig, settings


class _MockPage:
    async def goto(self, url):
        pass

    async def wait_for_selector(self, selector):
        pass

    async def inner_text(self, selector):
        return ""

    async def evaluate(self, expr):
        return None

    async def close(self):
        pass


class _MockBrowser:
    async def get(self, url):
        return _MockPage()

    async def new_context(self, **kwargs):
        return _MockPage()

    async def close(self):
        pass


class BrowserManager:
    def __init__(self):
        self._browsers: dict[str, object] = {}
        self._contexts: dict[str, object] = {}
        self._lock = asyncio.Lock()
        self._browser_available = True
        self.logger = logging.getLogger("browser.manager")

    async def launch_browser(self):
        for lib_name, import_path in [("nodriver", "nodriver"), ("playwright", "playwright.async_api")]:
            try:
                __import__(lib_name)
                if lib_name == "nodriver":
                    from nodriver import start
                    return await start(headless=settings.headless)
                else:
                    from playwright.async_api import async_playwright
                    p = await async_playwright().start()
                    return await p.chromium.launch(headless=settings.headless)
            except ImportError:
                continue

        self._browser_available = False
        self.logger.warning("No browser automation library found (install playwright or nodriver)")
        return _MockBrowser()

    async def create_context(self, agent_config: AgentConfig, browser) -> object:
        if isinstance(browser, _MockBrowser):
            return _MockPage()

        try:
            import nodriver as nd
            if isinstance(browser, nd.Browser):
                return browser
        except (ImportError, TypeError):
            pass

        try:
            from playwright.async_api import Browser as PWBrowser
            if isinstance(browser, PWBrowser):
                proxy = agent_config.proxy
                proxy_settings = {"server": proxy.url} if proxy else None
                return await browser.new_context(
                    user_agent=agent_config.user_agent,
                    viewport={"width": agent_config.viewport_width, "height": agent_config.viewport_height},
                    timezone_id=agent_config.timezone,
                    locale=agent_config.locale,
                    proxy=proxy_settings,
                    storage_state=agent_config.data_dir,
                )
        except (ImportError, TypeError):
            pass

        return browser

    async def get_or_create_browser(self, agent_id: str) -> object:
        async with self._lock:
            if agent_id not in self._browsers:
                browser = await self.launch_browser()
                self._browsers[agent_id] = browser
            return self._browsers[agent_id]

    async def assign_context(self, agent_config: AgentConfig) -> object:
        browser = await self.get_or_create_browser(agent_config.agent_id)
        context = await self.create_context(agent_config, browser)
        self._contexts[agent_config.agent_id] = context
        return context

    async def close_context(self, agent_id: str):
        context = self._contexts.pop(agent_id, None)
        if context:
            try:
                await context.close()
            except Exception:
                pass

    async def close_browser(self, agent_id: str):
        await self.close_context(agent_id)
        browser = self._browsers.pop(agent_id, None)
        if browser:
            try:
                await browser.close()
            except Exception:
                pass

    async def shutdown_all(self):
        for agent_id in list(self._browsers.keys()):
            await self.close_browser(agent_id)
