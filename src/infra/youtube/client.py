import typing
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import httpx
from pydantic import BaseModel

from utils.rest.client import RestClient


class YouTubeVideoCandidate(BaseModel):
    video_id: str
    title: str | None = None
    description: str | None = None
    default_language: str | None = None
    default_audio_language: str | None = None
    published_at: datetime | None = None


class YouTubeClient(typing.Protocol):
    async def most_popular(
        self,
        *,
        region_code: str,
        time_window_days: int,
        max_results: int = 50,
        page_token: str | None = None,
    ) -> tuple[list[YouTubeVideoCandidate], str | None]:
        raise NotImplementedError

    async def search(
        self,
        *,
        region_code: str,
        time_window_days: int,
        queries: list[str] | None = None,
        max_results: int = 50,
    ) -> list[YouTubeVideoCandidate]:
        raise NotImplementedError


class YouTubeDataApiV3Client(RestClient):
    """Minimal async client for YouTube Data API v3.

    Uses API key auth.

    Notes:
    - This only returns basic metadata needed for discovery.
    - Caption requirement checks are handled in later pipeline steps.
    """

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(
        self,
        *,
        api_key: str,
        http: httpx.AsyncClient | None = None,
        request_timeout_s: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._owns_http = http is None

        http_client = http or httpx.AsyncClient(
            timeout=httpx.Timeout(request_timeout_s),
            headers={"Accept": "application/json"},
        )

        super().__init__(http_client)
        self._http = http_client

    def _published_after(self, time_window_days: int) -> str:
        dt = datetime.now(UTC) - timedelta(days=time_window_days)
        return dt.isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_rfc3339(value: str | None) -> datetime | None:
        if not value:
            return None

        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")

        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    async def most_popular(
        self,
        *,
        region_code: str,
        time_window_days: int,
        max_results: int = 50,
        page_token: str | None = None,
    ) -> tuple[list[YouTubeVideoCandidate], str | None]:
        params = {
            "key": self._api_key,
            "part": "snippet",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": min(max_results, 50),
        }
        if page_token:
            params["pageToken"] = page_token

        _, data = await self.get(
            "videos",
            params=params,
        )

        published_after = datetime.now(UTC) - timedelta(days=time_window_days)
        out: list[YouTubeVideoCandidate] = []

        for item in data.get("items") or []:
            video_id = item.get("id")
            if not isinstance(video_id, str):
                continue

            snippet = item.get("snippet") or {}
            published_at = self._parse_rfc3339(snippet.get("publishedAt"))
            if published_at and published_at < published_after:
                continue

            out.append(
                YouTubeVideoCandidate(
                    video_id=video_id,
                    title=snippet.get("title"),
                    description=snippet.get("description"),
                    default_language=snippet.get("defaultLanguage"),
                    default_audio_language=snippet.get("defaultAudioLanguage"),
                    published_at=published_at,
                )
            )

        page_token = data.get("nextPageToken")
        return out, page_token

    async def search(
        self,
        *,
        region_code: str,
        time_window_days: int,
        queries: list[str] | None = None,
        max_results: int = 50,
    ) -> list[YouTubeVideoCandidate]:
        queries = [q for q in (queries or []) if q.strip()]
        if not queries:
            return []

        published_after = self._published_after(time_window_days)

        seen: set[str] = set()
        out: list[YouTubeVideoCandidate] = []

        per_query_limit = max(1, min(50, max_results // len(queries) or 1))

        for q in queries:
            if len(out) >= max_results:
                break

            page_token: str | None = None

            while len(out) < max_results:
                params: dict[str, typing.Any] = {
                    "part": "snippet",
                    "type": "video",
                    "q": q,
                    "regionCode": region_code,
                    "publishedAfter": published_after,
                    "maxResults": min(per_query_limit, 50),
                    "safeSearch": "moderate",
                    "order": "relevance",
                    "key": self._api_key,
                }
                if page_token:
                    params["pageToken"] = page_token

                _, data = await self.get("search", params=params)
                if not isinstance(data, dict):
                    raise TypeError("Unexpected YouTube API response")

                items = typing.cast(list[dict[str, typing.Any]], data.get("items") or [])
                for item in items:
                    if len(out) >= max_results:
                        break

                    id_obj = typing.cast(dict[str, typing.Any], item.get("id") or {})
                    video_id = id_obj.get("videoId")
                    if not isinstance(video_id, str):
                        continue
                    if video_id in seen:
                        continue
                    seen.add(video_id)

                    snippet = typing.cast(dict[str, typing.Any], item.get("snippet") or {})
                    published_at = self._parse_rfc3339(typing.cast(str | None, snippet.get("publishedAt")))

                    out.append(
                        YouTubeVideoCandidate(
                            video_id=video_id,
                            title=typing.cast(str | None, snippet.get("title")),
                            description=typing.cast(str | None, snippet.get("description")),
                            published_at=published_at,
                        )
                    )

                next_token = data.get("nextPageToken")
                page_token = next_token if isinstance(next_token, str) and next_token else None

                if not page_token or not items:
                    break

        return out


class DisabledYouTubeClient:
    """Safe no-op client for local/test when YouTube integration isn't wired."""

    async def most_popular(
        self,
        *,
        region_code: str,
        time_window_days: int,
        max_results: int = 50,
    ) -> list[YouTubeVideoCandidate]:
        return []

    async def search(
        self,
        *,
        region_code: str,
        time_window_days: int,
        queries: list[str] | None = None,
        max_results: int = 50,
    ) -> list[YouTubeVideoCandidate]:
        return []
