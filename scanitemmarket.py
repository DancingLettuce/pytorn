import argparse
import sys
import json
from pathlib import Path
import pathlib
import requests #sudo apt-get install python3-requests
from datetime import datetime
import sqlite3
import os
import re
import time
import csv
from operator import itemgetter
import random
from requests.exceptions import ConnectionError, RequestException

import library

    # SQL Language  https://inloop.github.io/sqlite-viewer/
    # Table https://sqliteviewer.app/#/pytorn.db/table/userlog/

# scans the item market and reports on prices
#python3 scanitemmarket.py --getmarketfile listitems_allitems.txt

parser = argparse.ArgumentParser()
parser.add_argument("--getmarketfile",   help="Get market for all items in INFILE")
parser.add_argument("--limit",   help="only process the first X in the list", type=int)
parser.add_argument("--debugsql", action="store_true",  help="Show SQLite execution")
parser.add_argument("--showsecrets", action="store_true",  help="shows secrets")
parser.add_argument("--debug", action="store_true",  help="Show detailed tracing log")
parser.add_argument("--truncatedata", action="store_true",  help="truncate the market data first")
parser.add_argument("--notruncate", action="store_true",  help="do not truncate bazaar data")
args = parser.parse_args()
library.args = args
library.secrets = {}
dbcon = sqlite3.connect('pytorn.db')
library.dbcon = dbcon
library.apicount = 0
library.timestart = datetime.now()
library.dlog = library.debuglog()
library.loadsecrets()
secrets = library.secrets
if args.debugsql:
    # trace calls
    library.dbcon.set_trace_callback(print)

class marketplace:
    listing = []
    item_id = None
    def __init__(self,**kwargs):
    # call the super by using super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
        if self.item_id:
            self.getitemlisting(self.item_id)
    def getitemlisting(self, itemid):
        # https://api.torn.com/v2/market/175/itemmarket
        res = library.get_api(section='market', slug=str(itemid),urlbreadcrumb='itemmarket' )
        try:
            self.listing = res['itemmarket']['listings']
        except Exception as e:
            print(f"ERROR {e} {res}")
            self.listing = None
        library.dlog.debug(f"Market listing {self.listing}")
    def append_todb(self):
        pass

class stockitem:
    # representation of the item table
    item_id = None
    name = None
    sell_price = 0
    buy_price = None
    market_price = None 
    monitorprice = None
    label = None
    updated_on = None
    last_sellprice = None
    last_buyprice = None
    def __init__(self,**kwargs):
    # call the super by using super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
        if self.item_id:
            self.get_attrib_fromdb()
    def get_sell_price(self):
        if self.sell_price is None:
            return 0
        else:
            return self.sell_price
    def get_attrib_fromdb(self):
        res = library.get_cur("""SELECT updated_on, name, buy_price, sell_price, market_price, 
            monitorprice, label, last_sellprice, last_buyprice FROM item WHERE item_id = ?""", 
            (self.item_id,)).fetchone()
        self.updated_on = res[0]
        self.name = res[1]
        self.buy_price = res[2]
        self.sell_price = res[3]
        self.market_price = res[4]
        self.monitorprice = res[5]
        self.label = res[6]
        self.last_sellprice = res[7]
        self.last_buyprice = res[8]
        return res

