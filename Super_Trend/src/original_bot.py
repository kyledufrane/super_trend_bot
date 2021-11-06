import ccxt
import schedule
import time
import pandas as pd
import numpy as np
import json
from datetime import datetime

pd.set_option('display.max_rows', None)

import warnings
warnings.filterwarnings('ignore')

# ------------------------------------------------------------------ #

def get_keys(path):    
    with open(path) as f:
        return json.load(f)

# ------------------------------------------------------------------ #

CB_API_KEY = get_keys('/Users/kyledufrane/.secret/cbpro_key.json')
CB_API_SECRET = get_keys('/Users/kyledufrane/.secret/cbpro_secret.json')
CB_API_PASSPHRASE = get_keys('/Users/kyledufrane/.secret/cbpro_passphrase.json')

exchange = ccxt.coinbasepro({'apiKey': CB_API_KEY['key'],
                             'secret': CB_API_SECRET['secret'],
                             'password': CB_API_PASSPHRASE['passphrase']})

bars = exchange.fetch_ohlcv('ETH/USDT', timeframe='1m', limit=100)

df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')


def true_range(dataframe):
    df['previous_close'] = df['close'].shift(1)
    df['high-low'] = df['high'] - df['low']
    df['high-previous_close'] = abs(df['high'] - df['previous_close'])
    df['low-previous_close'] = abs(df['low'] - df['previous_close'])
    true_range = df[['high-low', 'high-previous_close', 'low-previous_close']].max(axis=1)  
    return true_range

# ------------------------------------------------------------------ #


def atr(dataframe, period=5):   
    dataframe['true_range'] = true_range(dataframe)   
    print("calculate average true range")   
    the_atr = dataframe['true_range'].rolling(period).mean()   
    return the_atr

# ------------------------------------------------------------------ #


def super_trend(dataframe, period=5, multiplier=3):
    hl2 = (dataframe['high'] + dataframe['low']) / 2
    dataframe['atr'] = atr(dataframe, period=period)
    dataframe['upperband'] = hl2 + (multiplier * dataframe['atr'])
    dataframe['lowerband'] = hl2 - (multiplier * dataframe['atr'])
    dataframe['in_uptrend'] = True
    
    for current in range(1, len(dataframe.index)):
        previous = current - 1
        
        if dataframe['close'][current] > dataframe['upperband'][previous]:
            dataframe['in_uptrend'][current]= True
        elif dataframe['close'][current] < dataframe['lowerband'][previous]:
            dataframe['in_uptrend'][current] = False
        else:
            dataframe['in_uptrend'][current] = dataframe['in_uptrend'][previous]
            if dataframe['in_uptrend'][current] and dataframe['lowerband'][current] < dataframe['lowerband'][previous]:
                dataframe['lowerband'][current] = dataframe['lowerband'][previous]
            if not dataframe['in_uptrend'][current] and dataframe['upperband'][current] > dataframe['upperband'][previous]:
                dataframe['upperband'][current] = dataframe['upperband'][previous]
    return dataframe

# ------------------------------------------------------------------ #


in_position = False

# ------------------------------------------------------------------ #

def check_buy_sell_signal(dataframe):
    global in_position
    print("Checking for buy or sell")
    last_row = len(dataframe.index) - 1
    previous_row = last_row - 1
    
    if not dataframe['in_uptrend'][previous_row] and dataframe['in_uptrend'][last_row]:
        print('Change to uptrend, buy')
        if not in_position:
            order = exchange.create_market_buy_order('ETH/USDT', 0.05)
            print(order)
            in_position=True
        else: 
            print("Already in position, nothing to do")
    if dataframe['in_uptrend'][previous_row] and not dataframe['in_uptrend'][last_row]:
        print('Change to uptrend, sell')
        if in_position:
            order = exchange.create_limit_sell_order('ETH/USDT', 0.05)
            print(order)
            in_position=False
        else:
            print("You aren't in position, nothing to sell")


# ------------------------------------------------------------------ #            
            
def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}....")
    bars = exchange.fetch_ohlcv('ETH/USDT', timeframe='1m', limit=100)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    supertrend_data = super_trend(df)
    check_buy_sell_signal(supertrend_data)   