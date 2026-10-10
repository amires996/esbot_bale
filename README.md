# ESBot — CRM & After-Sales Service Platform

**Operational MVP — Version 0.3.0**

ESBot is a customer relationship management (CRM) and after-sales service platform featuring a Persian RTL interface, a FastAPI backend, SQLAlchemy database integration, and a Bale messaging bot powered by long polling.

This version is designed for local deployment and testing of core workflows. It must not be used in production with sensitive data or for bulk messaging without a thorough security and operational review.

## Implemented Features

* **Secure Admin Authentication:** Administrator login with hashed passwords and JWT-based authentication.
* **Live Dashboard:** Dashboard statistics powered by real database records.
* **Customer Management:** Create, view, search, and archive customer records.
* **Product Management:** Create, view, edit, and deactivate products.
* **Purchase History:** Record customer purchases and automatically generate service reminders based on configurable service intervals.
* **Support Ticket Management:** Create, view, and manage support tickets and their statuses.
* **Service Reminders:** Manage service reminders through the web interface.
* **Campaign Management:** Create messaging campaigns, send messages to customers with a registered `bale_chat_id`, and record the result of each message.
* **Bale Connectivity Testing:** Test the actual Bale bot connection and send real messages directly from the dashboard.
* **Persistent Bot User Registration:** Persistently register users who start the Bale bot and send them welcome messages.
* **Role-Based Bot Menus:** Provide separate menus for regular users and administrators using `BALE_ADMIN_CHAT_ID`.
* **Bale Support Tickets:** Allow users to submit support tickets through Bale and forward them to the administrator's chat. Administrators can reply using `/reply`.
* **Broadcast Messaging:** Send broadcast messages to registered bot users and record delivery results in campaign and message reports.
* **Bale Admin Dashboard:** Access statistics, customers, products, purchases, support tickets, and service reminders through the bot's administrative menu.
* **Messaging Reports:** Track messaging activity and outcomes.
* **Audit Logs:** Record auditable system events.
* **Excel Import and Export:** Import and export customer records using `.xlsx` files.
* **Interactive API Documentation:** Automatically generated API documentation powered by Swagger UI.

## Important Limitations

This release is an operational MVP, not a finalized enterprise-grade product.

The following limitations must be considered before deployment:

* The Bale bot uses long polling.
* There is no persistent messaging queue.
* Automatic scheduled execution of service reminders has not yet been implemented.
* Intelligent retry mechanisms are not available.
* Global rate limiting has not been implemented.
* Advanced role-based access control and permission management are not available.
* Alembic database migrations have not been implemented.
* No independent security audit has been conducted.
* Campaign messages are sent sequentially and directly. Always review the recipient list before sending a campaign. This implementation is not suitable for large-scale campaigns.
* The Bale bot token is loaded from a local `.env` file. Never publish this file to a public GitHub repository. Production deployments require stronger secrets management and access controls.
* SQLite is intended for local development. Configure PostgreSQL and database migrations before deploying the application in a multi-user or production environment.
* The current version is tested in a development environment and must not be considered bug-free or production-ready.

## Getting Started — Windows PowerShell

### 1. Configure Environment Variables

From the root directory of the `esbot` project, create your local environment configuration file from the example:

```powershell
Copy-Item .env.example .env
```

Generate a secure secret key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open the `.env` file:

```powershell
notepad .env
```

Replace the `SECRET_KEY` value with the generated key.

Configure any other required environment variables according to `.env.example`.

### 2. Set Up the Backend

From the project root, execute:

```powershell
cd .\backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Create the administrator account:

```powershell
python ..\scripts\create_admin.py
```

Start the FastAPI development server:

```powershell
python -m uvicorn app.main:app --reload
```

The backend will be available at:

* **API Base URL:** `http://127.0.0.1:8000`
* **Swagger UI:** `http://127.0.0.1:8000/docs`

The `--reload` option is intended for development and should not be used as a production server configuration.

### 3. Set Up the Frontend

Open a second PowerShell terminal and navigate to the frontend directory:

```powershell
cd C:\Path\To\esbot\frontend
```

Replace `C:\Path\To\esbot` with the actual path to your project.

Install dependencies:

```powershell
npm.cmd install
```

Start the frontend development server:

```powershell
npm.cmd run dev
```

The frontend is typically available at:

`http://localhost:5173`

Open the frontend in your browser and sign in using the administrator credentials created in the previous step.

## Customer Data — Excel Import and Export

Customer import files must use the `.xlsx` format.

The first row must contain the following column names:

| Column       | Required | Description               |
| ------------ | -------- | ------------------------- |
| `first_name` | Yes      | Customer's first name     |
| `last_name`  | Yes      | Customer's last name      |
| `mobile`     | Yes      | Customer's mobile number  |
| `email`      | No       | Customer's email address  |
| `notes`      | No       | Additional customer notes |

Duplicate mobile numbers are ignored during import.

## Running Tests

Activate the backend virtual environment, navigate to the `backend` directory, and run:

```powershell
pytest -q
```

Review the test results before making changes or deploying the application.

## Security Considerations

Before deploying ESBot, follow these security practices:

* Never commit `.env` files, Bale bot tokens, database files, or customer data to a public GitHub repository.
* Use HTTPS for production deployments.
* Use PostgreSQL instead of SQLite for production workloads that require concurrent access and stronger operational capabilities.
* Implement secure secrets management.
* Configure regular database backups and verify that restoration works.
* Monitor application health, errors, and operational events.
* Review authentication, authorization, input validation, and messaging permissions before exposing the application to the internet.
* Apply appropriate rate limits and messaging safeguards before enabling bulk messaging.
* Conduct a security review before using real customer information.

## Setting Up the Bale Bot

The complete Persian-language setup guide covers:

* Configuring the Bale bot token.
* Finding the administrator's chat ID.
* Enabling the administrative menu.
* Creating and managing support tickets.
* Sending broadcast messages.

Read the setup guide:

**[BALE_BOT_FA.md — Bale Bot Setup Guide](https://github.com/amires996/esbot_bale/blob/main/BALE_BOT_FA.md)**

To enable the Bale bot, configure the following variables in your `.env` file:

```env
BALE_BOT_TOKEN=your_bale_bot_token
BALE_ADMIN_CHAT_ID=your_admin_chat_id
```

Replace both placeholder values with the appropriate credentials and identifiers.

Restart the backend server after updating the configuration.

If either variable is empty, the application runs its web API without starting the Bale bot's polling process.

## Technology Stack

* **Backend:** FastAPI
* **Database ORM:** SQLAlchemy
* **Database:** SQLite for local development
* **Authentication:** JWT and password hashing
* **Messaging Integration:** Bale Bot API with long polling
* **Frontend:** Web-based RTL interface
* **Data Import/Export:** Excel (`.xlsx`)
* **API Documentation:** Swagger UI
* **Testing:** pytest

## Project Status

**Current Release:** `v0.3.0` — Operational MVP

ESBot provides the core functionality required to manage customer records, products, purchases, support tickets, service reminders, messaging campaigns, and Bale bot interactions.

Further development is needed to improve scalability, security, automated scheduling, messaging reliability, access control, and production deployment readiness.

**ESBot is an actively developing project. Contributions, feedback, and suggestions for improvement are welcome.**
