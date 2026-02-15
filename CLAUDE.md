# CLAUDE.md — D365 F&O Customer Management Tool

## Project Context

This project connects to a Microsoft Dynamics 365 Finance & Operations environment via the OData REST API, authenticates using OAuth 2.0 Client Credentials, and supports retrieving and creating customer records via the **CustomersV2** entity. Output is displayed in the console in a formatted table.

---

## Tech Stack

| Layer        | Technology                          |
| ------------ | ----------------------------------- |
| Language     | Python 3.11+                        |
| Auth         | OAuth 2.0 Client Credentials (MSAL) |
| API          | D365 F&O OData v4 REST API          |
| HTTP Client  | `requests`                          |
| Config       | `.env` file via `python-dotenv`     |
| Display      | `tabulate` (console table output)   |

---

## API Endpoints

```
GET  https://d365fo-nov235e1ff351a4734eb8aos.axcloud.dynamics.com/data/CustomersV2
POST https://d365fo-nov235e1ff351a4734eb8aos.axcloud.dynamics.com/data/CustomersV2
```

---

## Coding Conventions

- snake_case for files, functions, variables. PascalCase for classes.
- Type hints on all function signatures.
- Use Python `logging` module, not `print()` (except for final table output).
- Read secrets from `.env` only. Never hardcode.
- Supports **GET** (retrieve) and **POST** (create) operations on the CustomersV2 entity.
