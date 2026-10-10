# Bale API: verified scope and limitations

Research starting point: official Bale Bot API documentation at `https://docs.bale.ai/`. The API endpoint pattern and `getMe` / `sendMessage` operations are consistent with the official Bot API documentation; this project intentionally implements only those two HTTP operations in its current client.

## Implemented
- `getMe`: validate token and retrieve bot metadata.
- `sendMessage`: submit text to an explicitly supplied Bale chat ID.
- Timeouts and network errors are normalized without returning raw URLs or token values.

## Not implemented / not verified in this repository
- Webhook or long-polling receiver and update deduplication
- Inline keyboard/callback workflows
- Media sending
- Provider rate limits and official quotas
- Delivery receipts, read receipts, and message-edit/delete semantics
- Durable proactive messaging eligibility and consent rules
- Official production behavior under ambiguous timeouts

A successful `sendMessage` response is treated as provider acceptance, not proof of delivery or reading. Before release, review the current official documentation and run integration tests with a real test bot. Do not infer Telegram support guarantees apply unchanged to Bale.
