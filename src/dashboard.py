"""Interactive Streamlit dashboard for D365 F&O customer data."""

import logging
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# Ensure src package is importable when run via `streamlit run src/dashboard.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api_client import D365ApiClient
from src.auth import D365Authenticator
from src.customer_service import get_all_customers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading (cached to avoid repeated API calls on every interaction)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner="Fetching customers from D365 F&O...")
def load_customer_data() -> pd.DataFrame:
    """Authenticate with D365 and fetch all customers, returning a DataFrame."""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    load_dotenv(env_path)

    config = {
        "tenant_id": os.getenv("D365_TENANT_ID"),
        "client_id": os.getenv("D365_CLIENT_ID"),
        "client_secret": os.getenv("D365_CLIENT_SECRET"),
        "environment_url": os.getenv("D365_ENVIRONMENT_URL"),
    }

    missing = [k for k, v in config.items() if not v]
    if missing:
        st.error(f"Missing environment variables: {', '.join(missing)}")
        st.stop()

    authenticator = D365Authenticator(
        tenant_id=config["tenant_id"],
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        environment_url=config["environment_url"],
    )
    token = authenticator.get_access_token()

    client = D365ApiClient(
        environment_url=config["environment_url"],
        access_token=token,
    )

    records = get_all_customers(client=client)
    df = pd.DataFrame(records)

    # Derive Country-State composite column for grouping
    df["CountryState"] = (
        df["AddressCountryRegionId"].fillna("Unknown")
        + " - "
        + df["AddressState"].fillna("Unknown")
    )
    return df


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

def render_sidebar_filters(df: pd.DataFrame) -> None:
    """Render interactive filter controls in the sidebar."""
    st.sidebar.header("Filters")

    # Customer Group multi-select
    all_groups = sorted(df["CustomerGroupId"].dropna().unique().tolist())
    st.sidebar.multiselect(
        "Customer Group",
        options=all_groups,
        default=[],
        key="filter_customer_group",
    )

    # Country multi-select
    all_countries = sorted(df["AddressCountryRegionId"].dropna().unique().tolist())
    st.sidebar.multiselect(
        "Country",
        options=all_countries,
        default=[],
        key="filter_country",
    )

    # State multi-select (dynamically filtered by country selection)
    selected_countries = st.session_state.get("filter_country", [])
    if selected_countries:
        state_pool = df[df["AddressCountryRegionId"].isin(selected_countries)]
    else:
        state_pool = df
    all_states = sorted(state_pool["AddressState"].dropna().unique().tolist())
    st.sidebar.multiselect(
        "State",
        options=all_states,
        default=[],
        key="filter_state",
    )

    # Search by customer name
    st.sidebar.text_input(
        "Search by Name",
        key="filter_name_search",
    )


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar filter selections to the DataFrame."""
    filtered = df.copy()

    groups = st.session_state.get("filter_customer_group", [])
    if groups:
        filtered = filtered[filtered["CustomerGroupId"].isin(groups)]

    countries = st.session_state.get("filter_country", [])
    if countries:
        filtered = filtered[filtered["AddressCountryRegionId"].isin(countries)]

    states = st.session_state.get("filter_state", [])
    if states:
        filtered = filtered[filtered["AddressState"].isin(states)]

    name_search = st.session_state.get("filter_name_search", "").strip()
    if name_search:
        filtered = filtered[
            filtered["OrganizationName"]
            .fillna("")
            .str.contains(name_search, case=False, na=False)
        ]

    return filtered


# ---------------------------------------------------------------------------
# Dashboard components
# ---------------------------------------------------------------------------

def render_metrics(df: pd.DataFrame) -> None:
    """Render summary KPI metrics across the top."""
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Customers", len(df))
    m2.metric("Customer Groups", df["CustomerGroupId"].nunique())
    m3.metric("Countries", df["AddressCountryRegionId"].nunique())
    m4.metric("States / Provinces", df["AddressState"].nunique())


def render_customer_group_view(df: pd.DataFrame) -> None:
    """Render the Customer Group bar chart and detail table."""
    st.subheader("Customers by Group")

    if df.empty:
        st.info("No customers match the current filters.")
        return

    group_counts = (
        df.groupby("CustomerGroupId", dropna=False)
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )

    fig = px.bar(
        group_counts,
        x="CustomerGroupId",
        y="Count",
        color="CustomerGroupId",
        labels={"CustomerGroupId": "Customer Group", "Count": "Customers"},
    )
    fig.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View Group Data"):
        st.dataframe(group_counts, use_container_width=True, hide_index=True)


def render_country_state_view(df: pd.DataFrame) -> None:
    """Render the Country-State bar chart and detail table."""
    st.subheader("Customers by Country-State")

    if df.empty:
        st.info("No customers match the current filters.")
        return

    cs_counts = (
        df.groupby(["AddressCountryRegionId", "AddressState"], dropna=False)
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )
    cs_counts["CountryState"] = (
        cs_counts["AddressCountryRegionId"].fillna("Unknown")
        + " - "
        + cs_counts["AddressState"].fillna("Unknown")
    )

    top_n = cs_counts.head(20)

    fig = px.bar(
        top_n,
        x="CountryState",
        y="Count",
        color="AddressCountryRegionId",
        labels={"CountryState": "Country - State", "Count": "Customers"},
    )
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View Full Country-State Data"):
        st.dataframe(cs_counts, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main dashboard layout
# ---------------------------------------------------------------------------

def render_dashboard(df: pd.DataFrame) -> None:
    """Render the main dashboard layout."""
    st.title("D365 F&O Customer Dashboard")
    st.caption(f"{len(df)} customers loaded from CustomersV2")

    render_sidebar_filters(df)
    filtered_df = apply_filters(df)

    render_metrics(filtered_df)

    col_left, col_right = st.columns(2)

    with col_left:
        render_customer_group_view(filtered_df)

    with col_right:
        render_country_state_view(filtered_df)

    st.subheader("Customer Details")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Streamlit dashboard entry point."""
    st.set_page_config(
        page_title="D365 F&O Customers",
        page_icon="📊",
        layout="wide",
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    df = load_customer_data()
    render_dashboard(df)


if __name__ == "__main__":
    main()
