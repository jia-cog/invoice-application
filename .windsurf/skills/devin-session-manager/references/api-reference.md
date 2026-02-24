# Devin API v3 — Session Management Reference

Complete endpoint reference for session management and related APIs.

## Table of Contents

- [Organization Session Endpoints](#organization-session-endpoints)
- [Enterprise Session Endpoints](#enterprise-session-endpoints)
- [Schedule Endpoints](#schedule-endpoints)
- [Session Consumption Endpoints](#session-consumption-endpoints)
- [Queue Endpoint](#queue-endpoint)
- [Request/Response Schemas](#requestresponse-schemas)

---

## Organization Session Endpoints

### Create Session

`POST /v3beta1/organizations/{org_id}/sessions`

Create a new Devin session (task).

**Path parameters**:
- `org_id` (string, required)

**Request body** (`SessionCreateRequest`):

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | Yes | Task description |
| `title` | string | No | Display title |
| `tags` | string[] | No | Tags for filtering |
| `repos` | string[] | No | Repository paths (e.g. `org/repo`) |
| `playbook_id` | string | No | Playbook to guide execution |
| `max_acu_limit` | integer | No | ACU consumption cap |
| `secret_ids` | string[] | No | Org-level secret IDs to attach |
| `session_secrets` | SessionSecretInput[] | No | Inline secrets |
| `session_links` | string[] | No | URLs for Devin to reference |
| `knowledge_ids` | string[] | No | Knowledge note IDs |
| `attachment_urls` | string[] | No | Attachment URLs (valid URIs) |
| `structured_output_schema` | object | No | JSON Schema (Draft 7) for output validation, max 64KB, self-contained |
| `advanced_mode` | string | No | One of: `analyze`, `create`, `improve`, `batch`, `manage` |
| `bypass_approval` | boolean | No | Skip deploy approval gates |
| `child_playbook_id` | string | No | Playbook for child sessions |
| `create_as_user_id` | string | No | Create on behalf of another user |

**Response**: `SessionResponse` (200)

---

### List Sessions

`GET /v3beta1/organizations/{org_id}/sessions`

**Path parameters**:
- `org_id` (string, required)

**Query parameters**:

| Param | Type | Default | Description |
|---|---|---|---|
| `first` | integer | 100 | Page size (1-200) |
| `after` | string | — | Pagination cursor |
| `session_ids` | string[] | — | Filter by session IDs |
| `created_after` | integer | — | Unix timestamp lower bound |
| `created_before` | integer | — | Unix timestamp upper bound |
| `updated_after` | integer | — | Unix timestamp lower bound |
| `updated_before` | integer | — | Unix timestamp upper bound |
| `tags` | string[] | — | Filter by tags |
| `playbook_id` | string | — | Filter by playbook |
| `origins` | string[] | — | Filter by origin: `webapp`, `slack`, `teams`, `api`, `linear`, `jira`, `scheduled`, `other` |
| `schedule_id` | string | — | Filter by schedule |

**Response**: `PaginatedResponse[SessionResponse]` (200)

Paginated response fields:
- `items` — array of `SessionResponse`
- `has_next_page` — boolean
- `end_cursor` — string (use as `after` for next page)
- `total` — integer (optional)

---

### Get Session

`GET /v3beta1/organizations/{org_id}/sessions/{devin_id}`

**Path parameters**:
- `org_id` (string, required)
- `devin_id` (string, required) — the session ID

**Response**: `SessionResponse` (200)

---

### Terminate Session

`DELETE /v3beta1/organizations/{org_id}/sessions/{devin_id}`

**Path parameters**:
- `org_id` (string, required)
- `devin_id` (string, required)

**Query parameters**:
- `archive` (boolean, default `false`) — also archive the session

**Response**: `SessionResponse` (200)

---

### Archive Session

`POST /v3beta1/organizations/{org_id}/sessions/{devin_id}/archive`

Archives the session and puts it to sleep if currently running.

**Path parameters**:
- `org_id` (string, required)
- `devin_id` (string, required)

**Response**: `SessionResponse` (200)

---

### Send Message to Session

`POST /v3beta1/organizations/{org_id}/sessions/{devin_id}/messages`

Send a follow-up message. Automatically resumes suspended sessions.

**Path parameters**:
- `org_id` (string, required)
- `devin_id` (string, required)

**Request body** (`SessionMessageCreateRequest`):

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | Message content |
| `message_as_user_id` | string | No | Send as another user |

**Response**: `SessionResponse` (200)

---

## Enterprise Session Endpoints

These provide cross-organization visibility.

### List Enterprise Sessions

`GET /v3beta1/enterprise/sessions`

Same query parameters as org-level list, plus:
- `org_ids` (string[]) — filter by organization IDs

**Response**: `PaginatedResponse[SessionResponse]` (200)

### Get Enterprise Session

`GET /v3beta1/enterprise/sessions/{devin_id}`

**Path parameters**:
- `devin_id` (string, required)

**Query parameters**:
- `org_id` (string, optional)

**Response**: `SessionResponse` (200)

### Send Message (Enterprise)

`POST /v3beta1/enterprise/sessions/{devin_id}/messages`

**Path parameters**:
- `devin_id` (string, required)

**Query parameters**:
- `org_id` (string, optional)

**Request body**: Same as org-level `SessionMessageCreateRequest`.

**Response**: `SessionResponse` (200)

---

## Schedule Endpoints

Manage recurring/scheduled sessions.

### Create Schedule

`POST /v3beta1/organizations/{org_id}/schedules`

**Request body** (`ScheduleCreateRequest`):

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Schedule name |
| `prompt` | string | Yes | Task prompt |
| `frequency` | string | Yes | Cron expression |
| `agent` | string | No | `devin` (default), `data_analyst`, or `advanced` |
| `notify_on` | string | No | `failure` (default), `always`, or `never` |
| `playbook_id` | string | No | Playbook to use |
| `create_as_user_id` | string | No | Create on behalf of another user |

**Response**: `ScheduleResponse` (200)

### List Schedules

`GET /v3beta1/organizations/{org_id}/schedules`

**Query parameters**:
- `limit` (integer, default 50, max 100)
- `offset` (integer, default 0)

**Response**: `PaginatedResponse[ScheduleResponse]` (200)

### Get Schedule

`GET /v3beta1/organizations/{org_id}/schedules/{schedule_id}`

**Response**: `ScheduleResponse` (200)

### Update Schedule

`PATCH /v3beta1/organizations/{org_id}/schedules/{schedule_id}`

**Request body** (`ScheduleUpdateRequest`) — all fields optional:

| Field | Type | Description |
|---|---|---|
| `name` | string | Updated name |
| `prompt` | string | Updated prompt |
| `frequency` | string | Updated cron expression |
| `enabled` | boolean | Enable/disable |
| `agent` | string | `devin`, `data_analyst`, or `advanced` |
| `notify_on` | string | `failure`, `always`, or `never` |
| `playbook_id` | string | Updated playbook |

**Response**: `ScheduleResponse` (200)

### Delete Schedule

`DELETE /v3beta1/organizations/{org_id}/schedules/{schedule_id}`

Soft-deletes the schedule.

**Response**: `ScheduleResponse` (200)

### ScheduleResponse Fields

| Field | Type | Description |
|---|---|---|
| `scheduled_session_id` | string | Unique schedule identifier |
| `org_id` | string | Organization ID |
| `created_by` | string? | Creator user ID |
| `name` | string | Schedule name |
| `prompt` | string | Task prompt |
| `playbook` | PlaybookInfo? | Attached playbook info |
| `frequency` | string | Cron expression |
| `agent` | string | Agent type |
| `enabled` | boolean | Whether schedule is active |
| `last_executed_at` | datetime? | Last execution time |
| `created_at` | datetime | Creation time |
| `updated_at` | datetime | Last update time |
| `last_error_at` | datetime? | Last error time |
| `last_error_message` | string? | Last error message |
| `consecutive_failures` | integer | Consecutive failure count |
| `notify_on` | string | Notification setting |

---

## Session Consumption Endpoints

Track ACU consumption for sessions.

### Get Session Daily Consumption

`GET /v3beta1/enterprise/consumption/daily/sessions/{session_id}`

**Query parameters**:
- `time_before` (integer, optional) — Unix timestamp
- `time_after` (integer, optional) — Unix timestamp

**Response**: `ConsumptionResponse` (200)

```json
{
  "total_acus": 5.2,
  "consumption_by_date": [
    {
      "date": 1733385600,
      "acus": 3.1,
      "acus_by_product": {
        "devin": 2.5,
        "cascade": 0.4,
        "terminal": 0.2
      }
    }
  ]
}
```

**Timezone note**: Billing cycles use midnight PST (08:00:00 UTC) as the day boundary.

---

## Queue Endpoint

### Get Queue Status

`GET /v3beta1/enterprise/queue`

Returns the number of queued sessions (status: new, resuming, claimed) and a health indicator.

**Response**: `QueueResponse` (200)

```json
{
  "queue_size": 12,
  "status": "normal"
}
```

Status values: `normal`, `elevated`, `high`.

---

## Request/Response Schemas

### SessionResponse

```json
{
  "session_id": "string",
  "url": "string",
  "status": "new | claimed | running | exit | error | suspended | resuming",
  "title": "string | null",
  "tags": ["string"],
  "org_id": "string",
  "user_id": "string | null",
  "created_at": 1700000000,
  "updated_at": 1700000000,
  "acus_consumed": 0.0,
  "pull_requests": [
    {"pr_url": "string", "pr_state": "string | null"}
  ],
  "structured_output": {"key": "value"} ,
  "is_archived": false,
  "is_advanced": false,
  "parent_session_id": "string | null",
  "child_session_ids": ["string"] 
}
```

### SessionCreateRequest

```json
{
  "prompt": "string (required)",
  "title": "string",
  "tags": ["string"],
  "repos": ["org/repo"],
  "playbook_id": "string",
  "max_acu_limit": 10,
  "secret_ids": ["string"],
  "session_secrets": [
    {"key": "MY_KEY", "value": "secret_value", "sensitive": true}
  ],
  "session_links": ["https://example.com"],
  "knowledge_ids": ["string"],
  "attachment_urls": ["https://example.com/file.pdf"],
  "structured_output_schema": {},
  "advanced_mode": "analyze | create | improve | batch | manage",
  "bypass_approval": false,
  "child_playbook_id": "string",
  "create_as_user_id": "string"
}
```

### SessionSecretInput

```json
{
  "key": "string (1-256 chars, required)",
  "value": "string (max 65536 chars, required)",
  "sensitive": true
}
```

### SessionMessageCreateRequest

```json
{
  "message": "string (required)",
  "message_as_user_id": "string"
}
```

### PaginatedResponse

All list endpoints return:

```json
{
  "items": [],
  "has_next_page": false,
  "end_cursor": "string | null",
  "total": 42
}
```

Iterate pages by passing `end_cursor` as the `after` query parameter until `has_next_page` is `false`.
