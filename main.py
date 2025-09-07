# ===================================================================
# Crypto Scanner V32 - Confirmed Break Edition (Render Ready)
# ===================================================================
import os
import ccxt.async_support as ccxt
import requests
import pytz
import pandas as pd
import pandas_ta as ta
import asyncio
import signal
import sys
import numpy
import scipy.signal

# ===================================================================
# CONFIGURATION
# ===================================================================
class Config:
    # --- Secrets (taken from Render environment variables) ---
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID_15MIN = os.getenv("TELEGRAM_CHAT_ID")

    # --- Manual Price Alerts ---
    MANUAL_PRICE_ALERTS = {
        "BTC/USDT": {"above": 72000, "below": 68500},
        "ETH/USDT": {"above": 3800},
        "SOL/USDT": {"below": 150},
    }

    # --- Scanner Settings ---
    TIMEZONE = "Asia/Kolkata"
    SCAN_INTERVAL = 300  # 5 min
    LTF_TIMEFRAME = '15m'
    HTF_TIMEFRAME = '1d'
    PULLBACK_TIMEFRAME = '1m'
    DUPLICATE_TIMEOUT = 900
    WATCHLIST_TIMEOUT_HOURS = 4
    SNIPER_COOLDOWN_SECONDS = 120

    # --- Indicators ---
    BB_LENGTH = 20
    BB_STDDEV = 2.0
    REGRESSION_LENGTH = 50
    ADX_LENGTH = 14
    EMA_FAST = 20
    EMA_SLOW = 50
    RSI_PERIOD = 14

    # --- Thresholds ---
    MIN_ADX_LEVEL = 25
    BBW_SQUEEZE_THRESHOLD = 0.02
    TRENDLINE_TOLERANCE_PCT = 0.002

    # --- Range Breakout ---
    RANGE_ADX_MAX = 23
    RANGE_BBW_MAX = 0.03
    RANGE_LOOKBACK = 50
    RANGE_VOLUME_MULTIPLIER = 3.0

    # --- Trend Hunter ---
    REVERSAL_LOOKBACK = 20
    LOOKBACK_PERIOD_BREAKOUT = 32
    STRUCTURE_BREAK_LOOKBACK = 96
    BREAKOUT_VOLUME_MULTIPLIER = 2.0
    MASSIVE_VOLUME_MULTIPLIER = 4.0  
    ZERO_LAG_VOLUME_MULTIPLIER = 4
    ZERO_LAG_BODY_PERCENTAGE = 0.60
    ZERO_LAG_LOOKBACK = 10
    ZERO_LAG_WICK_PERCENTAGE = 0.35
    SWING_LOOKBACK = 192
    SWING_PROMINENCE_PCT = 0.015
    SR_TOLERANCE_PCT = 0.002


# ===================================================================
# CRYPTO SCANNER CLASS
# ===================================================================
class CryptoScanner:
    def __init__(self, symbols_to_scan):
        self.config = Config()
        self.symbols_to_scan = symbols_to_scan
        self.exchange = ccxt.binance({'timeout': 30000})

    # -------------------- TELEGRAM ALERT --------------------
    def _send_telegram_alert(self, message):
        url = f"https://api.telegram.org/bot{self.config.TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": self.config.TELEGRAM_CHAT_ID_15MIN,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            requests.post(url, json=payload, timeout=10).raise_for_status()
        except Exception as e:
            print(f"Telegram error: {e}")

    # -------------------- SCANNER LOOP --------------------
    async def run(self):
        while True:
            try:
                for symbol in self.symbols_to_scan:
                    ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe=self.config.LTF_TIMEFRAME, limit=200)
                    if not ohlcv:
                        continue

                    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
                    df.ta.ema(length=self.config.EMA_FAST, append=True)
                    df.ta.ema(length=self.config.EMA_SLOW, append=True)

                    last_close = df.iloc[-1]['close']
                    ema_fast = df.iloc[-1][f'EMA_{self.config.EMA_FAST}']
                    ema_slow = df.iloc[-1][f'EMA_{self.config.EMA_SLOW}']

                    if last_close > ema_fast and ema_fast > ema_slow:
                        self._send_telegram_alert(f"🚀 {symbol} bullish trend confirmed: {last_close}")
                    elif last_close < ema_fast and ema_fast < ema_slow:
                        self._send_telegram_alert(f"⚠️ {symbol} bearish trend confirmed: {last_close}")
                    else:
                        print(f"{symbol} neutral at {last_close}")

                await asyncio.sleep(self.config.SCAN_INTERVAL)

            except Exception as e:
                print(f"Scanner error: {e}")
                await asyncio.sleep(10)


# ===================================================================
# MAIN ENTRY (Render Ready)
# ===================================================================
scanner = CryptoScanner(["BTC/USDT", "ETH/USDT", "SOL/USDT"])  # add more coins if needed

def shutdown():
    print("Shutting down gracefully...")
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(scanner.exchange.close())
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, lambda s, f: shutdown())
signal.signal(signal.SIGINT, lambda s, f: shutdown())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(scanner.run())
