from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

PAIR_MAP = {
    "XAUUSD": "PAXGUSDT",
    "BTCUSD": "BTCUSDT"
}

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_bollinger(prices, period=20, std_mult=2):
    if len(prices) < period:
        return prices[-1], prices[-1]
    recent = prices[-period:]
    sma = sum(recent) / period
    variance = sum((x - sma) ** 2 for x in recent) / period
    std_dev = variance ** 0.5
    return sma + (std_dev * std_mult), sma - (std_dev * std_mult)

@app.get("/api/signals")
def get_signals(pair: str = "BTCUSD"):
    symbol = PAIR_MAP.get(pair.upper(), "BTCUSDT")
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=100"
    
    try:
        res = requests.get(url, timeout=5).json()
        raw_candles = []
        close_prices = []

        for item in res:
            close_p = float(item[4])
            close_prices.append(close_p)
            raw_candles.append({
                "time": int(item[0] / 1000),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": close_p,
            })

        current_price = close_prices[-1]
        rsi_val = round(calculate_rsi(close_prices), 2)
        bb_upper, bb_lower = calculate_bollinger(close_prices)

        signal = "NEUTRAL"
        reason = "Pasar berada di area konsolidasi / normal."

        if current_price <= bb_lower and rsi_val < 40:
            signal = "BUY / CALL 🟢"
            reason = "Harga tembus Lower BB + RSI Oversold."
        elif current_price >= bb_upper and rsi_val > 60:
            signal = "SELL / PUT 🔴"
            reason = "Harga tembus Upper BB + RSI Overbought."

        return {
            "pair": pair.upper(),
            "candles": raw_candles,
            "signal": signal,
            "reason": reason,
            "price": current_price,
            "rsi": rsi_val
        }
    except Exception as e:
        return {"error": str(e), "signal": "ERROR", "reason": "Gagal mengambil data dari Binance", "price": 0, "rsi": 0, "candles": []}

@app.get("/", response_class=HTMLResponse)
def index():
    try:
        with open("index.html", "r") as f:
            return f.read()
    except Exception:
        return "<h1>Index file not found</h1>"

