import talib
import pandas as pd
import matplotlib.pyplot as plt
import time
from pybit import usdt_perpetual
from config import BYBIT_API_KEY, BYBIT_SECRET_KEY

# Create an authenticated session
session = usdt_perpetual.HTTP(
    endpoint="https://api.bybit.com",
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_SECRET_KEY,
)

# Get the most recent 1 minute candles
def get_data():
    kline_response = session.query_kline(symbol='SOLUSDT', interval=5, from_time=1581231260)
    klines = kline_response['result']
    df = pd.DataFrame(klines)
    df.set_index('start_at', inplace=True)
    df.index = pd.to_datetime(df.index, unit='s')

    return df

data = get_data()

# Print the DataFrame
#print(data)

# Calculate RSI using close price and specified length
rsi = talib.RSI(data["close"], timeperiod=14)


# Create figure and plot RSI
fig, ax = plt.subplots()
ax.plot(rsi)

# All inputs
overbuy = 70
oversell = 30
topLimit = 60
botLimit = 40
rsiLen = 14
priceTopBotSource = "close"
maxLoopback = 50
confirmation = 2

# Create a new column in the DataFrame to hold the buy/sell signals
data['signal'] = 0

# Set the signal to 1 for buy and -1 for sell
data.loc[rsi < oversell, 'signal'] = 1
data.loc[rsi > overbuy, 'signal'] = -1

# Plot the buy and sell signals
ax.scatter(data.index, data.signal * 80, marker='^', c='green', s=100)
ax.scatter(data.index, data.signal * -80, marker='v', c='red', s=100)

# Add overbought/oversold lines
ax.axhline(y=overbuy, linestyle="dotted", color="black")
ax.axhline(y=oversell, linestyle="dotted", color="black")


# Detect and plot divergences
if priceTopBotSource == "close":
    price = data["close"]
else:
    price = data[["high", "low"]].max(axis=1)

# Initialize variables for loop
divergences = [] 
loopbackCounter = 0  
maxCounter = maxLoopback 

# Loop through data in reverse order (from the end of the data to the beginning)
for i in range(len(data)-2, 0, -1):
    # Check if divergence is detected
    if (rsi[i] > topLimit and price[i] < price[i+1]) or (rsi[i] < botLimit and price[i] > price[i+1]):
        # If divergence is detected, add index to list and reset loopbackCounter
        divergences.append(i)
        loopbackCounter = 0
    else:
        # If divergence is not detected, increment loopbackCounter
        loopbackCounter += 1
    if loopbackCounter > maxCounter:
        # If loopbackCounter exceeds maxCounter, stop the loop
        break

# Show the plot
plt.show()


def place_order():
        if loopbackCounter==0:
            order_response = session.place_order(
                symbol="SOLUSDT",
                side="Buy",
                order_type="Market",
                qty=1,
                time_in_force="GoodTillCancel",
                reduce_only=False,
                close_on_trigger=False,
            )
            print("long order placed")

        elif loopbackCounter==1:
            order_response = session.place_order(
                symbol="SOLUSDT",
                side="Sell",
                order_type="Market",
                qty=1,
                time_in_force="GoodTillCancel",
                reduce_only=False,
                close_on_trigger=False,
            )
            print("short order placed")

while True:
    data = get_data()
    rsi = talib.RSI(data["close"], timeperiod=14)
    print(rsi[-1])

    # Check for divergences
    if (rsi[-1] > topLimit and data["close"][-1] < data["close"][-2]) or (rsi[-1] < botLimit and data["close"][-1] > data["close"][-2]):
        print("Divergence detected!")
        place_order()
    else:
        print("No divergence detected")
    
    # Sleep for a while before checking again
    time.sleep(60)  # sleep for 60 seconds (1 minute)

