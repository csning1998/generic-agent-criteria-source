---
name: skill-module-google-calendar
description: Stateless module to inspect, create, and manage Google Calendar events using Google Calendar tools. Mandates skill-meta-mcp-json pre/post-flight checks and skill-meta-python-engine ISO time formatting.
allowed-tools: calendar
---
# Module Google Calendar Adapter

Stateless module executing Google Calendar operations within the factory system.

## When to Use

A layer skill or user requests inspecting, listing, or creating Google Calendar events.

## Input Requirements

Mandatory prerequisites:
- Enforce `skill-meta-mcp-json` for parameter validation and error quarantine.
- Enforce `skill-meta-python-engine` for local wall-clock ISO-8601 formatting and timezone calculation.

Create Event Input:
```json
{
  "op": "create_event",
  "calendar_id": "primary",
  "summary": "Meeting Title",
  "start_time": "2026-10-15T14:00:00",
  "end_time": "2026-10-15T15:00:00",
  "time_zone": "Asia/Taipei",
  "description": "Optional notes",
  "location": "Optional location",
  "add_google_meet_url": true,
  "attendees": [{"email": "user@example.com"}],
  "notification_level": "ALL"
}
```

List Events Input:
```json
{
  "op": "list_events",
  "calendar_id": "primary",
  "start_time": "2026-10-15T00:00:00",
  "end_time": "2026-10-15T23:59:59",
  "order_by": "startTime",
  "page_size": 20
}
```

## Process

1. **Pre-flight Check (`skill-meta-mcp-json` & `skill-meta-python-engine`)**:
   - Ensure timestamps use local wall-clock ISO-8601 without `Z` or offset (e.g. `YYYY-MM-DDTHH:MM:SS`).
   - Enforce strictly typed IANA timezone (defaults to `Asia/Taipei`).
   - Title Case `summary`.
2. **Execution**:
   - For `create_event`: Call `calendar:create_event`.
   - For `list_events`: Call `calendar:list_events` with bounded `start_time` and `end_time`.
3. **Post-flight Check (`skill-meta-mcp-json`)**:
   - Check response dictionary for `isError` flag.
   - Extract event ID, HTML link, and Google Meet URL into structured output artifact.

## Output

Artifact `GoogleCalendarResult`:
```json
{
  "ok": true,
  "op": "create_event",
  "event_id": "...",
  "html_link": "https://www.google.com/calendar/event?eid=...",
  "google_meet_url": "https://meet.google.com/...",
  "error": null
}
```
