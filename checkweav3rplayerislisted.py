# return true if weav3r is currently listing player_id having item_id
#python3 checkweav3rplayerislisted.py playerid itemid

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
import concurrent.futures
import library

# v1
parser = argparse.ArgumentParser()
parser.add_argument("--truncatebazaar", action="store_true",  help="Truncate the bazaar table, run this to reset.")
parser.add_argument("--debug", action="store_true",  help="Show detailed tracing log")
parser.add_argument("--debugsql", action="store_true",  help="Show SQLite execution")
parser.add_argument("player_id")
parser.add_argument("item_id")

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
    library.dbcon.set_trace_callback(print)



def main():
    # https://weav3r.dev/api/marketplace/1086
    apiurl = 'https://weav3r.dev/api/marketplace/'
    apiendpoint = apiurl + str(args.item_id) 
    print(f"Getting {apiendpoint} ")
    response = requests.get(apiendpoint)
    print(f"Status code is {response.status_code}")
    try:
        bizlist = response.json()
    except Exception as e:
        print(f"Error {response} calling api {apiendpoint} {e} for item {args.item_id}")
        return None
    bizlist = bizlist.get('listings', None)
    if bizlist is None:
        print(f"Data issue listings is None {bizlist}")
    else:
        n=0
        found=False
        for i in bizlist:
            n+=1
            mm=''
            if str(i['player_id']) == str(args.player_id):
                found=True
                mm = "**** "
            print(f"{mm}{n}/{len(bizlist)}: {i['player_id']} {i['player_name']} {i['quantity']} {i['price']} {i['content_updated_relative']}{mm}")
        if found:
            print(f"Player {args.player_id} exists in Weav3r database.")
        else:
            print("------x------")
            print(f"NOT FOUND Player {args.player_id} NOT FOUND.")

if __name__ == '__main__':
    main()