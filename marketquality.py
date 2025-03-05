# v3
# sort UI by quality
# https://www.torn.com/page.php?sid=ItemMarket#/market/view=search&itemID=790&itemName=Plastic%20Sword&itemType=Melee&sortField=quality&sortOrder=DESC

import requests #sudo apt-get install python3-requests
import argparse
import json
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-api", "--apikey", help="Api key")
parser.add_argument("--itemids", help="Comma delimited list of item IDs")
parser.add_argument("--maxitems", help="Max number of market items to show")
args = parser.parse_args()

itemids = [790,223,419,621]
apikey='myapikey'
maxitems = 4

if args.apikey:
    apikey = args.apikey
if args.itemids:
    itemids = split(args.itemids, ',')
if args.maxitems:
    maxitems = int(args.maxitems)

def getitemlisting(itemid):
    # https://api.torn.com/v2/market/175/itemmarket
    apiendpoint = f'https://api.torn.com/v2/market/{itemid}/itemmarket'
    print(apiendpoint)
    headers = {'Authorization':'ApiKey '+ apikey}
    response = requests.get(apiendpoint, headers = headers)
    res = response.json()['itemmarket']
    return res

for item in itemids:
    res = getitemlisting(str(item))
    print(f"{item} Name: {res['item']['name']}, Type: {res['item']['type']}")
    n = 0
    for listing in res['listings']:
        n += 1
        m1 = f"Price: {listing.get('price','')}, Amount: {listing.get('amount','')}, "
        try:
            m2 = f"Dam: {listing['itemDetails']['stats']['damage']} Acc: {listing['itemDetails']['stats']['accuracy']} \
Arm: {listing['itemDetails']['stats']['armor']} Qual:{listing['itemDetails']['stats']['quality']}"
        except Exception as e:
            m2 = ""
        print(m1 + m2)
        if n > maxitems:
            break
