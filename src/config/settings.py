import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ProxyConfig:
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    protocol: str = "http"

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class AgentConfig:
    agent_id: str
    proxy: Optional[ProxyConfig] = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    viewport_width: int = 1920
    viewport_height: int = 1080
    timezone: str = "UTC"
    locale: str = "en-US"
    data_dir: str = ""
    max_concurrent_tasks: int = 3
    task_timeout: int = 300

    def __post_init__(self):
        if not self.data_dir:
            self.data_dir = os.path.join("agents_data", self.agent_id)
        os.makedirs(self.data_dir, exist_ok=True)


@dataclass
class Settings:
    db_path: str = "orchestrator.db"
    max_agents: int = 10
    task_queue_size: int = 100
    heartbeat_interval: int = 30
    browser_type: str = "chromium"
    headless: bool = True
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    proxies_file: str = "proxies.txt"

    def load_agents_from_json(self, path: str):
        with open(path) as f:
            raw = json.load(f)
        for item in raw:
            proxy = None
            if item.get("proxy"):
                proxy = ProxyConfig(**item["proxy"])
            cfg = AgentConfig(agent_id=item["agent_id"], proxy=proxy)
            self.agents[cfg.agent_id] = cfg

    @classmethod
    def from_env(cls) -> "Settings":
        inst = cls()
        if os.getenv("MAX_AGENTS"):
            inst.max_agents = int(os.getenv("MAX_AGENTS"))
        if os.getenv("BROWSER_TYPE"):
            inst.browser_type = os.getenv("BROWSER_TYPE")
        if os.getenv("HEADLESS", "true").lower() == "false":
            inst.headless = False
        return inst


settings = Settings.from_env()
