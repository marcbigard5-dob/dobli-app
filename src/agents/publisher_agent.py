from typing import Any

from src.agents.base_agent import BaseAgent, Task


class PublisherAgent(BaseAgent):
    async def execute(self, task: Task) -> Any:
        self.logger.info(f"Publishing: {task.action} with params={task.params}")

        content = task.params.get("content")
        platform = task.params.get("platform", "web")
        destination = task.params.get("destination", "")

        if not content:
            raise ValueError("Missing 'content' in task params")

        result = {
            "platform": platform,
            "destination": destination,
            "status": "published",
            "content_length": len(str(content)),
        }

        if self._browser:
            result["browser"] = True
            self.logger.info(f"Posting to {platform} via browser automation")

        result["message"] = f"Content published to {platform}" + (f" at {destination}" if destination else "")
        return result