def readitemmarketdetails(item_id, message=""):
    timestampnow_iso = datetime.utcnow().isoformat()
    this_si = stockitem(item_id= item_id)
    library.print_flush(f"{message} Reading {this_si.name}")
    mkt = marketplace(item_id = item_id)
    paramlist = []
    first = True 
    if mkt.listing is None:
        print(f"{message} no listing for {item_id}, sleeping x 1")
        time.sleep(30)
        mkt = marketplace(item_id = item_id)
    if mkt.listing is None:
        print(f"{message} no listing for {item_id}, sleeping x 2")
        time.sleep(40)
        mkt = marketplace(item_id = item_id)
    if mkt.listing is None:
        print(f"{message} no listing for {item_id}, exiting x 3")
        return

    for listitem in mkt.listing:
        paramlist.append( (item_id, listitem['price'], listitem['amount']) )
        if this_si.sell_price is not None and ( (this_si.sell_price - (listitem['price'] ) * listitem['amount'] >= 500) ):
            if first:
                print(f"{message} Profit {this_si.name} ({this_si.sell_price}*{listitem['amount']}) > {(this_si.sell_price - listitem['price']) * listitem['amount']}")
                # if want a buylist at the end if doing a small number of items or multithreading
                #buylist.append((f"Buy {this_si.name} {(this_si.sell_price - listitem['price']) * listitem['amount']}",
                #(this_si.sell_price - listitem['price']) * listitem['amount']))
        elif this_si.monitorprice is not None and (listitem['price'] <= this_si.monitorprice):
            if first:
                print(f"{message}----- Below monitor {this_si.name} ({listitem['price']}*{listitem['amount']}) > {(this_si.monitorprice - listitem['price']) * listitem['amount']}")
        elif  listitem['price'] == this_si.sell_price:
            if first:
                print(f"{message} ----- Same price {this_si.name} {listitem['price']}*{listitem['amount']}")
        elif first:
            pass
            #print(f"{n}/{len(itemslist)} Processing {this_si.name} {this_si.sell_price}  {listitem['price']} ")
        else:
            pass
        first = False    
    library.execute_sql(sql="""INSERT INTO market (item_id, price, quantity) 
        VALUES (?,?,?);""", args=paramlist, many=True)
    
def main():
    timestampnow_iso = datetime.utcnow().isoformat()

    

    if args.truncatedata:
        library.execute_sql("DELETE FROM market;")
        library.execute_sql("DELETE FROM bazaar;")
        print("Deleting market, bazaar")

    itemslist = []
    params = []
    finl = []
    with open(args.getmarketfile) as fin:
        print(f"Loading from {args.getmarketfile}")
        finl = fin.read().splitlines()
    for iid in finl:
        iid = iid.replace(",","\t")
        iid = iid.replace('"',"")
        if iid.startswith('#break'):
            break
        if iid.startswith('#'):
            continue
        iid = iid.split('\t')[0].strip()
        if not iid:
            continue
        if iid in itemslist:
            continue
        else:
            itemslist.append(iid)
            params.append( (iid,))   
        print_flush(f"Loaded {len(finl)} rows into {len(itemslist)} unique player_ids")         
        # don't sort
        #itemslist.sort()

    if args.limit:
        itemslist = itemslist[:args.limit]
    
    n = 0
    buylist = []
    
    # iterating through all the items by ID
    if args.getmarketfile:
        library.execute_sql("DELETE FROM market;")
        print(f"Market table truncated")
        print(f"Processing all {len(itemslist)} market items in itemslist")
        len_itemlist = len(itemslist)
        while len(itemslist) >=20:
            n+=1
            rnd_item_id = random.choice(itemslist)
            itemslist.remove(rnd_item_id)
            message = f"{datetime.now().strftime('%H:%M')} {n}/{len_itemlist}"
            library.print_flush(f"{message} getting itemmarket for  {rnd_item_id}")
            readitemmarketdetails(rnd_item_id, message=message)                    
            time.sleep(0.3)

        if len(itemslist) <= 20:
            for item_id in itemslist:
                n+=1
                message = f"{datetime.now().strftime('%H:%M')} {n}/{len_itemlist}"
                library.print_flush(f"{message} getting last 20 itemarkets  {item_id}")
                readitemmarketdetails(item_id, message=message)                    
                time.sleep(0.3)
        print(f"Reviewed all {len(itemslist)} itemmarkets")   
        

    ## summary
    print(f"Buy: {len(buylist)}")
    buylist = sorted(buylist,key=itemgetter(1) )
    for i in buylist:
        print(i)
    print("done")
    print(f"Started {timestampnow_iso } completed {datetime.utcnow().isoformat()}")

if __name__ == '__main__':
    main()

