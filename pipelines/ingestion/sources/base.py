"""Base Source Adapter Interface for Literature Acquisition.

Provides resilient HTTP transport, exponential backoff retries, polite rate limiting,
and deterministic raw serialization.
"""

from __future__ import annotations

import abc
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from dataset.schemas.canonical_paper import CanonicalPaper, RawRecord
from pipelines.ingestion.config import config

logger = logging.getLogger(__name__)


class BaseSourceAdapter(abc.ABC):
    """Abstract base class for scholarly literature source adapters."""

    def __init__(
        self,
        source_name: str,
        rate_limit_delay: float = 0.5,
        max_retries: int = config.MAX_RETRIES,
        timeout: float = config.HTTP_TIMEOUT_SECONDS,
    ):
        self.source_name = source_name
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_request_time: float = 0.0
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Lazy initialized HTTP client session."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self._get_default_headers(),
            )
        return self._client

    @client.setter
    def client(self, client: httpx.Client) -> None:
        self._client = client

    def _get_default_headers(self) -> Dict[str, str]:
        """Default HTTP headers across requests."""
        return {
            "User-Agent": f"ResearchGraph/0.1.0 (https://github.com/researchgraph; mailto:{config.OPENALEX_MAILTO})",
            "Accept": "application/json",
        }

    def _rate_limit(self) -> None:
        """Enforce polite rate limiting between consecutive network requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _request_with_retry(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Execute HTTP request with exponential backoff and error logging."""
        merged_headers = self._get_default_headers()
        if headers:
            merged_headers.update(headers)

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            self._rate_limit()
            try:
                response = self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=merged_headers,
                )

                if response.status_code == 429 or response.status_code >= 500:
                    delay = config.BACKOFF_FACTOR ** attempt
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        delay = max(delay, float(retry_after))
                    logger.warning(
                        f"[{self.source_name}] Received status {response.status_code} from {url}. "
                        f"Retrying in {delay:.1f}s (Attempt {attempt}/{self.max_retries})..."
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                return response

            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_exception = exc
                delay = config.BACKOFF_FACTOR ** attempt
                logger.warning(
                    f"[{self.source_name}] Request failed for {url}: {exc}. "
                    f"Retrying in {delay:.1f}s (Attempt {attempt}/{self.max_retries})..."
                )
                time.sleep(delay)

        logger.error(f"[{self.source_name}] All {self.max_retries} attempts failed for {url}.")
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Failed to execute request to {url}")

    def create_raw_record(
        self,
        source_record_id: str,
        raw_data: Dict[str, Any],
        query: Optional[str] = None,
    ) -> RawRecord:
        """Wrap source response into a RawRecord container."""
        return RawRecord(
            source=self.source_name,
            source_record_id=str(source_record_id),
            fetched_at=datetime.now(timezone.utc).isoformat(),
            query=query,
            raw_data=raw_data,
        )

    def save_raw_records_checkpoint(
        self,
        records: List[RawRecord],
        output_file: Path,
    ) -> None:
        """Append raw records to a JSONL checkpoint file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "a", encoding="utf-8") as f:
            for rec in records:
                f.write(rec.model_dump_json() + "\n")

    @abc.abstractmethod
    def search(
        self,
        query: str,
        limit: int = 100,
        checkpoint_file: Optional[Path] = None,
        **kwargs: Any,
    ) -> List[RawRecord]:
        """Query the scholarly source API and return a list of RawRecord items."""
        pass

    @abc.abstractmethod
    def fetch_by_id(self, identifier: str) -> Optional[RawRecord]:
        """Fetch a specific paper record by its native source identifier."""
        pass

    @abc.abstractmethod
    def normalize(self, raw_record: RawRecord) -> CanonicalPaper:
        """Transform a raw source record into a canonical ResearchGraph representation."""
        pass

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "BaseSourceAdapter":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
