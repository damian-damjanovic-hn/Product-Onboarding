### Use FastAPI to validate CSVs against a schema

1.  **Endpoints**:
    
    - `POST /validate`: Accepts CSV file via URL or upload, optional schema, and dialect options.
    - `GET /validate`: Accepts CSV and schema URLs, with dialect options in query parameters.
2.  **Validation**:
    
    - Validates CSV content for format, structure, and optional schema.
    - Errors, warnings, and info are categorized for better insights.
3.  **Error Handling**:
    
    - Detailed error messages for invalid inputs or URL fetch failures.
4.  **Dialect Options**:
    
    - Supports custom dialect settings like delimiter and header.

```python
from fastapi import FastAPI, UploadFile, Form, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import csv
import json
import requests
from io import StringIO

app = FastAPI()

def fetch_content_from_url(url: str):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching content from URL: {e}")

def validate_csv(csv_content: str, schema: Optional[dict] = None, dialect: Optional[dict] = None):
    errors = []
    warnings = []
    info = []

    # Parse CSV with optional dialect
    try:
        if dialect:
            csv_reader = csv.reader(StringIO(csv_content), **dialect)
        else:
            csv_reader = csv.reader(StringIO(csv_content))
        headers = next(csv_reader)
    except Exception as e:
        errors.append({"type": "invalid_csv", "category": "structure", "detail": str(e)})
        return errors, warnings, info

    # Validate against schema if provided
    if schema:
        expected_headers = schema.get("headers", [])
        if set(headers) != set(expected_headers):
            errors.append({"type": "header_mismatch", "category": "schema", "detail": "Headers do not match schema."})
        else:
            info.append({"type": "headers_valid", "category": "schema"})

    # Additional CSV validation logic here if needed

    return errors, warnings, info

@app.post("/validate")
async def validate_csv_post(
    csvUrl: Optional[str] = Form(None),
    file: Optional[UploadFile] = None,
    schemaUrl: Optional[str] = Form(None),
    schema: Optional[UploadFile] = None,
    delimiter: Optional[str] = Form(None),
    header: Optional[bool] = Form(None)
):
    if not csvUrl and not file:
        raise HTTPException(status_code=400, detail="Either csvUrl or file must be provided.")

    # Fetch CSV content
    csv_content = fetch_content_from_url(csvUrl) if csvUrl else (await file.read()).decode("utf-8")

    # Fetch schema content
    schema_content = fetch_content_from_url(schemaUrl) if schemaUrl else (await schema.read()).decode("utf-8") if schema else None
    schema_dict = json.loads(schema_content) if schema_content else None

    # Dialect options
    dialect = {}
    if delimiter:
        dialect["delimiter"] = delimiter
    if header is not None:
        dialect["header"] = header

    errors, warnings, info = validate_csv(csv_content, schema_dict, dialect)

    return JSONResponse({
        "validation": {
            "state": "invalid" if errors else "valid",
            "errors": errors,
            "warnings": warnings,
            "info": info,
        }
    })

@app.get("/validate")
async def validate_csv_get(
    csvUrl: str = Query(...),
    schemaUrl: Optional[str] = Query(None),
    delimiter: Optional[str] = Query(None),
    header: Optional[bool] = Query(None),
    format: Optional[str] = Query(None)
):
    # Fetch CSV content
    csv_content = fetch_content_from_url(csvUrl)

    # Fetch schema content
    schema_content = fetch_content_from_url(schemaUrl) if schemaUrl else None
    schema_dict = json.loads(schema_content) if schema_content else None

    # Dialect options
    dialect = {}
    if delimiter:
        dialect["delimiter"] = delimiter
    if header is not None:
        dialect["header"] = header

    errors, warnings, info = validate_csv(csv_content, schema_dict, dialect)

    if format in ["svg", "png"]:
        # Generate and return badge (Placeholder logic)
        badge = f"Validation: {'Valid' if not errors else 'Invalid'}"
        return JSONResponse({"badge": badge})

    return JSONResponse({
        "validation": {
            "state": "invalid" if errors else "valid",
            "errors": errors,
            "warnings": warnings,
            "info": info,
        }
    })

```
*run and test this app locally first
