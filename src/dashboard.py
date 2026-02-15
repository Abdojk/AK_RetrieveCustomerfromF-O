"""Dashboard summary view for customer data."""

from collections import Counter


def _bar(count: int, total: int, width: int = 30) -> str:
    """Render a simple text bar proportional to count/total."""
    if total == 0:
        return ""
    filled = round(count / total * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def _top_section(title: str, counter: Counter, total: int, limit: int = 10) -> str:
    """Format a ranked breakdown section."""
    lines = [f"  {title}"]
    lines.append(f"  {'-' * (len(title) + 4)}")
    for value, count in counter.most_common(limit):
        label = value if value else "(blank)"
        pct = count / total * 100 if total else 0
        lines.append(f"    {label:<25} {count:>5}  ({pct:5.1f}%)  {_bar(count, total)}")
    if len(counter) > limit:
        lines.append(f"    ... and {len(counter) - limit} more")
    return "\n".join(lines)


def display_dashboard(customers: list[dict]) -> None:
    """Print a summary dashboard of customer data to the console."""
    total = len(customers)

    print(f"\n{'=' * 70}")
    print(f"  D365 F&O CUSTOMER DASHBOARD")
    print(f"{'=' * 70}")

    # --- Overview ---
    print(f"\n  Total customers: {total}\n")

    if total == 0:
        print("  No data to display.\n")
        return

    # --- By Customer Group ---
    group_counts = Counter(c.get("CustomerGroupId", "") or "" for c in customers)
    print(_top_section("By Customer Group", group_counts, total))

    # --- By Currency ---
    currency_counts = Counter(c.get("SalesCurrencyCode", "") or "" for c in customers)
    print()
    print(_top_section("By Currency", currency_counts, total))

    # --- By Company (DataAreaId) ---
    company_counts = Counter(c.get("DataAreaId", "") or "" for c in customers)
    print()
    print(_top_section("By Company", company_counts, total))

    # --- Contact Coverage ---
    has_email = sum(1 for c in customers if c.get("PrimaryContactEmail"))
    has_phone = sum(1 for c in customers if c.get("PrimaryContactPhone"))

    print(f"\n  Contact Coverage")
    print(f"  --------------------")
    email_pct = has_email / total * 100
    phone_pct = has_phone / total * 100
    print(f"    Email:  {has_email:>5} / {total}  ({email_pct:5.1f}%)  {_bar(has_email, total)}")
    print(f"    Phone:  {has_phone:>5} / {total}  ({phone_pct:5.1f}%)  {_bar(has_phone, total)}")

    print(f"\n{'=' * 70}\n")
