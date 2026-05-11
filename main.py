import os
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
import httpx


OXR_APP_ID = os.environ.get("OXR_APP_ID", "")
BASE_URL = "https://openexchangerates.org/api"

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=15.0)
    yield
    await http_client.aclose()


app = FastAPI(title="Open Exchange Rates Wrapper", lifespan=lifespan)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_app_id() -> str:
    key = OXR_APP_ID or os.environ.get("OXR_APP_ID", "")
    if not key:
        raise HTTPException(status_code=503, detail="OXR_APP_ID not configured")
    return key


async def _oxr_request(endpoint: str, params: dict | None = None) -> dict:
    """Make a request to Open Exchange Rates."""
    if params is None:
        params = {}
    params["app_id"] = _get_app_id()
    url = f"{BASE_URL}/{endpoint}"

    try:
        response = await http_client.get(url, params=params)
        if response.status_code == 429:
            raise HTTPException(status_code=429, detail="Open Exchange Rates rate limit exceeded")
        if response.status_code == 401:
            raise HTTPException(status_code=503, detail="Invalid OXR app_id")
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail="OXR feature not available on your plan")
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            raise HTTPException(status_code=400, detail=data.get("description", "OXR API error"))

        return data
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Network error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unexpected error: {str(e)}")


# ── Endpoints ────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "name": "Open Exchange Rates Wrapper",
        "description": "170+ fiat currency exchange rates, real-time and historical, with conversion",
        "endpoints": [
            {"path": "/latest", "description": "Get latest exchange rates (base USD)"},
            {"path": "/convert?from=USD&to=EUR&amount=100", "description": "Convert currency"},
            {"path": "/historical?date=2024-01-15", "description": "Get historical rates"},
            {"path": "/currencies", "description": "List all supported currencies"},
            {"path": "/health", "description": "Health check"},
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": _ts()}


@app.get("/latest")
async def get_latest(
    base: str = Query("USD", description="Base currency (USD on free plan)"),
    symbols: str = Query(None, description="Comma-separated currency codes to filter (e.g., EUR,GBP,JPY)"),
):
    """Get latest exchange rates."""
    params = {}
    if base.upper() != "USD":
        params["base"] = base.upper()
    if symbols:
        params["symbols"] = symbols.upper()

    data = await _oxr_request("latest.json", params)

    return {
        "base": data.get("base", "USD"),
        "rates": data.get("rates", {}),
        "rate_count": len(data.get("rates", {})),
        "last_updated": datetime.fromtimestamp(data.get("timestamp", 0), tz=timezone.utc).isoformat() if data.get("timestamp") else None,
        "timestamp": _ts(),
    }


@app.get("/convert")
async def convert_currency(
    from_currency: str = Query(..., description="From currency (e.g., USD)", alias="from"),
    to_currency: str = Query(..., description="To currency (e.g., EUR)", alias="to"),
    amount: float = Query(1.0, description="Amount to convert"),
):
    """Convert between currencies using latest rates."""
    # Free tier doesn't support /convert endpoint, so we compute from /latest
    data = await _oxr_request("latest.json")
    rates = data.get("rates", {})

    from_upper = from_currency.upper()
    to_upper = to_currency.upper()

    if from_upper not in rates and from_upper != "USD":
        raise HTTPException(status_code=404, detail=f"Currency not found: {from_upper}")
    if to_upper not in rates and to_upper != "USD":
        raise HTTPException(status_code=404, detail=f"Currency not found: {to_upper}")

    # Convert: amount in from_currency → USD → to_currency
    from_rate = rates.get(from_upper, 1.0)  # USD = 1.0
    to_rate = rates.get(to_upper, 1.0)

    usd_amount = amount / from_rate
    result = usd_amount * to_rate
    effective_rate = to_rate / from_rate

    return {
        "from": from_upper,
        "to": to_upper,
        "amount": amount,
        "result": round(result, 6),
        "rate": round(effective_rate, 6),
        "timestamp": _ts(),
    }


@app.get("/historical")
async def get_historical(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    base: str = Query("USD", description="Base currency"),
    symbols: str = Query(None, description="Comma-separated currency codes"),
):
    """Get historical exchange rates for a specific date."""
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")

    params = {}
    if base.upper() != "USD":
        params["base"] = base.upper()
    if symbols:
        params["symbols"] = symbols.upper()

    data = await _oxr_request(f"historical/{date}.json", params)

    return {
        "date": date,
        "base": data.get("base", "USD"),
        "rates": data.get("rates", {}),
        "rate_count": len(data.get("rates", {})),
        "timestamp": _ts(),
    }


@app.get("/currencies")
async def list_currencies():
    """List all supported currencies with their names."""
    # This endpoint doesn't need an API key
    try:
        response = await http_client.get(f"{BASE_URL}/currencies.json")
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch currencies: {str(e)}")

    return {
        "currencies": data,
        "count": len(data),
        "timestamp": _ts(),
    }
