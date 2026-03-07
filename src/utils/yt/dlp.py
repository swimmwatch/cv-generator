import asyncio
import typing

import yt_dlp


class YtDlpVideoMetadataClient:
    def __init__(self) -> None:
        self._ydl_opts: dict[str, typing.Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "cookiesfrombrowser": ("chrome",),
        }

    def _fetch_sync(self, video_id: str) -> dict[str, typing.Any] | None:
        url = f"https://www.youtube.com/watch?v={video_id}"

        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            safe_info = ydl.sanitize_info(info)

        return safe_info

    async def fetch(self, video_id: str) -> dict[str, typing.Any]:
        return await asyncio.to_thread(self._fetch_sync, video_id)
