from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import pandas as pd

app = FastAPI()

PAIR_MAP = {
    "XAUUSD": "PAXGUSDT",
    "BTCUSD": "BTCUSDT"
}

def calculate_indicators(df):
    df['EMA_200'] = df['CLOSE'].ewm(span=200, adjust=False).mean()
    delta = df['CLOSE'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    sma = df['CLOSE'].rolling(window=20).mean()
    std = df['CLOSE'].rolling(window=20).std()
    df['BB_UPPER'] = sma + (std * 2)
    df['BB_LOWER'] = sma - (std * 2)
    return df

def get_market_data(symbol="BTCUSDT", interval="5m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    res = requests.get(url, timeout=5).json()
    data = []
    for item in res:
        data.append({
            "time": int(item[0] / 1000),
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
        })
    df = pd.DataFrame(data)
    df.rename(columns={'open':'OPEN', 'high':'HIGH', 'low':'LOW', 'close':'CLOSE'}, inplace=True)
    df = calculate_indicators(df)
    return df, data

@app.get("/api/signals")
def get_signals(pair: str = "BTCUSD"):
    symbol = PAIR_MAP.get(pair.upper(), "BTCUSDT")
    df, raw_candles = get_market_data(symbol=symbol)
    
    curr = df.iloc[-1]
    signal = "NEUTRAL"
    reason = "Menunggu konfirmasi indikator..."

    if curr['CLOSE'] <= curr['BB_LOWER'] and curr['RSI'] < 40:
        signal = "BUY / CALL 🟢"
        reason = "Oversold di Lower BB + RSI Rendah"
    elif curr['CLOSE'] >= curr['BB_UPPER'] and curr['RSI'] > 60:
        signal = "SELL / PUT 🔴"
        reason = "Overbought di Upper BB + RSI Tinggi"

    return {
        "pair": pair.upper(),
        "candles": raw_candles,
        "signal": signal,
        "reason": reason,
        "price": curr['CLOSE'],
        "rsi": round(curr['RSI'], 2)
    }

@app.get("/", response_class=HTMLResponse)
def index():
    with open("index.html", "r") as f:
        return f.read()

