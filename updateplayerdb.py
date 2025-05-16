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
import library



parser = argparse.ArgumentParser()
parser.add_argument("--limit",   help="only process the first X in the list", type=int)
parser.add_argument("--debugsql", action="store_true",  help="Show SQLite execution")
parser.add_argument("--showsecrets", action="store_true",  help="shows secrets")
parser.add_argument("--debug", action="store_true",  help="Show detailed tracing log")
parser.add_argument("--appendidfromfile",   help="append IDs from the file")
parser.add_argument("--refreshifolderthan",   help="number of days to refresh if data older than this, default=7", type=int)

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


class playerprofile:
    playerattribute = {}
    playerid = None
    existsdb = None
    profilejson = None
    fieldnames = None
    profile_age = None    
    personalstatsjson = None
    name = None
    level = None
    signup = None
    age = None
    age_now = None
    profileimage = None
    # icon 27=company, 9 = faction, 35=bazaar
    basiciconsicon27 = None
    basiciconsicon9 = None
    basiciconsicon35 = None
    api_error = None

    def __init__(self,**kwargs):
        #super().__init__(**kwargs)
        self.items_list = []
        for k,v in kwargs.items():
            setattr(self,k,v)
        if self.playerid:
            self.exists_db = self.exists_db()
    def getattrib(self, value):
        if self.profilejson.get(value,''):
            return self.profilejson.get(value,'')
        else:
            return self.personalstatsjson.get(value,'')
        return ''
    def exists_db(self):
        library.dlog.debug(f"playerprofile getting profile age {self.playerid}")
        res = library.get_cur(
            sql='SELECT (julianday(current_timestamp) -julianday(profileupdateon)) , name FROM playerprofile WHERE playerid=?',args=(self.playerid ,)).fetchone()
        if res is not None:
            self.profile_age = res[0]
            return True
        else:
            return False
            
    def get_personalstats(self):
        # https://api.torn.com/v2/user/1326025/personalstats?cat=popular&stat=
        dlog.message(f'Getting personal stats for {self.playerid} from API')
        self.personalstatsjson = library.get_api(section='user',urlbreadcrumb='personalstats', slug=str(self.playerid), cat='popular')['personalstats']
        self.personalstatsjson = library.flatten_json(self.personalstatsjson,cleankey=True, delimiter='')
        dlog.debug(f'Player personalstats json {self.personalstatsjson}')
        self.update_db()
    def profile_isrecent(self):
        if self.profile_age is None:
            return False
        elif self.profile_age < ( 30 if args.dbage is None else float( args.dbage) ):
            return True
        return False
    def insertplayerid(self):
        sql='INSERT OR IGNORE INTO playerprofile (playerid) VALUES (?)'
        dlog.debug(f"Attempting to insert player id {self.playerid} {sql}")
        timestampnow_iso = datetime.utcnow().isoformat()
        cur = dbcon.cursor()
        cur.execute(sql, (self.playerid, ) )
        dbcon.commit()
    def getapi_playerprofile(self):
        # https://api.torn.com/v2/user?selections=profile&id=1326025
        #library.dlog.message(f"Getting playerprofile from API for {self.playerid}")
        self.profilejson = library.get_api(section='user',selections='profile', id=str(self.playerid))
        self.api_error = self.profilejson.get('error', None)
        if self.api_error:
            print(f"API ERROR {self.api_error} for {self.playerid}")
            return None
        else:
            self.profilejson = library.flatten_json(self.profilejson,cleankey=True, delimiter='')
            # icon 27=company, 9 = faction, 35=bazaar
            attriblist = ['name', 'level', 'signup', 'age','basiciconsicon27', 'basiciconsicon9', 'basiciconsicon35']
            for i in attriblist:
                setattr(self, i, self.profilejson.get(i,None))
        
    def update_db(self):
        # this is why ORMs like Alchemy or Django exist
        timestampnow_iso = datetime.utcnow().isoformat()
        if self.exists_db:
            sql = """UPDATE playerprofile 
                SET name = ?, level=?, signup=?, age=?, profileupdateon=? ,
                basiciconsicon27=?, basiciconsicon9=?, basiciconsicon35=? 
                WHERE playerid=?"""
            params = (self.name, self.level, self.signup, self.age, timestampnow_iso, 
                self.basiciconsicon27, self.basiciconsicon9, self.basiciconsicon35,
                self.playerid)
        else:
            sql = """INSERT OR IGNORE  INTO playerprofile (name, level, signup, 
                age, profileupdateon, 
                basiciconsicon27=?, basiciconsicon9=?, basiciconsicon35=? ,
                playerid)
                VALUES (?,?,?,
                ?,?, ?)"""
            params = (self.name, self.level, self.signup, self.age, timestampnow_iso, 
                self.basiciconsicon27, self.basiciconsicon9, self.basiciconsicon35,
                self.playerid)
        library.execute_sql(sql=sql,args=params,many=False)


def appendidfromfile():
    itemslist = []
    params = []
    with open(args.appendidfromfile) as fin:
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
    library.execute_sql(sql="""INSERT OR IGNORE INTO playerprofile (playerid) VALUES (?);""",
        args=params, many=True)
    

def main():

    if args.appendidfromfile:
        appendidfromfile()
        print("--Done--")
        #sys.exit()
    itemidslist = library.get_cur_list(sql=f"""SELECT playerid 
        FROM playerprofile 
        WHERE (julianday(current_timestamp) -julianday(profileupdateon)) > {args.refreshifolderthan  if args.refreshifolderthan else 7}  
        or profileupdateon IS NULL or name IS NULL
        order by coalesce((julianday(current_timestamp) -julianday(profileupdateon)), '99') desc,
        playerid;""")
    #WHERE name is not NULL;""")
    
    if args.limit:
        itemidslist = itemidslist[:args.limit]

    n = 0
    for i in itemidslist:
        n += 1
        pp = playerprofile(playerid=i)
        pp.getapi_playerprofile()
        if pp.api_error:
            print(f"{n}/{len(itemidslist)} {i} api error, sleeping x 1")
            time.sleep(20)
            pp = playerprofile(playerid=i)
            pp.getapi_playerprofile()
        if pp.api_error:
            print(f"{n}/{len(itemidslist)} {i} api error, sleeping x 2")
            time.sleep(30)
            pp = playerprofile(playerid=i)
            pp.getapi_playerprofile()
        if pp.api_error:
            print(f"{n}/{len(itemidslist)} {i} api error, breaking x 3")
            break
        pp.update_db()
        time.sleep(0.3) 
        library.print_flush(f"{n}/{len(itemidslist)} {pp.name} {pp.playerid} {pp.age} {pp.basiciconsicon35}")
    
        



if __name__ == '__main__':
    main()