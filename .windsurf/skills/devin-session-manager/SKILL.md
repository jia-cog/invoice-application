---
name: devin-session-manager
description: Interface with the Devin API for session management. Use this skill when the user wants to create Devin sessions (tasks), check on session status, list sessions, send messages to sessions, terminate or archive sessions, or manage scheduled sessions. Covers all Devin v3 API session lifecycle operations including creating tasks, polling for completion, and reviewing results.
---

# Devin Session Manager

Manage Devin sessions (tasks) via the Devin v3 API. All endpoints require Bearer token authentication with a service user credential (prefix: `cog_`).

**Base URL**: `https://api.devin.ai`

## Authentication

All requests require a Bearer token in the `Authorization` header:

```
Authorization: Bearer cog_<your_token>
```

The token must be stored securely. Never hardcode it. Use environment variables:

```bash
export DEVIN_API_TOKEN="cog_..."
```

If the user does not specify an organization ID, use the one from the environment variable `DEVIN_ORG_ID`.

## Core Workflow

### 1. Create a Session (Submit a Task)

```bash
curl -X POST "https://api.devin.ai/v3beta1/organizations/{org_id}/sessions" \
  -H "Authorization: Bearer $DEVIN_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Your task description here",
    "title": "Optional title",
    "tags": ["optional-tag"],
    "repos": ["org/repo-name"],
    "playbook_id": "optional-playbook-id",
    "max_acu_limit": 10
  }'
```

**Required field**: `prompt` (the task description).

**Optional fields**:
- **title** - Display title for the session
- **tags** - String array of tags for filtering
- **repos** - Repositories to make available
- **playbook_id** - Playbook to guide Devin's approach
- **max_acu_limit** - Cap ACU consumption
- **secret_ids** - Org-level secrets to attach
- **session_secrets** - Inline key/value secrets (each with `key`, `value`, optional `sensitive` boolean)
- **session_links** - URLs for Devin to reference
- **knowledge_ids** - Knowledge notes to attach
- **attachment_urls** - File attachment URLs
- **structured_output_schema** - JSON Schema (Draft 7) for structured output validation
- **advanced_mode** - One of: `analyze`, `create`, `improve`, `batch`, `manage`
- **bypass_approval** - Skip deploy approval gates
- **child_playbook_id** - Playbook for child sessions
- **create_as_user_id** - Create on behalf of another user

**Response**: `SessionResponse` object with `session_id`, `url`, `status`, etc.

### 2. Check Session Status (Poll for Completion)

```bash
curl "https://api.devin.ai/v3beta1/organizations/{org_id}/sessions/{session_id}" \
  -H "Authorization: Bearer $DEVIN_API_TOKEN"
```

**Session statuses**:
- **new** - Queued, not yet started
- **claimed** - Picked up by a worker
- **running** - Actively executing
- **suspended** - Paused/sleeping (can be resumed by sending a message)
- **resuming** - Waking up from suspended
- **exit** - Completed successfully
- **error** - Failed

Poll until status is `exit`, `error`, or `suspended`. A reasonable polling interval is 30-60 seconds.

### 3. Send a Message to a Session

Resume a suspended session or provide follow-up instructions:

```bash
curl -X POST "https://api.devin.ai/v3beta1/organizations/{org_id}/sessions/{session_id}/messages" \
  -H "Authorization: Bearer $DEVIN_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Your follow-up instructions"}'
```

Sending a message to a suspended session automatically resumes it.

### 4. List Sessions

```bash
curl "https://api.devin.ai/v3beta1/organizations/{org_id}/sessions?first=20" \
  -H "Authorization: Bearer $DEVIN_API_TOKEN"
```

**Filter parameters**:
- **session_ids** - Filter by specific IDs
- **created_after** / **created_before** - Unix timestamps
- **updated_after** / **updated_before** - Unix timestamps
- **tags** - Filter by tags
- **playbook_id** - Filter by playbook
- **origins** - Filter by origin: `webapp`, `slack`, `teams`, `api`, `linear`, `jira`, `scheduled`, `other`
- **schedule_id** - Filter by schedule
- **first** - Page size (1-200, default 100)
- **after** - Cursor for pagination

**Response** is paginated: use `end_cursor` and `has_next_page` to iterate.

### 5. Terminate a Session

```bash
curl -X DELETE "https://api.devin.ai/v3beta1/organizations/{org_id}/sessions/{session_id}?archive=false" \
  -H "Authorization: Bearer $DEVIN_API_TOKEN"
```

Set `archive=true` to also archive the session.

### 6. Archive a Session

```bash
curl -X POST "https://api.devin.ai/v3beta1/organizations/{org_id}/sessions/{session_id}/archive" \
  -H "Authorization: Bearer $DEVIN_API_TOKEN"
```

Archives the session and puts it to sleep if currently running.

## Enterprise-Level Session Endpoints

For cross-org visibility, use the enterprise endpoints:

- **List all sessions**: `GET /v3beta1/enterprise/sessions` (supports `org_ids` filter for cross-org queries)
- **Get session**: `GET /v3beta1/enterprise/sessions/{session_id}`
- **Send message**: `POST /v3beta1/enterprise/sessions/{session_id}/messages`

These accept the same parameters as org-level endpoints, plus an optional `org_id` query param.

## Scheduled Sessions

Manage recurring tasks. See [references/api-reference.md](references/api-reference.md) for full schedule CRUD details.

- **Create**: `POST /v3beta1/organizations/{org_id}/schedules` — requires `name`, `prompt`, `frequency` (cron expression)
- **List**: `GET /v3beta1/organizations/{org_id}/schedules`
- **Get**: `GET /v3beta1/organizations/{org_id}/schedules/{schedule_id}`
- **Update**: `PATCH /v3beta1/organizations/{org_id}/schedules/{schedule_id}`
- **Delete**: `DELETE /v3beta1/organizations/{org_id}/schedules/{schedule_id}`

## SessionResponse Fields

Key fields returned on every session object:

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Unique session identifier |
| `url` | string | Web URL to view the session |
| `status` | string | One of: new, claimed, running, exit, error, suspended, resuming |
| `title` | string? | Session title |
| `tags` | string[] | Tags attached to the session |
| `org_id` | string | Organization ID |
| `user_id` | string? | Creator's user ID |
| `created_at` | integer | Unix timestamp |
| `updated_at` | integer | Unix timestamp |
| `acus_consumed` | number | ACUs used so far |
| `pull_requests` | array | PRs created (each has `pr_url` and `pr_state`) |
| `structured_output` | object? | Validated structured output (only on get/list) |
| `is_archived` | boolean | Whether session is archived |
| `is_advanced` | boolean | Whether session used advanced mode |
| `parent_session_id` | string? | Parent session if this is a child |
| `child_session_ids` | string[]? | Child session IDs |

## Queue Status

Check enterprise queue health:

```bash
curl "https://api.devin.ai/v3beta1/enterprise/queue" \
  -H "Authorization: Bearer $DEVIN_API_TOKEN"
```

Returns `queue_size` (number of queued sessions) and `status` (`normal`, `elevated`, or `high`).

## Detailed API Reference

For full endpoint details including all request/response schemas, schedule management, and consumption tracking, see [references/api-reference.md](references/api-reference.md).
