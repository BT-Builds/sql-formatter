import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import sqlparse
from sqlparse import format as sql_format

app = FastAPI(title="SQL Formatter API", version="1.0.0")

# Rate limiting storage
rate_limit_store = defaultdict(list)

def rate_limit(api_key: str = "anonymous"):
    now = time.time()
    minute_ago = now - 60
    rate_limit_store[api_key] = [t for t in rate_limit_store[api_key] if t > minute_ago]
    if len(rate_limit_store[api_key]) >= 100:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    rate_limit_store[api_key].append(now)

def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    rate_limit(x_api_key)
    return x_api_key

class SQLFormatRequest(BaseModel):
    sql: str
    keyword_case: str = "upper"
    identifier_case: str = "lower"
    strip_comments: bool = False
    indent_columns: bool = True

class SQLFormatResponse(BaseModel):
    formatted: str
    original_length: int
    formatted_length: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/format", response_model=SQLFormatResponse)
def format_sql(request: SQLFormatRequest, api_key: str = Depends(verify_api_key)):
    if not request.sql.strip():
        raise HTTPException(status_code=400, detail="SQL query cannot be empty")
    try:
        formatted = sql_format(
            request.sql,
            keyword_case=request.keyword_case,
            identifier_case=request.identifier_case,
            strip_comments=request.strip_comments,
            indent_columns=request.indent_columns,
            reindent=True,
            strip_whitespace=True
        )
        return SQLFormatResponse(
            formatted=formatted,
            original_length=len(request.sql),
            formatted_length=len(formatted)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL parsing error: {str(e)}")

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass
