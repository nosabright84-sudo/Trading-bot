import yfinance as yf
import pandas as pd
import asyncio, nest_asyncio
from telegram import Bot
nest_asyncio.apply()

# ===== EDIT THESE =====
TOKEN = "8881926722:AAEm5Zu701dShSIQcRKvbmPULxWWDiYsETk"   # Keep quotes
CHAT_ID =8761906482         # NO quotes, just number
TICKERS = TICKERS = ["TSLA", "AAPL", "NVDA", "BTC-USD", "SPY"]  # Add/remove stocks here
# ======================

async def get_signal(ticker):
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
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

    except Exception as e:
        return f"*{ticker}*: Error - {str(e)[:30]}"

async def main():
    print("Getting signals for:", TICKERS)
    bot = Bot(token=TOKEN)

    # Get signal for each ticker
    results = []
    for ticker in TICKERS:
        signal_text = await get_signal(ticker)
        results.append(signal_text)

    # Combine into 1 message
    final_msg = "*📊 Daily Signals*\n\n" + "\n".join(results)

    await bot.send_message(chat_id=CHAT_ID, text=final_msg, parse_mode='Markdown')
    print("Sent to Telegram!")
import asyncio
asyncio.run(main())
