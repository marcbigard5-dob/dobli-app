from typing import Any

from src.agents.base_agent import BaseAgent, Task


class AnalystAgent(BaseAgent):
    async def execute(self, task: Task) -> Any:
        self.logger.info(f"Analyzing: {task.action} with params={task.params}")

        data = task.params.get("data")
        if isinstance(data, str):
            data = {"text": data}

        if not data:
            raise ValueError("Missing 'data' in task params")

        analysis = {
            "type": task.action,
            "input_size": len(str(data)),
            "summary": f"Analysis complete for {task.action}",
        }

        if task.action == "sentiment":
            positive_words = ["good", "great", "excellent", "amazing"]
            text = str(data.get("text", "")).lower()
            score = sum(1 for w in positive_words if w in text) / max(len(text.split()), 1)
            analysis["sentiment_score"] = round(score * 100, 2)

        elif task.action == "keywords":
            import re
            text = str(data.get("text", "")).lower()
            words = re.findall(r"\b[a-z]{3,}\b", text)
            freq = {}
            for w in words:
                freq[w] = freq.get(w, 0) + 1
            analysis["top_keywords"] = sorted(freq.items(), key=lambda x: -x[1])[:10]

        elif task.action == "compare":
            competitors = task.params.get("competitors", [])
            analysis["competitors_analyzed"] = len(competitors)
            analysis["recommendations"] = [
                f"Differentiate from competitor {i+1}" for i in range(len(competitors))
            ]

        return analysis
