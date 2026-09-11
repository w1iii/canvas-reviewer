import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class CanvasClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30)

    async def close(self):
        await self.client.aclose()

    async def _get_paginated(self, url: str, params: Optional[dict] = None) -> list:
        results = []
        if params is None:
            params = {}
        params.setdefault("per_page", 100)

        while True:
            resp = await self._request("GET", url, params=params)
            results.extend(resp)

            link_header = self.client.last_response.headers.get("link", "")
            next_url = self._parse_next(link_header)
            if not next_url:
                break
            url = next_url
            params = {}

        return results

    async def _request(self, method: str, url: str, **kwargs) -> dict | list:
        for attempt in range(3):
            try:
                resp = await self.client.request(method, url, **kwargs)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("retry-after", 5))
                    logger.warning("Rate limited, retrying after %ds", retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        return []

    def _parse_next(self, link_header: str) -> Optional[str]:
        for part in link_header.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
                return url
        return None

    async def get_courses(self) -> list:
        return await self._get_paginated(f"{self.base_url}/api/v1/courses")

    async def get_course_modules(self, course_id: str) -> list:
        return await self._get_paginated(
            f"{self.base_url}/api/v1/courses/{course_id}/modules",
            params={"include[]": "items"},
        )

    async def get_page_content(self, course_id: str, page_url: str) -> dict:
        return await self._request(
            "GET", f"{self.base_url}/api/v1/courses/{course_id}/pages/{page_url}"
        )

    async def get_file_content(self, course_id: str, file_id: str) -> bytes:
        resp = await self.client.get(
            f"{self.base_url}/api/v1/courses/{course_id}/files/{file_id}/download"
        )
        resp.raise_for_status()
        return resp.content

    async def get_discussion(self, course_id: str, topic_id: str) -> dict:
        return await self._request(
            "GET",
            f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics/{topic_id}",
        )
