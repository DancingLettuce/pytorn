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
import library
from library import libraryversion


parser = argparse.ArgumentParser()
parser.add_argument("--getmarketfile",   help="Get market for all items in INFILE")
parser.add_argument("--limit",   help="only process the first X in the list", type=int)
parser.add_argument("--debugsql", action="store_true",  help="Show SQLite execution")
parser.add_argument("--showsecrets", action="store_true",  help="shows secrets")
parser.add_argument("--debug", action="store_true",  help="Show detailed tracing log")

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
    def __init__(self,**kwargs):
    # call the super by using super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
    def getitemlisting(self, itemid):
        # https://api.torn.com/v2/market/175/itemmarket
        res = library.get_api(section='market', slug=str(itemid),urlbreadcrumb='itemmarket' )
        self.listing = res['itemmarket']['listings']
        library.dlog.debug(f"Market listing {self.listing}")

def main():

    itemslist = []
    if args.getmarketfile:
        with open(args.getmarketfile) as fin:
            finl = fin.read().splitlines()
        
        for iid in finl:
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
            
        itemslist.sort()
        if args.limit:
            itemidslist = itemidslist[:args.limit]

        for item in itemslist:
            marketitems = []
            mkt = marketplace()
            mkt.getitemlisting(item)
            print(mkt.listing)
            sys.exit()
            n = 0
            for item in mkt.listing:
                themarketitem = marketitem(stockitem=thestockitem, market_price=item['price'], market_amount=item['amount'])
                print(item)
                print(themarketitem)
if __name__ == '__main__':
    main()


