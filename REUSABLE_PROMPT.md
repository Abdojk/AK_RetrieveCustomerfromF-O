# Reusable Prompt — D365 F&O Entity Management Tool Generator

## How to Use

1. Copy everything below the `---START PROMPT---` line
2. Replace ALL `{{PLACEHOLDER}}` values with your specific values using the table below
3. Paste the filled-in prompt into a new Claude session
4. Claude will build the entire project from scratch

---

## Placeholder Reference

| Placeholder | What to fill in | Example (Customers) | Example (Vendors) |
|---|---|---|---|
| `{{PROJECT_NAME}}` | Repo/folder name | `AK_RetrieveCustomerfromF-O` | `AK_RetrieveVendorfromF-O` |
| `{{DESCRIPTION}}` | Short tool description | `Customer Management Tool` | `Vendor Management Tool` |
| `{{ENTITY_NAME}}` | D365 OData entity name | `CustomersV2` | `VendorsV3` |
| `{{ENTITY_LABEL}}` | Singular lowercase label | `customer` | `vendor` |
| `{{ENTITY_LABEL_PLURAL}}` | Plural lowercase label | `customers` | `vendors` |
| `{{ENTITY_FIELDS}}` | All fields to retrieve (Python list format) | See below | See below |
| `{{DISPLAY_COLUMNS}}` | Subset of fields for table view (Python list) | See below | See below |
| `{{DISPLAY_HEADERS}}` | Friendly column headers (Python list, same order) | See below | See below |
| `{{CREATE_REQUIRED_ARGS}}` | CLI args for `create` subcommand (required) | See below | See below |
| `{{CREATE_OPTIONAL_ARGS}}` | CLI args for `create` subcommand (optional w/ defaults) | See below | See below |
| `{{CREATE_PAYLOAD_FIELDS}}` | JSON field names for POST body | See below | See below |
| `{{PRIORITY_DISPLAY_FIELDS}}` | Key fields shown first in create confirmation | See below | See below |
| `{{DASHBOARD_GROUP_FIELD}}` | Field to group by in dashboard (like CustomerGroupId) | `CustomerGroupId` | `VendorGroupId` |
| `{{DASHBOARD_GROUP_LABEL}}` | Label for the grouping in dashboard | `Customer Group` | `Vendor Group` |
| `{{DASHBOARD_CURRENCY_FIELD}}` | Currency field name | `SalesCurrencyCode` | `CurrencyCode` |
| `{{DASHBOARD_EMAIL_FIELD}}` | Email field name (or empty if none) | `PrimaryContactEmail` | `PrimaryContactEmail` |
| `{{DASHBOARD_PHONE_FIELD}}` | Phone field name (or empty if none) | `PrimaryContactPhone` | `PrimaryContactPhone` |

### Example placeholder values for CustomersV2 (this is what the original project uses):

**{{ENTITY_FIELDS}}** — all fields to retrieve via GET:
```
CustomerAccount, CustomerGroupId, OrganizationName, NameAlias, SalesCurrencyCode, PaymentTermsName, InvoiceAccount, PrimaryContactEmail, PrimaryContactPhone, AddressDescription, DataAreaId
```

**{{DISPLAY_COLUMNS}}** — subset shown in default table:
```
CustomerAccount, OrganizationName, CustomerGroupId, SalesCurrencyCode, PrimaryContactEmail, DataAreaId
```

**{{DISPLAY_HEADERS}}** — friendly names (same order as DISPLAY_COLUMNS):
```
Account, Name, Group, Currency, Email, Company
```

**{{CREATE_REQUIRED_ARGS}}** — required CLI arguments for `create`:
```
--account (maps to CustomerAccount)
--name (maps to OrganizationName)
--group (maps to CustomerGroupId)
```

**{{CREATE_OPTIONAL_ARGS}}** — optional CLI arguments with defaults:
```
--currency (maps to SalesCurrencyCode, default: USD)
```

**{{CREATE_PAYLOAD_FIELDS}}** — the POST body key-value mapping:
```
CustomerAccount, OrganizationName, CustomerGroupId, SalesCurrencyCode
```

**{{PRIORITY_DISPLAY_FIELDS}}** — shown first in the create confirmation:
```
CustomerAccount, OrganizationName, CustomerGroupId, SalesCurrencyCode, DataAreaId
```

---

## ---START PROMPT---

Build me a complete Python CLI tool called **{{PROJECT_NAME}}** that connects to Microsoft Dynamics 365 Finance & Operations via the OData REST API, authenticates with OAuth 2.0 Client Credentials, and supports **retrieving** (GET) and **creating** (POST) records from the **{{ENTITY_NAME}}** entity.

