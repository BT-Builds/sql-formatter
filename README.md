# SQL Formatter API

Format and beautify SQL queries with proper indentation and uppercase keywords.

## Endpoints

### POST /format
Format SQL with options:
```json
{
  "sql": "select * from users where id = 1;",
  "uppercase": true,
  "indent": "  ",
  "lines_between_queries": true
}
```

### POST /format-simple
Quick format with defaults:
```json
{
  "sql": "select * from users;"
}
```

### GET /health
Health check endpoint.

## Usage
```bash
curl -X POST https://sql-formatter-gamma.vercel.app/format \
  -H "Content-Type: application/json" \
  -d '{"sql": "select id, name from users where active = true limit 10;"}'
```

## Authentication
Include `Authorization: Bearer ***` header. Free tier: 100 requests/hour.

## Use Cases
- Clean up messy SQL queries
- Standardize SQL formatting across teams
- SQL linting in CI/CD pipelines
- Format SQL in admin panels or dashboards
