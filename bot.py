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

def get_price(ticker):
    try:
        # Stooq - free and never blocks
        url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
        df = pd.read_csv(url)
        if len(df) < 20:
            return None, None
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df = df.dropna(subset=['Close'])
        price = float(df['Close'].iloc[-1])
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss.replace(0, 0.0001)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])
        if math.isnan(rsi_val): rsi_val = 50
        
        sig = "HOLD"
        if rsi_val < 35: sig = "BUY"
        elif rsi_val > 70: sig = "SELL"
        return price, rsi_val, sig
    except Exception as e:
        print(f"{ticker} error: {e}")
        return None, None, "ERROR"

def get_crypto(ticker):
    try:
        coin = "bitcoin" if "BTC" in ticker else "ethereum"
        r = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=30", timeout=15)
        prices = r.json()['prices']
        closes = [p[1] for p in prices]
        df = pd.DataFrame({'Close': closes})
        price = closes[-1]
        
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss.replace(0, 0.0001)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])
        
        sig = "HOLD"
        if rsi_val < 35: sig = "BUY"
        elif rsi_val > 70: sig = "SELL"
        return price, rsi_val, sig
    except Exception as e:
        print(f"{ticker} crypto error: {e}")
        return None, None, "ERROR"

async def main():
    bot = Bot(token=TOKEN)
    results = []
    
    loop = asyncio.get_event_loop()
    
    # Stocks
    for t in STOCKS:
        price, rsi, sig = await loop.run_in_executor(None, lambda t=t: get_price(t))
        if price: results.append((t, price, rsi, sig))
    
    # Crypto
    for t in ["BTC-USD", "ETH-USD"]:
        price, rsi, sig = await loop.run_in_executor(None, lambda t=t: get_crypto(t))
        if price: results.append((t, price, rsi, sig))
    
    # Build message
    lines = [f"*📊 LIVE REPORT (Stooq + CoinGecko)*\n_{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n"]
    for ticker, price, rsi, signal in results:
        emoji = "🟢" if signal=="BUY" else "🔴" if signal=="SELL" else "🟡"
        lines.append(f"*{ticker}* {emoji} {signal}\nPrice: ${price:.2f} | RSI: {rsi:.1f}\n")
    
    msg = "\n".join(lines)
    if len(msg) > 4000:
        mid = len(lines)//2
        await bot.send_message(chat_id=CHAT_ID, text="\n".join(lines[:mid]), parse_mode='Markdown')
        await bot.send_message(chat_id=CHAT_ID, text="\n".join(lines[mid:]), parse_mode='Markdown')
    else:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

    print(f"Sent {len(results)}")

if __name__ == "__main__":
    asyncio.run(main())
