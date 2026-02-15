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
    "PaymentTermsName",
    "InvoiceAccount",
    "PrimaryContactEmail",
    "PrimaryContactPhone",
    "AddressDescription",
    "DataAreaId",
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
