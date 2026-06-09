import os
import re
import time
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
from mangum import Mangum

app = FastAPI(title="SQL Formatter API", version="1.0.0")
# === BT Builds Standard Middleware (auto-injected) ===
from fastapi.middleware.cors import CORSMiddleware as _BTCors
app.add_middleware(_BTCors, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], expose_headers=["X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset"])

@app.middleware("http")
async def _bt_add_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "btbuilds"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

handler = Mangum(app)

# Rate limiting storage (simple in-memory)
rate_limit_storage = {}

API_KEY=os.environ.get("API_KEY", "dev-key-change-me")

KEYWORDS = [
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "LIKE", "BETWEEN",
    "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "GROUP BY", "ORDER BY",
    "HAVING", "LIMIT", "OFFSET", "AS", "DISTINCT", "COUNT", "SUM", "AVG",
    "MIN", "MAX", "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE",
    "CREATE TABLE", "DROP TABLE", "ALTER TABLE", "PRIMARY KEY", "FOREIGN KEY",
    "REFERENCES", "INDEX", "UNIQUE", "NOT NULL", "DEFAULT", "CHECK", "CONSTRAINT",
    "WHEN", "THEN", "ELSE", "END", "CASE", "IF", "IS NULL", "IS NOT NULL",
    "TRUE", "FALSE", "WITH", "RECURSIVE", "UNION", "EXCEPT", "INTERSECT", "ALL",
    "ASC", "DESC", "CAST", "CONVERT", "COALESCE", "NULLIF", "EXISTS", "ANY", "SOME"
]

def check_rate_limit(client_id: str = "default"):
    """Simple in-memory rate limiting: 100 requests per hour"""
    current_hour = int(time.time() / 3600)
    key = f"{client_id}:{current_hour}"
    if key not in rate_limit_storage:
        rate_limit_storage[key] = 0
    if rate_limit_storage[key] >= 100:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    rate_limit_storage[key] += 1
    return True

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """Verify API key for protected routes"""
    if not credentials or credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

class SQLFormatRequest(BaseModel):
    sql: str
    uppercase: bool = True
    indent: str = "  "
    lines_between_queries: bool = True

class SQLFormatResponse(BaseModel):
    formatted: str
    original: str

class HealthResponse(BaseModel):
    status: str

class BulkRequest(BaseModel):
    items: list

class BulkResponse(BaseModel):
    results: list
    total: int
    successful: int

def format_sql(sql: str, uppercase: bool = True, indent: str = "  ", lines_between: bool = True) -> str:
    """Format SQL with proper indentation and uppercase keywords"""
    # Normalize whitespace
    sql = re.sub(r'\s+', ' ', sql.strip())

    # Uppercase keywords if requested (preserving strings)
    if uppercase:
        # Find string literals to preserve
        strings = re.findall(r"('[^']*')", sql)
        for s in strings:
            sql = sql.replace(s, f"__STRING_{strings.index(s)}__")

        # Uppercase keywords
        for keyword in sorted(KEYWORDS, key=len, reverse=True):
            pattern = r'\b' + keyword + r'\b'
            sql = re.sub(pattern, keyword, sql, flags=re.IGNORECASE)

        # Restore strings
        for i, s in enumerate(strings):
            sql = sql.replace(f"__STRING_{i}__", s)

    # Split by semicolons for multiple statements
    statements = sql.split(';')

    formatted_statements = []
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue

        formatted = stmt

        # Add newlines before major clauses (case-insensitive)
        clauses = ["GROUP BY", "ORDER BY", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "OUTER JOIN",
                   "INSERT INTO", "CREATE TABLE", "DROP TABLE", "ALTER TABLE", "PRIMARY KEY", "FOREIGN KEY"]

        for clause in clauses:
            formatted = re.sub(r'\s+' + clause + r'\s+', f'\n{clause} ', formatted, flags=re.IGNORECASE)

        # Simple clauses
        simple_clauses = ["SELECT", "FROM", "WHERE", "HAVING", "LIMIT", "OFFSET", "SET", "VALUES", "JOIN", "ON", "AND", "OR"]
        for clause in simple_clauses:
            formatted = re.sub(r'\s+' + clause + r'\s+', f'\n{clause} ', formatted, flags=re.IGNORECASE)

        # Clean up and add indentation
        lines = formatted.split('\n')
        indent_level = 0
        result_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Adjust indent for closing parentheses
            close_before = line.count(')')
            open_in_line = line.count('(')

            # If line starts with closing paren, decrease indent first
            if line.startswith(')'):
                indent_level = max(0, indent_level - 1)

            result_lines.append(indent * indent_level + line)

            # Increase indent for opening parentheses
            indent_level += open_in_line

            # Decrease indent for closing parentheses that were opened before
            indent_level = max(0, indent_level - close_before)

        formatted_statements.append('\n'.join(result_lines))

    separator = '\n\n' if lines_between else '\n'
    return separator.join(formatted_statements).strip()

@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}

@app.post("/format", response_model=SQLFormatResponse)
async def format_sql_endpoint(request: SQLFormatRequest, _: bool = Depends(check_rate_limit)):
    if not request.sql.strip():
        raise HTTPException(status_code=400, detail="SQL query is required")

    formatted = format_sql(
        request.sql,
        uppercase=request.uppercase,
        indent=request.indent,
        lines_between=request.lines_between_queries
    )

    return SQLFormatResponse(formatted=formatted, original=request.sql)

@app.post("/format-simple")
async def format_simple(request: SQLFormatRequest, _: bool = Depends(check_rate_limit)):
    """Simple formatter with defaults"""
    formatted = format_sql(request.sql)
    return {"formatted": formatted}

@app.post("/bulk/format")
async def bulk_format(request: BulkRequest, _: bool = Depends(check_rate_limit)):
    """Format multiple SQL queries in bulk"""
    items = request.items
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    if len(items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")

    results = []
    successful = 0

    for item in items:
        try:
            sql = item.get("sql") if isinstance(item, dict) else str(item)
            uppercase = item.get("uppercase", True) if isinstance(item, dict) else True
            indent = item.get("indent", "  ") if isinstance(item, dict) else "  "
            lines_between = item.get("lines_between_queries", True) if isinstance(item, dict) else True

            formatted = format_sql(sql, uppercase=uppercase, indent=indent, lines_between=lines_between)
            results.append({"input": sql, "output": formatted, "error": None})
            successful += 1
        except Exception as e:
            results.append({"input": item.get("sql", str(item)) if isinstance(item, dict) else str(item), "output": None, "error": str(e)})

    return {"results": results, "total": len(items), "successful": successful}

@app.post("/bulk/format-simple")
async def bulk_format_simple(request: BulkRequest, _: bool = Depends(check_rate_limit)):
    """Format multiple SQL queries in bulk with defaults"""
    items = request.items
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    if len(items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")

    results = []
    successful = 0

    for item in items:
        try:
            sql = item.get("sql") if isinstance(item, dict) else str(item)
            formatted = format_sql(sql)
            results.append({"input": sql, "output": {"formatted": formatted}, "error": None})
            successful += 1
        except Exception as e:
            results.append({"input": item.get("sql", str(item)) if isinstance(item, dict) else str(item), "output": None, "error": str(e)})

    return {"results": results, "total": len(items), "successful": successful}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)