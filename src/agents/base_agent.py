import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from src.config.settings import AgentConfig


class AgentStatus(Enum):
    IDLE = auto()
    BUSY = auto()
    ERROR = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class Task:
    id: str
    agent_type: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout: int = 300
    max_retries: int = 3
    retry_count: int = 0
    result: Any = None
    error: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return self.retry_count >= self.max_retries


class BaseAgent(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"agent.{config.agent_id}")
        self._session_id: Optional[str] = None
        self._browser = None
        self._tasks_completed = 0
        self._tasks_failed = 0

    @abstractmethod
    async def execute(self, task: Task) -> Any:
        ...

    async def run(self, task: Task) -> Any:
        self.status = AgentStatus.BUSY
        try:
            result = await asyncio.wait_for(
                self.execute(task),
                timeout=task.timeout,
            )
            self._tasks_completed += 1
            return result
        except asyncio.TimeoutError:
            self._tasks_failed += 1
            task.error = "Task timed out"
            raise
        except Exception as e:
            self._tasks_failed += 1
            task.error = str(e)
            raise
        finally:
            if self._tasks_failed > 0 and self._tasks_completed == 0:
                self.status = AgentStatus.ERROR
            else:
                self.status = AgentStatus.IDLE

    async def attach_browser(self, browser):
        self._browser = browser

    async def detach_browser(self):
        if self._browser:
            await self._browser.close()
        self._browser = None

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str):
        self._session_id = value

    @property
    def stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "status": self.status.name,
            "completed": self._tasks_completed,
            "failed": self._tasks_failed,
        }
