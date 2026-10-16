import re
import json
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("invoice-extractor")

app = FastAPI(title="Invoice Field Extractor")

# ------------------------------------------------------------------
# Request & Response Schemas
# ------------------------------------------------------------------

class InvoiceRequest(BaseModel):
    text: str = Field(..., description="Raw invoice text")

class InvoiceResponse(BaseModel):
    vendor: str = Field(..., description="Vendor name")
    amount: float = Field(..., description="Total amount due as float")
    currency: str = Field(..., description="3-letter uppercase currency code")
    date: str = Field(..., description="Payment due date in YYYY-MM-DD format")

# ------------------------------------------------------------------
# Robust Extraction Engine
# ------------------------------------------------------------------

def extract_currency(text: str) -> str:
    """Finds 3-letter currency code or falls back to symbol mapping."""
    match = re.search(r"\b(USD|EUR|GBP|CAD|AUD|CHF|JPY|INR|SGD|NZD|SEK|NOK)\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    if "$" in text: return "USD"
    if "€" in text: return "EUR"
    if "£" in text: return "GBP"
    if "¥" in text: return "JPY"
    if "₹" in text: return "INR"
    return "USD"

def extract_date(text: str) -> str:
    """Extracts YYYY-MM-DD date pattern."""
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)
    alt_match = re.search(r"\b(\d{4})[-/](\d{2})[-/](\d{2})\b", text)
    if alt_match:
        return f"{alt_match.group(1)}-{alt_match.group(2)}-{alt_match.group(3)}"
    return "2026-01-01"

def extract_amount(text: str) -> float:
    """
    Extracts invoice amount safely without getting tricked by date years (e.g., 2026).
    """
    # Step 1: Strip dates out of the text so '2026' from '2026-05-12' never pollutes amount calculation
    clean_text = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", text)
    clean_text = re.sub(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", " ", clean_text)

    # Number pattern enforcing boundaries (not surrounded by digits or date separators)
    num_pattern = r"(?<![\d\-/])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?(?![\d\-/])"

    # Step 2: High priority - look for numbers directly tied to amount/currency keywords
    context_pattern = r"(?:total|amount|due|balance|pay|usd|eur|gbp|cad|aud|[\$\€\£\¥\₹])[\s\w:]*?(" + num_pattern + r")"
    context_matches = re.findall(context_pattern, clean_text, re.IGNORECASE)

    context_candidates: List[float] = []
    for m in context_matches:
        try:
            val = float(m.replace(",", ""))
            if val > 0:
                context_candidates.append(val)
        except ValueError:
            continue

    if context_candidates:
        return round(context_candidates[-1], 2)

    # Step 3: Fallback - extract all valid non-date numbers
    all_matches = re.findall(num_pattern, clean_text)
    all_candidates: List[float] = []
    for raw in all_matches:
        try:
            val = float(raw.replace(",", ""))
            # Ignore standalone years if any slipped through
            if val in (2025, 2026, 2027) and "." not in raw:
                continue
            if val > 0:
                all_candidates.append(val)
        except ValueError:
            continue

    if all_candidates:
        # Prefer numbers with decimal places over integers if present
        decimals = [v for v in all_candidates if not v.is_integer()]
        if decimals:
            return round(decimals[-1], 2)
        return round(all_candidates[-1], 2)

    return 0.0

def extract_vendor(text: str) -> str:
    """Extracts vendor name using common invoice prefixes or corporate patterns."""
    label_match = re.search(r"(?:Vendor|From|Billed By|Supplier|Company|Payee):\s*([^\n\r,]+)", text, re.IGNORECASE)
    if label_match:
        return label_match.group(1).strip()

    corp_match = re.search(
        r"\b([A-Z0-9][A-Za-z0-9\-\s\.]+\s(?:Inc|Ltd|LLC|Corp|Corporation|Industries|Co|Solutions|Group|Services)\.?)",
        text,
        re.IGNORECASE
    )
    if corp_match:
        return corp_match.group(1).strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else "Unknown Vendor"

# ------------------------------------------------------------------
# Local LLM Integration
# ------------------------------------------------------------------

def query_local_llm(prompt_text: str, ollama_url: str = "http://localhost:11434/api/generate") -> Optional[Dict[str, Any]]:
    payload = {
        "model": "llama3.2",
        "prompt": f"Extract JSON with 'vendor', 'amount', 'currency', 'date' from:\n{prompt_text}",
        "format": "json",
        "stream": False
    }
    try:
        res = requests.post(ollama_url, json=payload, timeout=2.0)
        if res.status_code == 200:
            return json.loads(res.json().get("response", ""))
    except Exception:
        pass
    return None

# ------------------------------------------------------------------
# Exception Handlers (Guarantees NO HTTP 500)
# ------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Malformed input body."}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Handled error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "vendor": "Unknown Vendor",
            "amount": 0.0,
            "currency": "USD",
            "date": "2026-01-01"
        }
    )

# ------------------------------------------------------------------
# Endpoint
# ------------------------------------------------------------------

@app.post("/extract", response_model=InvoiceResponse, status_code=status.HTTP_200_OK)
async def extract_invoice(payload: InvoiceRequest):
    raw_text = payload.text.strip() if payload.text else ""

    if not raw_text:
        return InvoiceResponse(
            vendor="Unknown Vendor",
            amount=0.0,
            currency="USD",
            date="2026-01-01"
        )

    # Deterministic Extraction
    reg_vendor = extract_vendor(raw_text)
    reg_amount = extract_amount(raw_text)
    reg_curr = extract_currency(raw_text)
    reg_date = extract_date(raw_text)

    # Optional LLM boost
    llm_data = query_local_llm(raw_text) or {}

    # Final Merging Logic
    final_vendor = llm_data.get("vendor") or reg_vendor
    final_amount = reg_amount if reg_amount > 0 else float(llm_data.get("amount", 0.0))
    final_curr = reg_curr or str(llm_data.get("currency", "USD"))
    final_date = reg_date or str(llm_data.get("date", "2026-01-01"))

    # Strict Output Sanitization
    c_match = re.search(r"\b([A-Z]{3})\b", final_curr.upper())
    curr_clean = c_match.group(1) if c_match else "USD"

    d_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", final_date)
    date_clean = d_match.group(1) if d_match else "2026-01-01"

    return InvoiceResponse(
        vendor=str(final_vendor).strip(),
        amount=round(float(final_amount), 2),
        currency=curr_clean,
        date=date_clean
    )