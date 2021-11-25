from pycoingecko import CoinGeckoAPI
from PIL import Image, ImageDraw, ImageFont
from math import log10
import requests
import difflib
import sys
import os
thismodule = sys.modules[__name__]
from json import loads, dumps
config = loads(open('config.json','r').read())

cg = CoinGeckoAPI()

coins_list = cg.get_coins_list()

def HumanFormat(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

from os import listdir
from os.path import isfile, join
coins = {
    f.replace('.png','').lower():
        Image.open(f'./white_icons/{f}').convert('RGBA')
        for f in listdir('./white_icons/') if isfile(join('./white_icons/', f))
}

class Coin:
    currency = '' # Stores currency that the next variable is compared to
    market_cap = 0
    volume_24h = 0
    change_24h = 0 # the value is stored in percentages
    price = 0
    previous_price = 0 # is computed by using price and change_24h
    def __init__(self, *args, **kwargs):
        if len(args) != 0 and isinstance(args[0], dict):
            for key, value in args[0].items():
                setattr(self, key, value)
        for key, value in kwargs.items():
            setattr(self, key, value)

def GetCoin(symbol: str, name: str):
    # list of coins as dicts {'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin'}
    t = [i for i in coins_list if i['symbol'].lower() == symbol.lower()]
    if len(t) > 1:
        # In coins_list, there could be multiple occurences of the coin with the same symbol.
        # UNI, for example, stands for UNICORN token, UNIVERSE token and, of course, Uniswap
        
        # Using the name of the coin we've just grabbed we search for it in the coinlist,
        # for the coin which name has the least difference with variable name
        differences = [len([j for j in difflib.ndiff(i['name'].lower(), name.lower()) if j[0] != ' ']) for i in t]
        t = t[differences.index(min(differences))]
    elif len(t) == 1:
        t = t[0]
    else:
        print(f'Critical error! {symbol} {name} not found in coins_list!')
        raise ValueError
    t = t.copy()
    t['name'] = name
    t['symbol'] = symbol
    return Coin(t)
previous_content = None
try:
    previous_content = open('cached_top.html','r', encoding='utf-8').read()
except:
    pass
def GetTopCoins(n = 10):
    global previous_content
    if n >= 80:
        raise ValueError('Maximum input value to GetTopCoins() function is n = 80')
    response = requests.get('https://www.coingecko.com/en')
    if response.status_code != 200:
        print(f'ERROR: GET request to https://www.coingecko.com/en returned {response.status_code}.\nUsing result of previous request.')
    else:
        previous_content = response.content.decode('utf-8')
        open('cached_top.html', 'w', encoding='utf-8').write(previous_content)
        
    """
    Bitcoin # Ethereum  #
    BTC     # ETH       # and etc.
    """
    html_symbol = '<span class="tw-hidden d-lg-inline font-normal text-3xs ml-2">\n'
    html_name = '<a class="tw-hidden lg:tw-flex font-bold tw-items-center tw-justify-between" style="width: 115px;" href="/en/coins/'
    
    symbol_index = 0 
    name_index = 0
    list = [] # list of parsed currencies w/o stables
    while n > 0:
         # we're searching for the next occurance of name and symbol in html
        symbol_index = previous_content.find(html_symbol, symbol_index) + len(html_symbol)
        name_index = previous_content.find(html_name, name_index) + len(html_name)
        n -= 1
        
        symbol = previous_content[symbol_index:previous_content.find('\n', symbol_index+1)]
        name = previous_content[name_index:previous_content.find('</a>', name_index+1)].split('">')[1].replace('\n','')
        symbol = symbol.replace(' ','').replace('\n', '')
        if symbol.lower() in [i.lower() for i in config['blacklist']] or symbol.lower() not in coins.keys():
            n += 1
            continue
        
        list.append(GetCoin(symbol, name))
    return list

def UpdateCoinPrices(coin_list: list[Coin], vs_currency: str):
    data = cg.get_price(ids=[coin.id for coin in coin_list], 
                        vs_currencies=vs_currency, include_market_cap=True, 
                        include_24hr_vol=True, include_24hr_change=True)
    for id, data_ in data.items():
        coin = [i for i in coin_list if i.id == id][0]
        setattr(coin, 'change_24h', data_[vs_currency + '_24h_change'])
        setattr(coin, 'market_cap', HumanFormat(int(data_[vs_currency + '_market_cap'])))
        setattr(coin, 'volume_24h', HumanFormat(int(data_[vs_currency + '_24h_vol'])))
        setattr(coin, 'price', data_[vs_currency])
        setattr(coin, 'currency', 'usdt')
        setattr(coin, 'previous_price', coin.price / (1 + coin.change_24h / 100))
        t = int(log10(coin.price))
        if t < 0:
            coin.price = ('{0:.' + str(-t+5) + 'f}').format(coin.price)
            coin.previous_price = ('{0:.' + str(-t+5) + 'f}').format(coin.previous_price)
        else:
            coin.price = ('{0:.' + str(0 if t > 3 else 3 - t) + 'f}').format(coin.price)
            coin.previous_price = ('{0:.' + str(0 if t > 3 else 3 - t) + 'f}').format(coin.previous_price)
        coin.price = coin.price[:9]
        setattr(coin, 'rate', (coin.symbol + '/' + coin.currency.upper()) )
    return coin_list

def GetTopCoinPricesPlusDAO(*,n = 9, vs_currency = 'usd'):
    t = [GetCoin('DAOvc', 'DAOvc')] + GetTopCoins(n)
    return UpdateCoinPrices(t, vs_currency)



for key, value in config['sticker_settings'].items():
    if 'font' not in value.keys():
        value['font'] = config['default_font']
    if 'font_size' not in value.keys():
        value['font_size'] = config['default_font_size']
    if 'color' not in value.keys():
        value['color'] = config['default_color']
    if 'enabled' not in value.keys():
        value['enabled'] = False
    if 'centered' not in value.keys():
        value['centered'] = True

arrow_green = Image.open(config['arrow_green']).convert("RGBA")
arrow_red = Image.open(config['arrow_red']).convert("RGBA")
small_arrow_green = Image.open(config['arrow_green']).convert("RGBA").resize(
    (int(arrow_green.size[0]* 1/3),
     int(arrow_green.size[1]* 1/3),
     ))
small_arrow_red = Image.open(config['arrow_red']).convert("RGBA").resize(
    (int(arrow_green.size[0]* 1/3),
     int(arrow_green.size[1]* 1/3),
     ))
template = Image.open(config['sticker_template']).convert("RGBA")




def GenerateSticker(filename, coin):
    im = template.copy()
    draw = ImageDraw.Draw(im)
    for key, values in config['sticker_settings'].items():
        if values['enabled']:
            if key == 'coin_icon':
                x, y = values['coordinates']
                if coin.symbol.lower() not in coins.keys():
                    continue
                t = coins[coin.symbol.lower()]
                im.paste(t, (int(x-t.size[0]/2),int(y-t.size[1]/2)), t)
                continue
            font = ImageFont.truetype(values['font'], values['font_size'])
            width_text, height_text = draw.textsize(getattr(coin, key), font)
            x,y = values['coordinates']
            if values['centered']:
                x,y = x-width_text/2, y-height_text/2
            draw.text((x,y), getattr(coin, key), font=font, fill=tuple(values['color']))
            if key == 'price':
                arrow = arrow_green if coin.previous_price < coin.price else arrow_red
                if coin.previous_price > coin.price:
                    im.paste(arrow, (int(x+width_text + 8),int(y-arrow.height+height_text)), arrow)
                else:
                    im.paste(arrow, (int(x+width_text + 8),int(y+arrow.height)), arrow)
   
            if key == 'previous_price':
                arrow = small_arrow_green if coin.previous_price > coin.price else small_arrow_red
                if coin.previous_price < coin.price:
                    im.paste(arrow, (int(x+width_text + 3),int(y-arrow.height+height_text)), arrow)
                else:
                    im.paste(arrow, (int(x+width_text + 3),int(y+arrow.height)), arrow)
   
    
    im.save(filename + '.png', "PNG")

def GenerateStickers(coins, currency):
    for i, coin in enumerate(coins):
        GenerateSticker(f'stickers/{i}', coin)