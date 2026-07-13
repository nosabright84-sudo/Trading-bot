import yfinance as yf
import pandas as pd
import asyncio
from telegram import Bot
import os

TOKEN = os.getenv("8881926722:AAGEtbZT0fe24hYZQDc_38mohULIgZiNXec")
CHAT_ID = int(os.getenv("8761906482"))

TICKERS = [
    "MSFT", "AAPL", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    "AVGO", "AMD", "INTC", "QCOM", "TXN", "MU", "AMAT",
    "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP",
    "LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "DHR", "PFE",
    "WMT", "COST", "HD", "PG", "KO", "PEP", "MCD", "NKE", "SBUX",
    "XOM", "CVX", "COP", "CAT", "BA", "GE", "HON", "UPS",
    "SPY", "QQQ", "DIA", "IWM", "BTC-USD", "ETH-USD"
]

async def get_signal(ticker):
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: yf.download(ticker, period="1mo", interval="1d", progress=False))
        if data.empty or len(data) < 15:
            return f"*{ticker}*: No data ❌"
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        price = float(data['Close'].iloc[-1])
        delta = data['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_now = float(rsi.iloc[-1])
        signal = "HOLD 🟡"
        if rsi_now < 35: signal = "BUY 🟢"
        elif rsi_now > 65: signal = "SELL 🔴"
        return f"*{ticker}*: ${price:.2f} | RSI: {rsi_now:.1f} | {signal}"
    except Exception:
        return f"*{ticker}*: Error"

async def send_long_message(bot, chat_id, text):
    if len(text) <= 4096:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
    else:
        chunks = []
        lines = text.split('\n')
        current_chunk = lines[0] + '\n\n'
        for line in lines[2:]:
            if len(current_chunk + line + '\n') > 4000:
                chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        chunks.append(current_chunk)
        for i, chunk in enumerate(chunks):
            if i > 0:
                chunk = f"*📊 Signals Part {i+1}*\n\n" + chunk
            await bot.send_message(chat_id=chat_id, text=chunk, parse_mode='Markdown')
            await asyncio.sleep(1)

async def main():
    print(f"Getting signals for {len(TICKERS)} tickers...")
    bot = Bot(token=TOKEN)
    tasks = [get_signal(ticker) for ticker in TICKERS]
    results = await asyncio.gather(*tasks)
    final_msg = "*📊 Daily Signals*\n\n" + "\n".join(results)
    await send_long_message(bot, CHAT_ID, final_msg)
    print("Sent to Telegram!")

if __name__ == "__main__":
    asyncio.run(main())
