"""D365 F&O Customer Retrieval Tool — Main entry point."""

import argparse
import logging
import os
import sys
import time
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import D365Authenticator
from src.api_client import D365ApiClient
from src.customer_service import get_all_customers
from src.display import display_customers


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def validate_env_vars() -> dict:
    """Validate all required environment variables exist."""
    required = {
        "D365_TENANT_ID": os.getenv("D365_TENANT_ID"),
        "D365_CLIENT_ID": os.getenv("D365_CLIENT_ID"),
        "D365_CLIENT_SECRET": os.getenv("D365_CLIENT_SECRET"),
        "D365_ENVIRONMENT_URL": os.getenv("D365_ENVIRONMENT_URL"),
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"\n❌ Missing required environment variables:")
        for var in missing:
            print(f"   • {var}")
        print(f"\n   Set them in your .env file and try again.\n")
        sys.exit(1)

    return required


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Retrieve all customers from D365 F&O",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py                     # Retrieve and display customers
  python src/main.py --cross-company     # Across all legal entities
  python src/main.py --max 50            # First 50 customers only
  python src/main.py --all-columns       # Show all fields
  python src/main.py --dry-run           # Test auth only
  python src/main.py -v                  # Verbose logging
        """,
    )
    parser.add_argument("--cross-company", action="store_true", help="Retrieve across all legal entities")
    parser.add_argument("--max", type=int, default=None, help="Maximum number of records to retrieve")
    parser.add_argument("--all-columns", action="store_true", help="Display all columns (not just key fields)")
    parser.add_argument("--dry-run", action="store_true", help="Authenticate and fetch first page only")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose/debug logging")
    return parser.parse_args()


def main() -> None:
    """Main execution flow."""
    args = parse_args()
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # Load .env from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(env_path)

    # Validate
    config = validate_env_vars()

    print("\n🔗 D365 F&O Customer Retrieval Tool")
    print(f"   Environment: {config['D365_ENVIRONMENT_URL']}")
    print(f"   Tenant:      {config['D365_TENANT_ID']}")
    print()

    # Step 1: Authenticate
    print("🔐 Authenticating...")
    start_time = time.time()

    authenticator = D365Authenticator(
        tenant_id=config["D365_TENANT_ID"],
        client_id=config["D365_CLIENT_ID"],
        client_secret=config["D365_CLIENT_SECRET"],
        environment_url=config["D365_ENVIRONMENT_URL"],
    )
    token = authenticator.get_access_token()
    print("✅ Authenticated successfully.\n")

    if args.dry_run:
        print("🏁 Dry run complete — authentication successful. No data retrieved.")
        return

    # Step 2: Retrieve customers
    print("📥 Retrieving customers...")
    client = D365ApiClient(
        environment_url=config["D365_ENVIRONMENT_URL"],
        access_token=token,
    )

    customers = get_all_customers(
        client=client,
        cross_company=args.cross_company,
        max_records=args.max,
    )

    elapsed = time.time() - start_time

    # Step 3: Display
    display_customers(customers, show_all_columns=args.all_columns)

    print(f"⏱️  Completed in {elapsed:.1f} seconds.\n")


if __name__ == "__main__":
    main()
