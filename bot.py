import yfinance as yf
import pandas as pd
import asyncio
from telegram import Bot
import os
import json

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
SEND_FULL = os.getenv("SEND_FULL_REPORT", "false").lower() == "true"

TICKERS = [
    "MSFT", "AAPL", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    "AVGO", "AMD", "INTC", "QCOM", "TXN", "MU", "AMAT",
    "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP",
    "LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "DHR", "PFE",
    "WMT", "COST", "HD", "PG", "KO", "PEP", "MCD", "NKE", "SBUX",
    "XOM", "CVX", "COP", "CAT", "BA", "GE", "HON", "UPS",
    "SPY", "QQQ", "DIA", "IWM", "BTC-USD", "ETH-USD"
]

STATE_FILE = "last_signals.json"

def load_last_signals():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_signals(signals):
    with open(STATE_FILE, 'w') as f:
        json.dump(signals, f)

async def get_signal(ticker):
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: yf.download(ticker, period="2d", interval="5m", progress=False))
        if data.empty or len(data) < 15:
            return ticker, None, None, "ERROR"
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        price = float(data['Close'].iloc[-1])
        delta = data['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_now = float(rsi.iloc[-1])

        signal = "HOLD"
        if rsi_now < 35: signal = "BUY"
        elif rsi_now > 65: signal = "SELL"

        return ticker, price, rsi_now, signal
    except Exception:
        return ticker, None, None, "ERROR"

async def main():
    bot = Bot(token=TOKEN)
    last_signals = load_last_signals()
    new_signals = {}

    tasks = [get_signal(ticker) for ticker in TICKERS]
    results = await asyncio.gather(*tasks)

    if SEND_FULL:
        # Send full report of all 50 stocks
        lines = ["*📊 FULL STATUS REPORT 📊*\n"]
        for ticker, price, rsi, signal in results:
            if signal != "ERROR":
                emoji = "🟢" if signal=="BUY" else "🔴" if signal=="SELL" else "🟡"
                lines.append(f"*{ticker}*: ${price:.2f} | RSI: {rsi:.1f} | {signal} {emoji}")
        
        # Split into 2 messages if too long for Telegram
        msg = "\n".join(lines)
        if len(msg) > 4000:
            mid = len(lines) // 2
            await bot.send_message(chat_id=CHAT_ID, text="\n".join(lines[:mid]), parse_mode='Markdown')
            await bot.send_message(chat_id=CHAT_ID, text="\n".join(lines[mid:]), parse_mode='Markdown')
        else:
            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
        print("Sent full report")
    else:
        # Send only alerts
        alerts = []
        for ticker, price, rsi, signal in results:
            if signal == "ERROR" or price is None:
                continue
            new_signals[ticker] = signal
            old_signal = last_signals.get(ticker, "HOLD")
            if signal!= old_signal and signal in ["BUY", "SELL"]:
                emoji = "🟢" if signal == "BUY" else "🔴"
                alerts.append(f"*{ticker}* {emoji} *{signal}*\nPrice: ${price:.2f} | RSI: {rsi:.1f}")

        if alerts:
            msg = "*🚨 REAL-TIME ALERT 🚨*\n\n" + "\n\n".join(alerts)
            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
            print(f"Sent {len(alerts)} alerts")
        else:
            print("No new signals")
        save_signals(new_signals)

if __name__ == "__main__":
    asyncio.run(main())
