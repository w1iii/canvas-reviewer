import json
from abc import ABC, abstractmethod

import httpx


class AIClient(ABC):
    @abstractmethod
    async def summarize(self, content: str, content_type: str) -> dict:
        ...


class OllamaClient(AIClient):
    def __init__(self, url: str, model: str):
        self.url = url.rstrip("/")
        self.model = model

    async def summarize(self, content: str, content_type: str) -> dict:
        prompt = f"""Analyze this {content_type} and create a study reviewer.

Content:
{content[:8000]}

Provide in this exact JSON format:
{{
    "key_concepts": ["concept1", "concept2"],
    "summary": "2-3 paragraph overview",
    "key_points": ["point1", "point2"],
    "definitions": {{"term": "definition"}},
    "key_takeaways": ["takeaway1", "takeaway2"]
}}"""

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=120,
            )
            resp.raise_for_status()
            return json.loads(resp.json()["message"]["content"])


class GroqClient(AIClient):
    def __init__(self, api_key: str, model: str):
        from groq import Groq

        self.client = Groq(api_key=api_key)
        self.model = model

    async def summarize(self, content: str, content_type: str) -> dict:
        prompt = f"""Analyze this {content_type} and create a study reviewer.

Content:
{content[:4000]}

Provide in this exact JSON format:
{{
    "key_concepts": ["concept1", "concept2"],
    "summary": "2-3 paragraph overview",
    "key_points": ["point1", "point2"],
    "definitions": {{"term": "definition"}},
    "key_takeaways": ["takeaway1", "takeaway2"]
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.content)


class GeminiClient(AIClient):
    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    async def summarize(self, content: str, content_type: str) -> dict:
        prompt = f"""Analyze this {content_type} and create a study reviewer.

Content:
{content[:4000]}

Provide in this exact JSON format:
{{
    "key_concepts": ["concept1", "concept2"],
    "summary": "2-3 paragraph overview",
    "key_points": ["point1", "point2"],
    "definitions": {{"term": "definition"}},
    "key_takeaways": ["takeaway1", "takeaway2"]
}}"""

        response = self.model.generate_content(prompt)
        return json.loads(response.text)


class NoAIClient(AIClient):
    async def summarize(self, content: str, content_type: str) -> dict:
        return {
            "key_concepts": [],
            "summary": content[:500],
            "key_points": [],
            "definitions": {},
            "key_takeaways": [],
            "original_content": content,
        }


def create_ai_client(provider: str, **kwargs) -> AIClient:
    if provider == "ollama":
        return OllamaClient(url=kwargs["ollama_url"], model=kwargs["ollama_model"])
    elif provider == "groq":
        return GroqClient(api_key=kwargs["groq_api_key"], model=kwargs["groq_model"])
    elif provider == "gemini":
        return GeminiClient(api_key=kwargs["gemini_api_key"], model=kwargs["gemini_model"])
    elif provider == "none":
        return NoAIClient()
    else:
        raise ValueError(f"Unknown AI provider: {provider}")