I need this built as a production-quality project with the exact structure and patterns described below. Follow every detail precisely.

---

### Project Structure

```
{{PROJECT_NAME}}/
├── .gitignore
├── CLAUDE.md
├── README.md
├── requirements.txt
└── src/
    ├── __init__.py
    ├── main.py
    ├── auth.py
    ├── api_client.py
    ├── {{ENTITY_LABEL}}_service.py
    ├── display.py
    └── dashboard.py
```

---

### Tech Stack & Dependencies

**requirements.txt:**
```
msal>=1.24.0
requests>=2.31.0
python-dotenv>=1.0.0
tabulate>=0.9.0
```

**Python version:** 3.11+

---

### Environment Configuration

**.env file structure** (4 variables, never committed):
```
D365_TENANT_ID=<Azure AD Tenant ID>
D365_CLIENT_ID=<OAuth 2.0 App Registration Client ID>
D365_CLIENT_SECRET=<OAuth 2.0 Client Secret>
D365_ENVIRONMENT_URL=<D365 F&O base URL, e.g. https://d365fo-xxx.axcloud.dynamics.com>
```

**.gitignore:**
```
.env
output/
__pycache__/
*.pyc
.venv/
```

---

### Coding Conventions (MUST follow)

- `snake_case` for files, functions, variables. `PascalCase` for classes.
- Type hints on ALL function signatures.
- Use Python `logging` module, NOT `print()` — except for final table output and status messages to the user.
- Read secrets from `.env` only. Never hardcode credentials.
- All HTTP operations go through the API client with retry logic.

---

### File-by-File Implementation

#### 1. `src/__init__.py`

Single docstring:
```python
"""D365 F&O {{DESCRIPTION}} — src package."""
```

---

#### 2. `src/auth.py` — OAuth 2.0 Authentication

Create a class `D365Authenticator` that handles OAuth 2.0 Client Credentials authentication using MSAL.

**Constructor** `__init__(self, tenant_id: str, client_id: str, client_secret: str, environment_url: str)`:
- Strip trailing `/` from `environment_url`
- Build authority URL: `https://login.microsoftonline.com/{tenant_id}`
- Build scope: `["{environment_url}/.default"]`
- Create `msal.ConfidentialClientApplication` with `client_id`, `client_credential=client_secret`, `authority`
- Initialize `_token_cache: dict | None = None`

**Method** `get_access_token(self) -> str`:
- Try silent token acquisition first: `self._app.acquire_token_silent(self.scope, account=None)`
- If no cached token, acquire new: `self._app.acquire_token_for_client(scopes=self.scope)`
- If result contains `"access_token"`, log success and return it
- Otherwise, extract `error` and `error_description` from result, log the error, print error message with the cross mark symbol, and `sys.exit(1)`

Use `logging.getLogger(__name__)` for all logging.

---

#### 3. `src/api_client.py` — Generic OData API Client

Create a class `D365ApiClient` with constants `MAX_RETRIES = 3` and `RETRY_BACKOFF_BASE = 2`.

**Constructor** `__init__(self, environment_url: str, access_token: str)`:
- Strip trailing `/` from URL, store as `self.base_url`
- Create `requests.Session()` with these default headers:
  ```
  Authorization: Bearer {access_token}
  Accept: application/json
  OData-MaxVersion: 4.0
  OData-Version: 4.0
  ```

**Method** `get_all_records(self, entity: str, select_fields: list[str] | None = None, cross_company: bool = False, max_records: int | None = None) -> list[dict]`:
- Build URL: `{base_url}/data/{entity}`
- Build params: `$select` (comma-joined fields), `cross-company=true` if flag set
- Page through results using a `while url:` loop:
  - Call `_get_with_retry(url, params)` — only pass `params` on first page
  - Extend `all_records` with `data["value"]`
  - Log page number and cumulative count
  - Stop if `max_records` reached (truncate list)
  - Follow `@odata.nextLink` for next page
- Return full list

**Method** `_get_with_retry(self, url: str, params: dict | None = None) -> dict`:
- Loop `MAX_RETRIES` attempts:
  - `session.get(url, params=params, timeout=60)`
  - **200**: return `response.json()`
  - **401**: log error, `raise SystemExit` immediately (no retry)
  - **429**: log warning with wait time, `time.sleep(RETRY_BACKOFF_BASE ** attempt)`, continue
  - **5xx**: same as 429 (exponential backoff, retry)
  - **Other 4xx**: log error with first 500 chars of response, `raise SystemExit`
  - **ConnectionError**: backoff and retry, `raise SystemExit` after max retries
  - **Timeout** (60s): backoff and retry, `raise SystemExit` after max retries
