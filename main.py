import requests
import datetime
import numpy as np
import pandas as pd
from binance.client import Client
from binance import helpers as help
from binance.enums import *
import json
import utility
import time
from multiprocessing import Process

def main ():
    currentCoins = []
    class Coin:
        def __init__(self, name, ticker, exchange):
            self.name = name
            self.ticker = ticker
            self.exchange = exchange
    def addCoin(name, ticker, exchange):
        currentCoins.append(Coin(name, ticker, exchange))
    def removeCoin(ticker):
        for i in range(len(currentCoins)):
            if currentCoins[i].ticker == ticker:
                currentCoins.remove(currentCoins[i])
            else:
                pass
    print("Please enter the coins you would like to monitor one by one...")
    while True:
        nameInput = input("Please enter the coin name: ")
        if nameInput.upper() == 'IOTA':
            tickerInput = input("Please enter a ticker: ")
            #If name is IOTA, ticker is IOT to get historical prices
            tickerInput = 'IOT'
            nameInput = tickerInput
        else:
            tickerInput = input("Please enter a ticker: ")
        exchangeInput = "Binance"
        addCoin(str(nameInput), str(tickerInput).upper(), str(exchangeInput).title())
        continueInput = input("Would you like to monitor another coin? (y/n) ")
        if str(continueInput).lower() == 'y':
            continue
        else: 
            break
    toBuy = input("How much USDT will you allocate to each coin? ")
    checkIncrease = input("What percentage increase would you like to see before starting the bot for each coin? (Example - 0.03)")
    checkTime = input("Over what time interval (in minutes) would you like to check? (Default - 60 mins; Max - 2000 mins) ")
    return(currentCoins, toBuy, checkIncrease, checkTime)
