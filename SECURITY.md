# Security notes

- Never commit `.env`, Bale tokens, encryption keys, customer exports, or database files.
- Configure a random `SECRET_KEY` before using authentication.
- Use HTTPS and PostgreSQL in production.
- The current API has only a basic super-admin model; granular RBAC, login rate limiting, token revocation, encrypted Bale-token storage, CSRF protections for cookie sessions, audit trails, and production hardening are not complete.
- The initial-admin script is intended to run from a trusted local terminal only.
- The current JWT is a short-lived bearer token. Store it carefully; do not put it in URLs or logs.
- Never use this early build with real customer data or mass messaging until the documented gaps are resolved and independently reviewed.
