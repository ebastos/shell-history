# API Reference

Complete REST API documentation for Shell History.

## Base URL

```
http://localhost:3000/api/v1
```

## Authentication

> [!IMPORTANT]
> All endpoints (except `/health`) require authentication via the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:3000/api/v1/commands
```

Get your API key from the web interface at http://localhost:3000/account.

---

## Endpoints

### Health Check

```http
GET /health
```

Check if the API is running. No authentication required.

---

### Commands

#### List/Search Commands

```http
GET /commands
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Full-text search query |
| `hostname` | string | Filter by hostname |
| `username` | string | Filter by username |
| `start_date` | string | Filter from date (YYYY-MM-DD) |
| `end_date` | string | Filter to date (YYYY-MM-DD) |
| `exit_code` | integer | Filter by exit code |
| `limit` | integer | Max results (default: 50) |
| `offset` | integer | Skip results for pagination |

**Example:**

```bash
# Search for docker commands
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:3000/api/v1/commands?q=docker"

# Filter by hostname and exit code
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:3000/api/v1/commands?hostname=my-server&exit_code=0"

# Date range filter
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:3000/api/v1/commands?start_date=2024-01-01&end_date=2024-12-31"
```

**Response:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "command": "docker-compose up -d",
    "hostname": "my-server",
    "username": "alice",
    "cwd": "/home/alice/project",
    "exit_code": 0,
    "timestamp": "2024-01-15T10:30:00Z",
    "session_id": "abc123",
    "redacted": false
  }
]
```

#### Create Command

```http
POST /commands
```

**Request Body:**

```json
{
  "command": "ls -la",
  "hostname": "my-server",
  "username": "alice",
  "cwd": "/home/alice",
  "exit_code": 0,
  "session_id": "optional-session-id"
}
```

**Example:**

```bash
curl -X POST http://localhost:3000/api/v1/commands \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "command": "ls -la",
    "hostname": "my-server",
    "username": "alice",
    "cwd": "/home/alice",
    "exit_code": 0
  }'
```

#### Get Command

```http
GET /commands/{id}
```

**Example:**

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:3000/api/v1/commands/550e8400-e29b-41d4-a716-446655440000
```

#### Delete Command

```http
DELETE /commands/{id}
```

**Example:**

```bash
curl -X DELETE \
  -H "X-API-Key: $API_KEY" \
  http://localhost:3000/api/v1/commands/550e8400-e29b-41d4-a716-446655440000
```

---

### Hosts

#### List Hosts

```http
GET /hosts
```

Returns all hosts that have sent commands.

**Example:**

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:3000/api/v1/hosts
```

**Response:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "hostname": "my-server",
    "ip_address": "192.168.1.100",
    "os_type": "linux",
    "is_active": true,
    "last_seen": "2024-01-15T10:30:00Z"
  }
]
```

#### Get Host

```http
GET /hosts/{id}
```

#### Update Host

```http
PUT /hosts/{id}
```

**Request Body:**

```json
{
  "hostname": "new-hostname",
  "is_active": true
}
```

---

### Users

#### Get Current User

```http
GET /users/me
```

Returns information about the authenticated user.

**Example:**

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:3000/api/v1/users/me
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "username": "alice",
  "email": "alice@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "api_key": "sh_..."
}
```

#### Regenerate API Key

```http
POST /users/me/api-key/regenerate
```

Deactivates all existing API keys and creates a new one.

**Example:**

```bash
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  http://localhost:3000/api/v1/users/me/api-key/regenerate
```

> [!NOTE]
> For managing multiple API keys (create, revoke, view usage), use the web interface at http://localhost:3000/account.

---

### Statistics

```http
GET /stats
```

Returns usage statistics for the authenticated user.

**Example:**

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:3000/api/v1/stats
```

**Response:**

```json
{
  "total_commands": 1234,
  "total_hosts": 3,
  "commands_today": 45,
  "top_commands": [
    {"command": "git status", "count": 150},
    {"command": "ls", "count": 120}
  ]
}
```

---

### Admin Endpoints

> [!IMPORTANT]
> These endpoints require admin authentication via `X-API-Key` header from an admin user.

#### List Users

```http
GET /users
```

#### Create User

```http
POST /users
```

**Request Body:**

```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "secure-password",
  "role": "user"
}
```

**Role options:** `user`, `admin`, `readonly`

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

**Common HTTP Status Codes:**

| Code | Description |
|------|-------------|
| 400 | Bad Request — Invalid parameters |
| 401 | Unauthorized — Missing or invalid API key |
| 403 | Forbidden — Insufficient permissions |
| 404 | Not Found — Resource doesn't exist |
| 422 | Unprocessable Entity — Validation error |
| 500 | Internal Server Error |

---

## Rate Limiting

Currently, there is no rate limiting. For production deployments, consider adding rate limiting at the reverse proxy level.

---

## Web UI Routes

The following routes serve the HTMX-based web interface (session authentication):

| Route | Description |
|-------|-------------|
| `/` | Home / redirect to history |
| `/login` | Login page |
| `/logout` | Logout and redirect |
| `/history` | Search interface |
| `/account` | Account management |
| `/admin` | Admin dashboard (admin only) |