- After all retries: `raise SystemExit`

**Method** `post_record(self, entity: str, payload: dict) -> dict`:
- Build URL: `{base_url}/data/{entity}`
- Call `_post_with_retry(url, payload)`

**Method** `_post_with_retry(self, url: str, payload: dict) -> dict`:
- Same retry structure as `_get_with_retry` but:
  - Uses `session.post(url, json=payload, timeout=60)`
  - Success code is **201** (not 200)
  - On non-retryable client errors (400, 409, etc.), try to parse the D365 inner error: `response.json()["error"]["innererror"]["message"]` and log it before exiting

---

#### 4. `src/{{ENTITY_LABEL}}_service.py` — Entity Business Logic

**Constants:**
```python
ENTITY_FIELDS = [
    {{ENTITY_FIELDS}}  # <-- replace with comma-separated quoted strings
]
ENTITY_NAME = "{{ENTITY_NAME}}"
```

**Function** `get_all_{{ENTITY_LABEL_PLURAL}}(client: D365ApiClient, cross_company: bool = False, max_records: int | None = None) -> list[dict]`:
- Log the entity name, fields, and cross-company flag
- Call `client.get_all_records(entity=ENTITY_NAME, select_fields=ENTITY_FIELDS, cross_company=cross_company, max_records=max_records)`
- Log total count
- Return records

**Function** `create_{{ENTITY_LABEL}}(client: D365ApiClient, <parameters from {{CREATE_REQUIRED_ARGS}} and {{CREATE_OPTIONAL_ARGS}}>) -> dict`:
- Build a payload dict mapping D365 field names to parameter values (using {{CREATE_PAYLOAD_FIELDS}})
- Log the payload
- Call `client.post_record(entity=ENTITY_NAME, payload=payload)`
- Log success
- Return result

---

#### 5. `src/display.py` — Console Table Output

**Constants:**
```python
DISPLAY_COLUMNS = [
    {{DISPLAY_COLUMNS}}  # <-- replace with quoted strings
]
DISPLAY_HEADERS = [
    {{DISPLAY_HEADERS}}  # <-- replace with quoted strings
]
```

**Function** `display_{{ENTITY_LABEL_PLURAL}}({{ENTITY_LABEL_PLURAL}}: list[dict], show_all_columns: bool = False) -> None`:
- If empty list: print warning and return
- If `show_all_columns`: use all keys from first record as headers, all values as rows
- Otherwise: use `DISPLAY_COLUMNS` / `DISPLAY_HEADERS`, extracting with `.get(col, "") or ""`
- Print a banner with `=` separator, title `D365 F&O {{ENTITY_LABEL_PLURAL | upper}} — {count} records`, then the table
- Use `tabulate(rows, headers=headers, tablefmt="grid", maxcolwidths=30)`
- Print total count at the bottom

**Function** `display_created_{{ENTITY_LABEL}}({{ENTITY_LABEL}}: dict) -> None`:
- If empty dict: print warning and return
- Print banner: `{{ENTITY_LABEL | upper}} CREATED SUCCESSFULLY`
- Show priority fields first (from {{PRIORITY_DISPLAY_FIELDS}}) as key-value rows
- Then show all remaining fields (excluding `@odata.*` metadata keys)
- Convert None values to empty string
- Use `tabulate(rows, headers=["Field", "Value"], tablefmt="grid", maxcolwidths=[30, 50])`

---

#### 6. `src/dashboard.py` — Summary Analytics Dashboard

**Helper** `_bar(count: int, total: int, width: int = 30) -> str`:
- Returns ASCII bar: filled blocks (Unicode \u2588) proportional to count/total, empty blocks (\u2591) for remainder

**Helper** `_top_section(title: str, counter: Counter, total: int, limit: int = 10) -> str`:
- Formats a ranked section with title, separator, then for each of the top `limit` entries: label (left-aligned 25 chars), count (right-aligned 5), percentage, bar
- Blank values shown as `(blank)`
- If more entries than limit: show `... and X more`

**Function** `display_dashboard({{ENTITY_LABEL_PLURAL}}: list[dict]) -> None`:
- Print banner: `D365 F&O {{ENTITY_LABEL | upper}} DASHBOARD` with `=` separators (width 70)
- Print total count
- If empty, print `No data to display.` and return
- **By {{DASHBOARD_GROUP_LABEL}}**: aggregate by `{{DASHBOARD_GROUP_FIELD}}`, show with `_top_section`
- **By Currency**: aggregate by `{{DASHBOARD_CURRENCY_FIELD}}`, show with `_top_section`
- **By Company**: aggregate by `DataAreaId`, show with `_top_section`
- **Contact Coverage** (if email/phone fields exist): count records that have `{{DASHBOARD_EMAIL_FIELD}}` and `{{DASHBOARD_PHONE_FIELD}}`, show counts and percentages with bars
- Print closing `=` separator

