from tvDatafeed import TvDatafeed, Interval
import talib as ta
import datetime
import pandas as pd
pd.set_option('display.max_rows', None, 'display.max_columns', None)
import numpy as np
from config import BYBIT_API_KEY_1, BYBIT_SECRET_KEY_1, tvusername, tvpassword
import ccxt
import time
import talib

exchange = ccxt.bybit({
    'options': {
        'adjustForTimeDifference': False,
    },
    'apiKey': BYBIT_API_KEY_1,
    'secret': BYBIT_SECRET_KEY_1,
})

#Bot parameters
SYMBOL = 'BTC/USDT:USDT'
TIMEFRAME = '15m'
AMOUNT = 1
ORDERTYPE = 'market'
TPSLRatio = 1.5 

username = tvusername
password = tvpassword

tv = TvDatafeed(username, password)

def newbars():
    df = tv.get_hist(symbol='BTCUSDTPERP',exchange='BINANCE',interval=Interval.in_5_minute,n_bars=200)
    return df

df = newbars()
df.reset_index(inplace=True)
df.index = pd.to_datetime(df.datetime)

def heikinashi(df):
    df['Heiken_Close'] = (df.open+df.close+df.high+df.low)/4
    df['Heiken_Open'] = df['open']
    for i in range(1, len(df)):
        df.at[i, 'Heiken_Open'] = (df.Heiken_Open[i-1]+df.Heiken_Close[i-1])/2

    df['Heiken_High'] = df[['high', 'Heiken_Open', 'Heiken_Close']].max(axis=1)
    df['Heiken_Low'] = df[['low', 'Heiken_Open', 'Heiken_Close']].min(axis=1)
    df.dropna(inplace=True)
    return df

df = heikinashi(df)

def indicators(df):
    df['RSI'] = ta.RSI(df['Heiken_Close'], timeperiod=14)
    df['EMA20'] = ta.EMA(df['Heiken_Close'], timeperiod=9)
    df['EMA50'] = ta.EMA(df['Heiken_Close'], timeperiod=21)
    return df

df = indicators(df)

def generate_order_signal(df):
    ordersignal=[0]*len(df)
    for i in range(0, len(df)):
        if (df.EMA20[i]>df.EMA50[i] and df.Heiken_Open[i]<df.EMA20[i] 
            and df.Heiken_Close[i]>df.EMA20[i]):
            ordersignal[i]=2
        if (df.EMA20[i]<df.EMA50[i] and df.Heiken_Open[i]>df.EMA20[i] 
            and df.Heiken_Close[i]<df.EMA20[i]):
            ordersignal[i]=1
    df['ordersignal']=ordersignal
    return df

df = generate_order_signal(df)

def totalSignal(df):
    ordersignal = [0]*len(df)
    for i in range(0, len(df)):
        if (df.EMA20[i] > df.EMA50[i] and df.Heiken_Open[i] < df.EMA20[i] and df.Heiken_Close[i] > df.EMA20[i]):
            ordersignal[i] = 2
        elif (df.EMA20[i] < df.EMA50[i] and df.Heiken_Open[i] > df.EMA20[i] and df.Heiken_Close[i] < df.EMA20[i]):
            ordersignal[i] = 1
    df['ordersignal'] = ordersignal
    return df

df = totalSignal(df)

def stoploss(df):
    SLSignal = [0] * len(df)
    SLbackcandles = 1
    for row in range(SLbackcandles, len(df)):
        mi=1e10
        ma=-1e10
        if df.ordersignal[row]==1:
            for i in range(row-SLbackcandles, row+1):
                ma = max(ma,df.high[i])
            SLSignal[row]=ma
        if df.ordersignal[row]==2:
            for i in range(row-SLbackcandles, row+1):
                mi = min(mi,df.low[i])
            SLSignal[row]=mi
    df['SLSignal']=SLSignal
    return df

df = stoploss(df)
print(df)
#def apply_trade_logic(df, exchange, SYMBOL):
#    executed_trade = False
#    for i in range(1, len(df)):
#        if executed_trade == False:
#            if (df.ordersignal[-1] == 2 
#                and df.Heiken_Open[i]>=df.Heiken_Open[i-1]):
#                exchange.create_order(SYMBOL, 'market', 'sell', AMOUNT)
#                executed_trade = True
#            elif (df.ordersignal[-1] == 1 
#                  and df.Heiken_Open[i]<=df.Heiken_Open[i-1]):
#                exchange.create_order(SYMBOL, 'market', 'buy', AMOUNT)
#                executed_trade = True
#
#        if df.ordersignal[i]==2 and len(df.ordersignal)==0:   
#            sl1 = df.SLSignal[i]
#            tp1 = df.close[i]+(df.close[i] - sl1)*TPSLRatio
#            order = exchange.create_order(SYMBOL, 'market', 'buy', AMOUNT)
#            exchange.create_oco_order(order['orderId'], stop_loss=sl1, take_profit=tp1)
#            executed_trade = True
#
#        elif df.ordersignal[i]==1 and len(df.ordersignal)==0:       
#            sl1 = df.SLSignal[i]
#            tp1 = df.close[i]-(sl1 - df.close[i])*TPSLRatio
#            order = exchange.create_order(SYMBOL, 'market', 'sell', AMOUNT)
#            exchange.create_oco_order(order['orderId'], stop_loss=sl1, take_profit=tp1)
#
#df = apply_trade_logic(df, exchange, SYMBOL)
#
#while True:
#   df = newbars()
#   df.reset_index(inplace=True)
#   df.index = pd.to_datetime(df.datetime)
#   df = heikinashi(df)
#   df = indicators(df)
#   df = generate_order_signal(df)
#   df = apply_trade_logic(df, exchange, SYMBOL)
#   print(df)
#   time.sleep(30)

# Define the backtest function
def backtest(df):
    # Create new columns to store the strategy's position and returns
    df['position'] = np.nan
    df['returns'] = np.nan

    # Iterate through the DataFrame and apply the strategy
    for index, row in df.iterrows():
        if row['ordersignal'] == 2:
            df.at[index, 'position'] = 1
        elif row['ordersignal'] == 1:
            df.at[index, 'position'] = -1

    # Calculate the strategy's returns
    df['returns'] = df['Heiken_Close'] * df['position'].shift(1)

    # Print the strategy's performance metrics
    print("Total Returns: ", df['returns'].sum())
    print("Annualized Returns: ", (df['returns'].sum() / len(df)) * 252)

# Run the backtest
backtest(df)


