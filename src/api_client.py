"""Generic OData API client for D365 F&O with pagination and retry."""

import logging
import time
import requests

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class D365ApiClient:
    """HTTP client for D365 F&O OData API."""

    def __init__(self, environment_url: str, access_token: str):
        self.base_url = environment_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        })

    def get_all_records(
        self,
        entity: str,
        select_fields: list[str] | None = None,
        cross_company: bool = False,
        max_records: int | None = None,
    ) -> list[dict]:
        """Retrieve all records from an entity, handling pagination."""
        url = f"{self.base_url}/data/{entity}"

        params = {}
        if select_fields:
            params["$select"] = ",".join(select_fields)
        if cross_company:
            params["cross-company"] = "true"

        all_records: list[dict] = []
        page = 1

        while url:
            logger.info(f"Fetching page {page}...")
            data = self._get_with_retry(url, params if page == 1 else None)

            records = data.get("value", [])
            all_records.extend(records)
            logger.info(f"  Page {page}: {len(records)} records (total: {len(all_records)})")

            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                logger.info(f"Reached max_records limit ({max_records}). Stopping.")
                break

            # Follow server-driven pagination
            url = data.get("@odata.nextLink")
            page += 1

        return all_records

    def _get_with_retry(self, url: str, params: dict | None = None) -> dict:
        """Execute GET request with retry logic for transient failures."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, params=params, timeout=60)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 401:
                    logger.error("HTTP 401 Unauthorized — token may be expired or invalid.")
                    raise SystemExit("Authentication error. Check credentials and token.")

                if response.status_code == 429:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(f"HTTP 429 Rate limited. Retrying in {wait}s... (attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(wait)
                    continue

                if response.status_code >= 500:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(f"HTTP {response.status_code} Server error. Retrying in {wait}s... (attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(wait)
                    continue

                # Other client errors — don't retry
                logger.error(f"HTTP {response.status_code}: {response.text[:500]}")
                raise SystemExit(f"API request failed with status {response.status_code}")

            except requests.exceptions.ConnectionError as e:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"Connection error (attempt {attempt}/{MAX_RETRIES}): {e}")
                if attempt == MAX_RETRIES:
                    raise SystemExit(f"Failed to connect after {MAX_RETRIES} attempts.")
                time.sleep(wait)

            except requests.exceptions.Timeout:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"Request timed out (attempt {attempt}/{MAX_RETRIES})")
                if attempt == MAX_RETRIES:
                    raise SystemExit(f"Request timed out after {MAX_RETRIES} attempts.")
                time.sleep(wait)

        raise SystemExit(f"Failed after {MAX_RETRIES} retries.")