---

#### 7. `src/main.py` — CLI Entry Point

**Function** `setup_logging(verbose: bool = False) -> None`:
- `logging.basicConfig` with:
  - Level: `DEBUG` if verbose, else `INFO`
  - Format: `"%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"`
  - Date format: `"%H:%M:%S"`

**Function** `validate_env_vars() -> dict`:
- Check for all 4 required env vars: `D365_TENANT_ID`, `D365_CLIENT_ID`, `D365_CLIENT_SECRET`, `D365_ENVIRONMENT_URL`
- If any missing: print each missing var name, tell user to set in `.env`, `sys.exit(1)`
- Return dict of validated values

**Function** `parse_args() -> argparse.Namespace`:
- Main parser with description `"D365 F&O {{DESCRIPTION}}"`
- Epilog with usage examples
- **Top-level flags**: `--cross-company`, `--max`, `--all-columns`, `--dashboard`, `--dry-run`, `-v/--verbose`
- **Subcommands** via `add_subparsers(dest="command")`:
  - `retrieve`: `--cross-company`, `--max`, `--all-columns`, `--dry-run`
  - `create`: required args from {{CREATE_REQUIRED_ARGS}}, optional args from {{CREATE_OPTIONAL_ARGS}}
- If no subcommand given: default to `"retrieve"` with all flags False/None

**Function** `_handle_retrieve(args, client, start_time) -> None`:
- If `--dry-run`: print success message and return
- If `--dashboard`: call `get_all_{{ENTITY_LABEL_PLURAL}}` then `display_dashboard`
- Otherwise: call `get_all_{{ENTITY_LABEL_PLURAL}}` then `display_{{ENTITY_LABEL_PLURAL}}(records, show_all_columns=args.all_columns)`
- Print elapsed time

**Function** `_handle_create(args, client, start_time) -> None`:
- Print creation info
- Call `create_{{ENTITY_LABEL}}` with args
- Call `display_created_{{ENTITY_LABEL}}` with result
- Print elapsed time

**Function** `main() -> None`:
1. Parse args
2. Setup logging (pass `args.verbose`)
3. Load `.env` from project root: `os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")`
4. Validate env vars
5. Print startup banner with environment URL and tenant ID
6. Create `D365Authenticator`, get access token, print success
7. Create `D365ApiClient`
8. Dispatch: `retrieve` → `_handle_retrieve`, `create` → `_handle_create`

**Entry point:**
```python
if __name__ == "__main__":
    main()
```

**Imports in main.py:**
- `argparse`, `logging`, `os`, `sys`, `time`
- `from dotenv import load_dotenv`
- `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` before local imports
- Then import from `src.auth`, `src.api_client`, `src.{{ENTITY_LABEL}}_service`, `src.display`, `src.dashboard`

---

### CLAUDE.md

Generate a `CLAUDE.md` file with:
- Project context paragraph mentioning the {{ENTITY_NAME}} entity
- Tech stack table (Python 3.11+, OAuth 2.0/MSAL, D365 OData v4, requests, python-dotenv, tabulate)
- API endpoints (GET and POST on `{D365_ENVIRONMENT_URL}/data/{{ENTITY_NAME}}`)
- Coding conventions (snake_case, type hints, logging module, secrets in .env, GET and POST support)

---

### README.md

Just: `# {{PROJECT_NAME}}`

---

### CLI Usage Examples

Once built, the tool should work like this:

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env with your D365 credentials

# Retrieve records (default)
python src/main.py

# Retrieve with options
python src/main.py --cross-company
python src/main.py --max 50
python src/main.py --all-columns
python src/main.py --dashboard
python src/main.py --dry-run
python src/main.py -v

# Create a record
python src/main.py create {{CREATE_REQUIRED_ARGS with example values}} {{CREATE_OPTIONAL_ARGS with example values}}
```

---

### Important Notes

- The `api_client.py` is COMPLETELY GENERIC — it has no entity-specific code. It works with any D365 F&O OData entity.
- The `auth.py` is COMPLETELY GENERIC — no entity-specific code.
- Entity-specific logic lives ONLY in `{{ENTITY_LABEL}}_service.py`, `display.py`, and `dashboard.py`.
- Initialize a git repo and make an initial commit with all files.
- Do NOT create any test files unless I specifically ask.
- Build ALL files in a single pass — I want a complete, working project.

## ---END PROMPT---
