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
