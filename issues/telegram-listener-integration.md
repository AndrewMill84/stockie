# Issue: Integrate Telegram Listener (Postponed; Daily Scan Remains)

## Summary
Add a persistent Telegram listener mode that safely coexists with the daily scheduled scan, without racing for updates or corrupting state. For now, keep the current scheduled run as the only production path.

## Background
We added a long-poll command (`python -m stockbot telegram-listen`) that listens for incoming Telegram messages and processes commands such as `/log on`. Today, the daily scan (`stockbot scan`) also calls `process_telegram_commands`, which can consume updates independently. Running both at the same time can lead to:
- Command updates being consumed by one process and not the other.
- Shared state file updates happening concurrently.

## Goals
- Allow continuous Telegram command handling without impacting daily scans.
- Prevent duplicate or missed command processing.
- Keep state file writes safe when multiple processes run.
- Provide a clear operational strategy (listener on/off, scheduling rules).

## Non-Goals
- No new trading logic or indicator changes.
- No migration to webhooks or external queueing system (yet).

## Current Decision
Remain on scheduled runs only. Do not enable `telegram-listen` in production until the items below are addressed.

## Proposed Work
1. Add a config flag to disable command sync during scans when a listener is enabled.
   - Example: `TELEGRAM_LISTENER_ENABLED=true` in `.env`.
   - If enabled, `stockbot scan` skips `process_telegram_commands`.
2. Add file-level locking for `state.json` updates.
   - Protect `save_state` with a simple lock to avoid overlapping writes.
3. Add a systemd service template for the listener (optional).
   - Ensure it does not run if daily-only mode is desired.
4. Add monitoring/logging for listener health.
   - Log poll errors and last-update-id progression.
5. Document the operational modes in `README.md` and `operations.md`.

## Acceptance Criteria
- Running `telegram-listen` while the daily scan runs does not lose commands.
- State file remains valid under concurrent access.
- Clear guidance exists on when to enable/disable listener.
- Documented rollback path to “daily scan only”.

## Testing Plan
- Run listener in a separate terminal and send `/log on`.
- Trigger a scan manually while listener is running.
- Confirm that:
  - The command is applied once.
  - `state.json` remains valid JSON.
  - No duplicate or missed command acknowledgements.

## Risks
- Conflicting update consumption from Telegram polling.
- State file corruption or partial writes under concurrency.
- Operational confusion if both modes are active without safeguards.

## Open Questions
- Do we want listener mode to always be enabled on production?
- Should listener run under systemd or via a separate process manager?
- Do we need a webhook-based design for lower latency?
