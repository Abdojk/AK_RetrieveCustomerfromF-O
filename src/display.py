"""Console display for customer records."""

from tabulate import tabulate

# Columns to display in console (subset for readability)
DISPLAY_COLUMNS = [
    "CustomerAccount",
    "OrganizationName",
    "CustomerGroupId",
    "SalesCurrencyCode",
    "PrimaryContactEmail",
    "DataAreaId",
]

# Friendly headers for display
DISPLAY_HEADERS = [
    "Account",
    "Name",
    "Group",
    "Currency",
    "Email",
    "Company",
]


def display_customers(customers: list[dict], show_all_columns: bool = False) -> None:
    """Print customers to console in a formatted table."""
    if not customers:
        print("\n⚠️  No customers found.")
        return

    if show_all_columns:
        # Use all keys from first record
        headers = list(customers[0].keys())
        rows = [list(c.values()) for c in customers]
    else:
        headers = DISPLAY_HEADERS
        rows = [
            [c.get(col, "") or "" for col in DISPLAY_COLUMNS]
            for c in customers
        ]

    print(f"\n{'='*80}")
    print(f"  D365 F&O CUSTOMERS — {len(customers)} records")
    print(f"{'='*80}\n")
    print(tabulate(rows, headers=headers, tablefmt="grid", maxcolwidths=30))
    print(f"\n  Total: {len(customers)} customers\n")


def display_created_customer(customer: dict) -> None:
    """Print a single created customer confirmation to the console."""
    if not customer:
        print("\n[WARNING] No customer data returned from API.")
        return

    print(f"\n{'='*60}")
    print(f"  CUSTOMER CREATED SUCCESSFULLY")
    print(f"{'='*60}\n")

    priority_fields = [
        "CustomerAccount",
        "OrganizationName",
        "CustomerGroupId",
        "SalesCurrencyCode",
        "DataAreaId",
    ]

    rows: list[list[str]] = []
    shown_keys: set[str] = set()
    for field in priority_fields:
        if field in customer:
            rows.append([field, customer[field] if customer[field] is not None else ""])
            shown_keys.add(field)

    for key, value in customer.items():
        if key not in shown_keys and not key.startswith("@"):
            rows.append([key, value if value is not None else ""])

    print(tabulate(rows, headers=["Field", "Value"], tablefmt="grid", maxcolwidths=[30, 50]))
    print()
