import requests #sudo apt-get install python3-requests
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("-api", "--apikey", help="Api key. Stored after first use")
args = parser.parse_args()

itemids = [223,419,621]
apikey='myapikey'

if args.apikey:
    apikey = args.apikey

def getitemlisting(itemid):
    # https://api.torn.com/v2/market/175/itemmarket

    apiendpoint = f'https://api.torn.com/v2/market/{itemid}/itemarket'
    headers = {'Authorization':'ApiKey '+ apikey}

    response = requests.get(apiendpoint, headers = headers)
    res = response.json()['itemmarket']
    return res

for item in itemids:
    print(res['item']['name'])
    
