# SQL Formatter API

Format messy SQL queries into readable, standardized statements.

## Problem it solves

Developers constantly share unformatted SQL in Slack, email, and code reviews. No quick HTTP API exists to format SQL without installing heavy libraries locally.

## Endpoints

### `GET /health`
Health check endpoint (no auth required)

### `POST /format`
Format a SQL query with customizable options.

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: your-api-key`

**Body:**
```json
{
  "sql": "select id,name from users where active=1",
  "keyword_case": "upper",
  "identifier_case": "lower",
  "strip_comments": false,
  "indent_columns": true
}
```

**Response:**
```json
{
  "formatted": "SELECT id,\n       name\nFROM   users\nWHERE  active = 1",
  "original_length": 35,
  "formatted_length": 62
}
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sql` | string | required | SQL query to format |
| `keyword_case` | string | "upper" | Keywords: "upper", "lower", or "capitalize" |
| `identifier_case` | string | "lower" | Identifiers: "upper", "lower", or "capitalize" |
| `strip_comments` | bool | false | Remove SQL comments |
| `indent_columns` | bool | true | Align column names |

## Example

```bash
curl -X POST https://sql-formatter.vercel.app/format \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key" \
  -d '{"sql": "select * from users where id=1 order by name"}'
```

## Pricing

- 100 requests/minute free tier
- $19/month for 10,000 requests
- $49/month for 100,000 requests