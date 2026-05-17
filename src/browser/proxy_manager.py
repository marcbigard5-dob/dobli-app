import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Proxy:
    host: str
    port: int
    username: str = ""
    password: str = ""
    protocol: str = "http"
    country: str = ""
    latency_ms: float = 0.0
    fail_count: int = 0
    is_active: bool = True

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    def __hash__(self) -> int:
        return hash((self.host, self.port, self.protocol))


class ProxyManager:
    def __init__(self):
        self._proxies: list[Proxy] = []
        self._assigned: dict[str, Proxy] = {}

    def load_from_file(self, path: str):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                if len(parts) == 2:
                    self._proxies.append(Proxy(host=parts[0], port=int(parts[1])))
                elif len(parts) == 4:
                    self._proxies.append(
                        Proxy(
                            host=parts[0],
                            port=int(parts[1]),
                            username=parts[2],
                            password=parts[3],
                        )
                    )
                elif len(parts) >= 5:
                    self._proxies.append(
                        Proxy(
                            protocol=parts[0],
                            host=parts[1],
                            port=int(parts[2]),
                            username=parts[3],
                            password=parts[4],
                        )
                    )

    def add_proxy(self, proxy: Proxy):
        self._proxies.append(proxy)

    def assign(self, agent_id: str) -> Optional[Proxy]:
        available = [p for p in self._proxies if p.is_active and p not in self._assigned.values()]
        if not available:
            return None
        proxy = random.choice(available)
        self._assigned[agent_id] = proxy
        return proxy

    def release(self, agent_id: str):
        self._assigned.pop(agent_id, None)

    def get_for_agent(self, agent_id: str) -> Optional[Proxy]:
        return self._assigned.get(agent_id)

    def mark_failed(self, proxy: Proxy):
        proxy.fail_count += 1
        if proxy.fail_count >= 3:
            proxy.is_active = False

    @property
    def available_count(self) -> int:
        return sum(1 for p in self._proxies if p.is_active and p not in self._assigned.values())

    @property
    def total_count(self) -> int:
        return len(self._proxies)
