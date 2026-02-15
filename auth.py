"""OAuth 2.0 Client Credentials authentication for D365 F&O."""

import logging
import sys
from msal import ConfidentialClientApplication

logger = logging.getLogger(__name__)


class D365Authenticator:
    """Handles OAuth 2.0 token acquisition for D365 F&O."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, environment_url: str):
        self.environment_url = environment_url.rstrip("/")
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scope = [f"{self.environment_url}/.default"]

        self._app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self.authority,
        )
        self._token_cache: dict | None = None

    def get_access_token(self) -> str:
        """Acquire or retrieve cached access token."""
        # Try silent (cached) first
        result = self._app.acquire_token_silent(self.scope, account=None)

        if not result:
            logger.info("No cached token found. Acquiring new token...")
            result = self._app.acquire_token_for_client(scopes=self.scope)

        if "access_token" in result:
            logger.info("Access token acquired successfully.")
            return result["access_token"]

        error = result.get("error", "unknown")
        error_desc = result.get("error_description", "No description provided.")
        logger.error(f"Authentication failed: {error} — {error_desc}")
        print(f"\n❌ Authentication failed: {error}")
        print(f"   {error_desc}")
        sys.exit(1)
