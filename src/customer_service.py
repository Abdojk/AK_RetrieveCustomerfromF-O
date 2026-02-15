"""Customer retrieval service for D365 F&O CustomersV2 entity."""

import logging
from src.api_client import D365ApiClient

logger = logging.getLogger(__name__)

# Key fields from CustomersV2 entity
CUSTOMER_FIELDS = [
    "CustomerAccount",
    "CustomerGroupId",
    "OrganizationName",
    "NameAlias",
    "SalesCurrencyCode",
    "PaymentTerms",
    "InvoiceAccount",
    "PrimaryContactEmail",
    "PrimaryContactPhone",
    "AddressDescription",
]

ENTITY_NAME = "CustomersV2"


def get_all_customers(
    client: D365ApiClient,
    cross_company: bool = False,
    max_records: int | None = None,
) -> list[dict]:
    """Retrieve all customers from D365 F&O."""
    logger.info(f"Retrieving customers from {ENTITY_NAME}...")
    logger.info(f"  Fields: {', '.join(CUSTOMER_FIELDS)}")
    logger.info(f"  Cross-company: {cross_company}")

    records = client.get_all_records(
        entity=ENTITY_NAME,
        select_fields=CUSTOMER_FIELDS,
        cross_company=cross_company,
        max_records=max_records,
    )

    logger.info(f"Total customers retrieved: {len(records)}")
    return records


def create_customer(
    client: D365ApiClient,
    customer_account: str,
    organization_name: str,
    customer_group_id: str,
    currency_code: str = "USD",
) -> dict:
    """Create a new customer in D365 F&O.

    Args:
        client: Authenticated D365 API client.
        customer_account: The customer account ID (e.g., 'AK001').
        organization_name: The organization/customer name.
        customer_group_id: The customer group ID (e.g., '80').

    Returns:
        The created customer record as a dictionary.
    """
    payload = {
        "CustomerAccount": customer_account,
        "OrganizationName": organization_name,
        "CustomerGroupId": customer_group_id,
        "SalesCurrencyCode": currency_code,
    }

    logger.info(f"Creating customer in {ENTITY_NAME}: {payload}")

    result = client.post_record(entity=ENTITY_NAME, payload=payload)

    logger.info(f"Customer created successfully: {result.get('CustomerAccount', 'unknown')}")
    return result
