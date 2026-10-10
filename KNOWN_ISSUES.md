# Known issues and incomplete scope

This is an early development foundation, not a production-ready CRM.

1. Alembic configuration and versioned migrations are not yet created; `create_all` is currently a development shortcut.
2. Authentication lacks login rate limiting, token revocation, refresh/logout semantics, and a complete permission matrix.
3. Current data endpoints use bearer authentication but do not yet enforce granular per-action RBAC.
4. No persistent encrypted storage for Bale tokens or dashboard connection management.
5. Bale client has only `getMe` and text `sendMessage`; incoming updates and interactive bot flows are absent.
6. Frontend is a polished RTL dashboard starter; login, routes, data fetching, CRUD screens, and forms are not yet wired.
7. Product and purchase endpoints are incomplete; purchase CRUD and service date calculation integration are absent.
8. No durable job queue, workers, scheduler, reminders, campaigns, support tickets, imports, audit logs, reports, or backup scripts.
9. Automated test coverage is very limited and does not establish security or production readiness.
10. Google Fonts is currently loaded remotely; self-host the font or document network dependency for offline deployments.