def coinChecker(coinInstance, amountToBuy, initialIncrease, timeInterval, public_key, private_key):
    client = Client(str(public_key), str(private_key))
    purchasePrices = {}
    #Infinite loop to check for historical prices in every 30 seconds.
    while True:
        coinData = (utility.historicalPrice(coinInstance, "ETH", timeInterval, exchange='Binance'))
        # Bot checks if any coin in the coin class has increased more than set percentage in the last 60 minutes 
        startPrice = min(coinData.close)
        #To get last price for the special case of IOTA
        if coinInstance == 'IOT':
            closePrice = float(client.get_ticker(symbol=str('IOTAETH')).get('lastPrice'))
        else:
            closePrice = float(client.get_ticker(symbol=str(coinInstance+'ETH')).get('lastPrice'))
        priceChange = closePrice/startPrice-1
        # If any coin increases by the set percentage in the time specified, buy the amount specified
        if priceChange >= initialIncrease:
            #If coinInstance is IOTA
            if coinInstance == 'IOT':
                coinInstance = 'IOTA'
            ETHprice = float(client.get_ticker(symbol='ETHUSDT').get('lastPrice'))
            order = client.order_market_buy(symbol=str('ETHUSDT'),
                                            quantity=round(amountToBuy/ETHprice, 5))
            orders = client.get_open_orders(symbol="ETHUSDT")
            while len(orders) > 0:
                time.sleep(2)
                if len(orders) > 0:
                    continue
                else:
                    break
            ETHBalance = float(client.get_asset_balance(asset='ETH').get('free'))
            buyPrice = float(client.get_ticker(symbol=str(coinInstance+'ETH')).get('lastPrice'))
            buyPriceCIUSD = float(client.get_ticker(symbol=str(coinInstance+'ETH')).get('lastPrice')) * float(client.get_ticker(symbol='ETHUSDT').get('lastPrice'))
            order = client.order_market_buy(symbol=str(coinInstance+'ETH'),
                                            quantity=int(ETHBalance/buyPrice))
            purchasePrices.update({str(coinInstance): buyPrice})
            coinBalance = float(client.get_asset_balance(asset=coinInstance).get('free'))
            # Initial stop-loss is at 3% below purchase price
            stopLoss = 1-initialIncrease
            stopLoss = buyPrice*stopLoss
            priceSize = float(client.get_symbol_info(symbol=str(coinInstance+'ETH')).get('filters')[0].get('minPrice'))
            stopLoss = int(stopLoss/priceSize)
            stopLoss = stopLoss*priceSize
            order = client.create_order(symbol=str(coinInstance+'ETH'),
                                            side=SIDE_SELL,
                                            type=ORDER_TYPE_STOP_LOSS_LIMIT,
                                            timeInForce=TIME_IN_FORCE_GTC, 
                                            quantity=int(coinBalance),
                                            stopPrice=stopLoss,
                                            price=stopLoss)
            print("The bot will proceed with ", coinInstance)
            break
            
        # Else the bot will check again for the price after 30 seconds                        
        else:
            print(coinInstance, "has not increased over the last 60 mins.")
            time.sleep(30)
            continue

    while True:
        currentPrice = float(client.get_ticker(symbol=str(coinInstance+'ETH')).get('lastPrice'))
        buyPrice = purchasePrices.get(coinInstance)
        # If price is more than 2% above purchase price, then change stop-loss to 1% above purchase price
        if currentPrice >= buyPrice*1.02:
            orders = client.get_open_orders(symbol=str(coinInstance+'ETH'))[0].get('orderId')
            result = client.cancel_order(symbol=str(coinInstance+'ETH'), orderId=orders)
            coinBalance = float(client.get_asset_balance(asset=coinInstance).get('free'))
            stopLoss = buyPrice*1.01
            priceSize = float(client.get_symbol_info(symbol=str(coinInstance+'ETH')).get('filters')[0].get('minPrice'))
            stopLoss = int(stopLoss/priceSize)
            stopLoss = stopLoss*priceSize
            order = client.create_order(symbol=str(coinInstance+'ETH'),
                                        side=SIDE_SELL,
                                        type=ORDER_TYPE_STOP_LOSS_LIMIT,
                                        timeInForce=TIME_IN_FORCE_GTC, 
                                        quantity=int(coinBalance),
                                        stopPrice=stopLoss,
                                        price=stopLoss)
        else:
            pass
        break
    while True:
        orders = client.get_open_orders(symbol=str(coinInstance+'ETH'))
        if len(orders) == 0:
            break
        else:
            pass
        # If price is more than 10% above purchase price, Trailing stop
        # loss is triggered; change stop-loss to 7% above purchase price
        currentPrice = float(client.get_ticker(symbol=str(coinInstance+'ETH')).get('lastPrice'))
        buyPrice = purchasePrices.get(coinInstance)
        if currentPrice >= buyPrice*1.10:
            orders = client.get_open_orders(symbol=str(coinInstance+'ETH'))[0].get('orderId')
            result = client.cancel_order(symbol=str(coinInstance+'ETH'), orderId=orders)
            coinBalance = float(client.get_asset_balance(asset=coinInstance).get('free'))
            stopLoss = buyPrice*1.07
            priceSize = float(client.get_symbol_info(symbol=str(coinInstance+'ETH')).get('filters')[0].get('minPrice'))
            stopLoss = int(stopLoss/priceSize)
            stopLoss = stopLoss*priceSize
            order = client.create_order(symbol=str(coinInstance+'ETH'),
                                        side=SIDE_SELL,
                                        type=ORDER_TYPE_STOP_LOSS_LIMIT,
                                        timeInForce=TIME_IN_FORCE_GTC, 
                                        quantity=int(coinBalance),
                                        stopPrice=stopLoss,
                                        price=stopLoss)
        # If price is more than 20% above purchase price, then change
        # stop-loss to 14% above purchase price
        elif currentPrice >= buyPrice*1.20:
            orders = client.get_open_orders(symbol=str(coinInstance+'ETH'))[0].get('orderId')
            result = client.cancel_order(symbol=str(coinInstance+'ETH'), orderId=orders)
            coinBalance = float(client.get_asset_balance(asset=coinInstance).get('free'))
            stopLoss = buyPrice*1.14
            priceSize = float(client.get_symbol_info(symbol=str(coinInstance+'ETH')).get('filters')[0].get('minPrice'))
            stopLoss = int(stopLoss/priceSize)
            stopLoss = stopLoss*priceSize
            order = client.create_order(symbol=str(coinInstance+'ETH'),
                                        side=SIDE_SELL,
                                        type=ORDER_TYPE_STOP_LOSS_LIMIT,
                                        timeInForce=TIME_IN_FORCE_GTC, 
                                        quantity=int(coinBalance),
                                        stopPrice=stopLoss,
                                        price=stopLoss)
        # If price is more than 30% above purchase price, then change
        # stop-loss to 21% above purchase price
        elif currentPrice >= buyPrice*1.30:
            orders = client.get_open_orders(symbol=str(coinInstance+'ETH'))[0].get('orderId')
            result = client.cancel_order(symbol=str(coinInstance+'ETH'), orderId=orders)
            coinBalance = float(client.get_asset_balance(asset=coinInstance).get('free'))
            stopLoss = buyPrice*1.21
            priceSize = float(client.get_symbol_info(symbol=str(coinInstance+'ETH')).get('filters')[0].get('minPrice'))
            stopLoss = int(stopLoss/priceSize)
            stopLoss = stopLoss*priceSize
            order = client.create_order(symbol=str(coinInstance+'ETH'),
                                        side=SIDE_SELL,
                                        type=ORDER_TYPE_STOP_LOSS_LIMIT,
                                        timeInForce=TIME_IN_FORCE_GTC, 
                                        quantity=int(coinBalance),
                                        stopPrice=stopLoss,
                                        price=stopLoss)
        else:
            pass
        # Follow the pattern until SL is not triggered
        continue
    while len(orders) > 0:
            time.sleep(2)
            if len(orders) > 0:
                continue
            else:
                break
    #check balance and sell the amount into tether to finish the bot
    finalBalance = float(client.get_asset_balance(asset="ETH").get('free'))
    lotSize = float(client.get_symbol_info(symbol="ETHUSDT").get('filters')[1].get('minQty'))
    finalBalance = int(finalBalance/lotSize)
    finalBalance = finalBalance*lotSize
    order = client.order_market_sell(symbol=str('ETHUSDT'),
                                     quantity=finalBalance)
    print("Bot is finished for", coinInstance)
    return

if __name__ == '__main__':
    # Initializing variable with public and private api keys.
    public_key = "YqODE1Mv4RkqMEkq3FtUEsE2v3XEX4q9VNhl59YoIDcxU9Jiu8DyGizX0beLBvUr"
    private_key = "qRFbmnpBFqsDL3iWgRkHQTnCeQlMYfmLxzaBoyWwZvXOyiePkAaYMNKFBBVtZ8Wm"
    args = main()
    coins = args[0]
    dollarAmount = int(args[1])
    percentage = float(args[2])
    timeInt = int(args[3])
    processes = []

    for coin in coins:
        p = Process(target=coinChecker, args=(coin.ticker, dollarAmount, percentage, timeInt, public_key, private_key))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()


