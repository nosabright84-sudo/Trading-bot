import pandas as pd
import asyncio
from telegram import Bot
import os
import json
import math
from datetime import datetime
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

STOCKS = [
    "MSFT", "AAPL", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    "AVGO", "AMD", "INTC", "QCOM", "TXN", "MU", "AMAT",
    "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP",
    "LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "DHR", "PFE",
    "WMT", "COST", "HD", "PG", "KO", "PEP", "MCD", "NKE", "SBUX",
    "XOM", "CVX", "COP", "CAT", "BA", "GE", "HON", "UPS",
    "SPY", "QQQ", "DIA", "IWM"
]

def get_yahoo_data(ticker):
    try:
        # Direct Yahoo API - bypasses yfinance completely
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=3mo&interval=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        result = data['chart']['result'][0]
        closes = result['indicators']['quote'][0]['close']
        closes = [c for c in closes if c is not None]
        if len(closes) < 15:
            return None, None, "ERROR"
        
        df = pd.DataFrame({'Close': closes})
        price = closes[-1]
        
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss.replace(0, 0.0001)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])
        if math.isnan(rsi_val): rsi_val = 50.0
        
        sig = "HOLD"
        if rsi_val < 35: sig = "BUY"
        elif rsi_val > 70: sig = "SELL"
        return float(price), rsi_val, sig
    except Exception as e:
        print(f"{ticker} yahoo error: {e}")
        return None, None, "ERROR"

def get_crypto_live():
    try:
        # Simple price - always live
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd", timeout=10)
        data = r.json()
        btc_price = data['bitcoin']['usd']
        eth_price = data['ethereum']['usd']
        
        # For RSI, get chart
        btc_chart = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=30", timeout=10).json()
        eth_chart = requests.get("https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=30", timeout=10).json()
        
        def calc_rsi(prices):
            df = pd.DataFrame({'Close': prices})
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss.replace(0, 0.0001)
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        
        btc_rsi = calc_rsi([p[1] for p in btc_chart['prices']])
        eth_rsi = calc_rsi([p[1] for p in eth_chart['prices']])
        
        return [("BTC-USD", btc_price, btc_rsi), ("ETH-USD", eth_price, eth_rsi)]
    except Exception as e:
        print(f"Crypto error: {e}")
        return []

async def main():
    bot = Bot(token=TOKEN)
    loop = asyncio.get_event_loop()
    results = []

    for t in STOCKS:
        price, rsi, sig = await loop.run_in_executor(None, lambda t=t: get_yahoo_data(t))
        if price:
            results.append((t, price, rsi, sig))
        await asyncio.sleep(0.3) # avoid Yahoo rate limit

    crypto = await loop.run_in_executor(None, get_crypto_live)
    for ticker, price, rsi in crypto:
        sig = "HOLD"
        if rsi < 35: sig = "BUY"
        elif rsi > 70: sig = "SELL"
        results.append((ticker, price, rsi, sig))

    lines = [f"*📊 LIVE PRICES (Direct Yahoo + CoinGecko)*\n_{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n"]
    for ticker, price, rsi, signal in results:
        emoji = "🟢" if signal=="BUY" else "🔴" if signal=="SELL" else "🟡"
        lines.append(f"*{ticker}* {emoji} {signal}\nPrice: ${price:,.2f} | RSI: {rsi:.1f}\n")

    msg = "\n".join(lines)
    if len(msg) > 4000:
        for i in range(0, len(lines), 25):
            await bot.send_message(chat_id=CHAT_ID, text="\n".join(lines[i:i+25]), parse_mode='Markdown')
    else:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
    
    print(f"Sent {len(results)} tickers")

if __name__ == "__main__":
    asyncio.run(main())
