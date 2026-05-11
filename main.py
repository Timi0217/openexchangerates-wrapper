import os
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
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


HOME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Open Exchange Rates</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0a;
            color: #fff;
            padding: 24px;
            min-height: 100vh;
        }
        .container {
            max-width: 640px;
            margin: 0 auto;
            opacity: 0;
            animation: fadeIn 0.6s ease forwards;
        }
        @keyframes fadeIn {
            to { opacity: 1; }
        }
        .card {
            background: rgba(255,255,255,.03);
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 16px;
            padding: 32px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }
        h1 {
            color: #27AE60;
            font-size: 24px;
            font-family: 'Courier New', monospace;
            font-style: italic;
            font-weight: 600;
        }
        .badge {
            background: rgba(39,174,96,.2);
            color: #27AE60;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .subtitle {
            color: #888;
            font-size: 14px;
            margin-bottom: 32px;
        }
        .hero {
            text-align: center;
            margin-bottom: 32px;
            padding: 24px;
            background: rgba(39,174,96,.05);
            border-radius: 12px;
            border: 1px solid rgba(39,174,96,.1);
        }
        .hero-conversion {
            font-size: 18px;
            color: #aaa;
            margin-bottom: 12px;
        }
        .hero-result {
            font-size: 48px;
            font-family: 'Courier New', monospace;
            color: #27AE60;
            font-weight: 700;
        }
        .hero-currency {
            font-size: 28px;
            color: #27AE60;
            margin-left: 8px;
        }
        .rates-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }
        .rate-card {
            background: rgba(255,255,255,.02);
            border: 1px solid rgba(255,255,255,.05);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }
        .rate-emoji {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .rate-code {
            font-size: 12px;
            color: #888;
            margin-bottom: 4px;
        }
        .rate-value {
            font-family: 'Courier New', monospace;
            font-size: 16px;
            color: #27AE60;
            font-weight: 600;
        }
        .timestamp {
            text-align: center;
            font-size: 11px;
            color: #555;
            margin-bottom: 32px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .form-section {
            border-top: 1px solid rgba(255,255,255,.07);
            padding-top: 24px;
        }
        .form-row {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        input, select {
            flex: 1;
            background: rgba(255,255,255,.05);
            border: 1px solid rgba(255,255,255,.1);
            border-radius: 8px;
            padding: 12px;
            color: #fff;
            font-size: 14px;
            font-family: inherit;
        }
        input::placeholder {
            color: #666;
        }
        button {
            width: 100%;
            background: #27AE60;
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 14px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover {
            background: #229954;
        }
        .try-currencies {
            text-align: center;
            font-size: 12px;
            color: #666;
            margin-top: 12px;
        }
        .try-currencies span {
            color: #27AE60;
            cursor: pointer;
            margin: 0 4px;
        }
        .try-currencies span:hover {
            text-decoration: underline;
        }
        .error {
            background: rgba(231,76,60,.1);
            border: 1px solid rgba(231,76,60,.3);
            color: #e74c3c;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 13px;
        }
        .result-display {
            background: rgba(39,174,96,.1);
            border: 1px solid rgba(39,174,96,.2);
            color: #27AE60;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 18px;
            text-align: center;
            font-family: 'Courier New', monospace;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <h1>Open Exchange Rates</h1>
                <div class="badge" id="health-badge">\\u2022 checking</div>
            </div>
            <p class="subtitle">Real-time forex conversion, 170+ fiat currencies</p>

            <div id="error-box" class="error" style="display:none;"></div>

            <div class="hero">
                <div class="hero-conversion">100 USD =</div>
                <div>
                    <span class="hero-result" id="hero-result">--</span>
                    <span class="hero-currency">EUR</span>
                </div>
            </div>

            <div class="rates-grid" id="rates-grid">
                <div class="rate-card">
                    <div class="rate-emoji">\\ud83c\\uddea\\ud83c\\uddfa</div>
                    <div class="rate-code">EUR</div>
                    <div class="rate-value">--</div>
                </div>
                <div class="rate-card">
                    <div class="rate-emoji">\\ud83c\\uddec\\ud83c\\udde7</div>
                    <div class="rate-code">GBP</div>
                    <div class="rate-value">--</div>
                </div>
                <div class="rate-card">
                    <div class="rate-emoji">\\ud83c\\uddef\\ud83c\\uddf5</div>
                    <div class="rate-code">JPY</div>
                    <div class="rate-value">--</div>
                </div>
                <div class="rate-card">
                    <div class="rate-emoji">\\ud83c\\udde8\\ud83c\\udded</div>
                    <div class="rate-code">CHF</div>
                    <div class="rate-value">--</div>
                </div>
                <div class="rate-card">
                    <div class="rate-emoji">\\ud83c\\udde8\\ud83c\\udde6</div>
                    <div class="rate-code">CAD</div>
                    <div class="rate-value">--</div>
                </div>
                <div class="rate-card">
                    <div class="rate-emoji">\\ud83c\\udde6\\ud83c\\uddfa</div>
                    <div class="rate-code">AUD</div>
                    <div class="rate-value">--</div>
                </div>
            </div>

            <div class="timestamp" id="timestamp">LAST UPDATED: --</div>

            <div class="form-section">
                <div id="result-display" class="result-display"></div>
                <form id="convert-form">
                    <div class="form-row">
                        <input type="number" id="amount" value="100" step="0.01" min="0" placeholder="Amount">
                        <input type="text" id="from" value="USD" placeholder="From" maxlength="3" style="text-transform:uppercase;">
                        <input type="text" id="to" value="EUR" placeholder="To" maxlength="3" style="text-transform:uppercase;">
                    </div>
                    <button type="submit">\\u2192 convert</button>
                </form>
                <div class="try-currencies">
                    Try: <span data-pair="GBP">GBP</span> \\u00b7
                    <span data-pair="JPY">JPY</span> \\u00b7
                    <span data-pair="CHF">CHF</span> \\u00b7
                    <span data-pair="CAD">CAD</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const majorCurrencies = ['EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD'];
        let currentRates = {};

        function showError(msg) {
            const box = document.getElementById('error-box');
            box.textContent = msg;
            box.style.display = 'block';
            setTimeout(() => box.style.display = 'none', 5000);
        }

        async function fetchHealth() {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                document.getElementById('health-badge').textContent = '\\u2022 ' + data.status;
            } catch (e) {
                document.getElementById('health-badge').textContent = '\\u2022 error';
            }
        }

        async function fetchHeroConversion() {
            try {
                const res = await fetch('/convert?from=USD&to=EUR&amount=100');
                const data = await res.json();
                document.getElementById('hero-result').textContent = data.result.toFixed(2);
            } catch (e) {
                showError('Failed to load hero conversion');
            }
        }

        async function fetchLatestRates() {
            try {
                const res = await fetch('/latest');
                const data = await res.json();
                currentRates = data.rates;

                majorCurrencies.forEach((cur, idx) => {
                    const rate = currentRates[cur];
                    if (rate) {
                        const cards = document.querySelectorAll('.rate-card');
                        const valueEl = cards[idx].querySelector('.rate-value');
                        valueEl.textContent = rate.toFixed(4);
                    }
                });

                if (data.last_updated) {
                    const date = new Date(data.last_updated);
                    const formatted = date.toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        timeZoneName: 'short'
                    });
                    document.getElementById('timestamp').textContent = 'LAST UPDATED: ' + formatted;
                }
            } catch (e) {
                showError('Failed to load exchange rates');
            }
        }

        async function convertCurrency(from, to, amount) {
            try {
                const res = await fetch(`/convert?from=${from}&to=${to}&amount=${amount}`);
                const data = await res.json();
                const resultBox = document.getElementById('result-display');
                resultBox.textContent = `${amount} ${from} = ${data.result.toFixed(4)} ${to}`;
                resultBox.style.display = 'block';
            } catch (e) {
                showError('Conversion failed. Check currency codes.');
            }
        }

        document.getElementById('convert-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const amount = parseFloat(document.getElementById('amount').value) || 1;
            const from = document.getElementById('from').value.toUpperCase() || 'USD';
            const to = document.getElementById('to').value.toUpperCase() || 'EUR';
            convertCurrency(from, to, amount);
        });

        document.querySelectorAll('.try-currencies span').forEach(span => {
            span.addEventListener('click', () => {
                const cur = span.getAttribute('data-pair');
                document.getElementById('to').value = cur;
                const amount = parseFloat(document.getElementById('amount').value) || 1;
                const from = document.getElementById('from').value.toUpperCase() || 'USD';
                convertCurrency(from, cur, amount);
            });
        });

        Promise.all([
            fetchHealth(),
            fetchHeroConversion(),
            fetchLatestRates()
        ]);
    </script>
</body>
</html>
"""


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
    return HTMLResponse(content=HOME_HTML)


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
