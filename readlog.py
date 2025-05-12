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
# v22
#
    # sqlite viewer online with export-to-csv https://inloop.github.io/sqlite-viewer/
    # sqlite viewer with refresh https://sqliteviewer.app/#/pytorn.db/table/userlog/
    # json viewer https://jsonformatter.org/

 
parser = argparse.ArgumentParser()
parser.add_argument("-api", "--apikey", help="Api key. Stored after first use")
parser.add_argument("--truncatereference", action="store_true",  help="Reload and rebuild the reference tables Item, Logtype, LogCategory.")
parser.add_argument("--truncateplayerprofile", action="store_true",  help="Delete and re-create the playerprofile table.")
parser.add_argument("--truncatecompany", action="store_true",  help="reload company details")
parser.add_argument("--truncateitem", action="store_true",  help="reload item details")
parser.add_argument("--truncatethreadstatus", action="store_true",  help="recreate threadstatus table")
parser.add_argument("--truncatemarket", action="store_true",  help="recreate threadstatus table")
parser.add_argument("--truncatebazaar", action="store_true",  help="reload bazaar details")
parser.add_argument("--nolog", action="store_true",  help="Skip checking the log and downloading")
parser.add_argument("--debug", action="store_true",  help="Show detailed tracing log")
parser.add_argument("--debugsql", action="store_true",  help="Show SQLite execution")
parser.add_argument("--sleep",   help="How long in seconds to sleep to throttle the API. Default=5s")
parser.add_argument("--dbage",   help="API refreshed if age > dbage. Default = 30mins")
parser.add_argument("--showsecrets", action="store_true",  help="show the secrets")
parser.add_argument("--dryrun", action="store_true",  help="Do a run using the last 100 log entries in the base API")
parser.add_argument("--logstart",   help="Timestamp to go back to")

args = parser.parse_args()
library.args = args
secrets = {}
apiurl = 'https://api.torn.com/v2/'
dbcon = sqlite3.connect('pytorn.db')
library.dbcon = dbcon
apicount = 0
library.apicount = 0
library.timestart = datetime.now()

dlog = library.debuglog()
library.dlog = dlog

if args.debugsql:
    # trace calls
    library.dbcon.set_trace_callback(print)

    
def get_me():
    section = 'user'
    selections = 'basic'
    apiendpoint = apiurl + section + '?' + 'selections=' + selections
    headers = {'Authorization':'ApiKey '+ secrets['apikey']}
    response = requests.get(apiendpoint, headers = headers)
    meme = response.json() 
    print(meme['name'])
    print(meme)

def get_log():
    res=library.get_api(section='user',selections='log')
    return res



def get_log_createevnet():
    accountcreatelog=library.get_api(section='user',selections='log', cat='1')
    #https://api.torn.com/v2/user?selections=log&cat=1
    accountcreationevent = None
    for key, values in accountcreatelog['log'].items():
        if values.get('title') == 'Created account':
            accountcreationevent = values.get('timestamp','')
    if not accountcreationevent:
        print("ERROR: Can't find the account creation event")
        return None
    return accountcreatelog
    print(accountcreationevent)
    print(library.timestamptodate(accountcreationevent))

def savesecrets():
    secretfile = 'secrets.json'
    with open(secretfile, 'w') as ff:
        json.dump(secrets, ff)

def checkinit():
    global secrets
    ischeck = False
    secretfile = 'secrets.json'
    secretfilep = Path(secretfile)
    if secretfilep.is_file():
        try:
            with open(secretfile, 'r') as ff:
                library.secrets = json.load(ff)
        except Exception as e:
            print(f"ERROR: Cannot load secrets {e}")
            return False
    if args.apikey:
        library.secrets['apikey'] = args.apikey
        library.savesecrets()

    if not library.secrets.get('apikey',None):
        print("ERROR: there is no API key. Initialise with the --apikey argument.")
        return False
    
    return True

    return
    if args.apikey:
        secrets['apikey'] = args.apikey
        savesecrets()
        return True
    else:
        secretfile = 'secrets.json'
        secretfilep = Path(secretfile)
        if not secretfilep.is_file():
            print("ERROR: there is no API key. Initialise with the --apikey argument.")
            return False
        try:
            with open(secretfile, 'r') as ff:
                secrets = json.load(ff)
        except Exception as e:
            print(f"ERROR: Cannot load secrets {e}")
            return False
        try:
            if not secrets['apikey']:
                print(f"ERROR: Apikey not found in secrets")
                return False
        except Exception as e:
            print(f"ERROR: apikey not found in secrets {e}")
            return False
    return True

def init_database():
    Path('textfiles').mkdir(parents=False, exist_ok=True)
    if args.truncateplayerprofile:
        library.execute_sql("DROP TABLE playerprofile")
    if args.truncatereference:
        library.execute_sql("DROP TABLE IF EXISTS item")
        library.execute_sql("DROP TABLE IF EXISTS logtype")
        library.execute_sql("DROP TABLE IF EXISTS logcategory")
        library.execute_sql("DROP TABLE IF EXISTS company")
        library.execute_sql("DROP TABLE IF EXISTS threadstatus")
    if args.truncatecompany:
        library.execute_sql("DROP TABLE IF EXISTS company")
    if args.truncatethreadstatus:
        library.execute_sql("DROP TABLE IF EXISTS threadstatus")
    if args.truncatemarket:
        library.execute_sql("DROP TABLE IF EXISTS market")
    if args.truncatebazaar:
        library.execute_sql("DROP TABLE IF EXISTS bazaar")
    if args.truncateitem:
        library.execute_sql("DROP TABLE IF EXISTS item")
    #dbcon.execute("DROP TABLE userlog")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS userlog (id INTEGER PRIMARY KEY, log_id TEXT UNIQUE, log_type TEXT, title TEXT, 
        timestamp INTEGER, torndatetime TEXT,
        data TEXT, params TEXT )""")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS market (id INTEGER PRIMARY KEY, item_id INTEGER UNIQUE, price INTEGER, quantity INTEGER )""")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS logtype (id INTEGER PRIMARY KEY, logtype_id INTEGER UNIQUE, title TEXT )""")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS logcategory (id INTEGER PRIMARY KEY, logcategory_id INTEGER UNIQUE, title TEXT )""")
    library.execute_sql("CREATE INDEX IF NOT EXISTS idxlc_logcategory_id ON logcategory (logcategory_id)")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS company (id INTEGER PRIMARY KEY, company_id INTEGER UNIQUE, name TEXT )""")
    library.execute_sql("CREATE INDEX IF NOT EXISTS idxco_company_id ON company (company_id)")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS item (id INTEGER PRIMARY KEY, updated_on TEXT, 
        item_id INTEGER UNIQUE, name TEXT ,
        description TEXT, effect TEXT, requirement TEXT, type TEXT ,
        sub_type TEXT, is_masked TEXT, is_tradable TEXT, 
        is_found_in_city TEXT, vendor_country TEXT, vendor_name TEXT, 
        buy_price INTEGER, sell_price INTEGER, market_price INTEGER,
        circulation INTEGER, category TEXT, stealth_level INTEGER,
        label TEXT DEFAULT '',
        monitorprice INTEGER, last_sellprice INTEGER , last_buyprice INTEGER )""")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS threadstatus (id INTEGER PRIMARY KEY, updated_on TEXT, 
        item_id INTEGER UNIQUE, status TEXT , statuscount INTEGER )""")
    library.execute_sql("CREATE INDEX IF NOT EXISTS idxitm_item_id ON item (item_id)")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS playerprofile (id INTEGER PRIMARY KEY, 
        attackingattackswon INTEGER,
        attackingattackslost INTEGER,
        attackingdefendswon INTEGER,
        attackingdefendslost INTEGER,
        attackingdefendstotal INTEGER,
        attackinghighestlevelbeaten INTEGER,
        attackingkillstreakbest INTEGER,
        attackingkillstreakcurrent INTEGER,
        attackinghitssuccess INTEGER,
        attackinghitsmiss INTEGER,
        attackinghitscritical INTEGER,
        attackinghitsonehitkills INTEGER,
        attackingdamagetotal INTEGER,
        attackingdamagebest INTEGER,
        attackingnetworthmoneymugged INTEGER,
        attackingnetworthlargestmug INTEGER,
        attackingammunitiontotal INTEGER,
        jobsjobpointsused INTEGER,
        jobstrainsreceived INTEGER,
        tradingitemsboughtmarket INTEGER,
        tradingitemsboughtshops INTEGER,
        tradingpointsbought INTEGER,
        tradingpointssold INTEGER,
        tradingbazaarcustomers INTEGER,
        tradingbazaarsales INTEGER,
        tradingbazaarprofit INTEGER,
        hospitaltimeshospitalized INTEGER,
        hospitalmedicalitemsused INTEGER,
        hospitalbloodwithdrawn INTEGER,
        crimesoffensestotal INTEGER,
        crimesskillssearchforcash INTEGER,
        crimesskillsbootlegging INTEGER,
        crimesskillsgraffiti INTEGER,
        crimesskillsshoplifting INTEGER,
        crimesskillspickpocketing INTEGER,
        crimesskillscardskimming INTEGER,
        crimesskillsburglary INTEGER,
        crimesskillshustling INTEGER,
        crimesskillsdisposal INTEGER,
        crimesskillscracking INTEGER,
        crimesskillsforgery INTEGER,
        crimesskillsscamming INTEGER,
        bountiesplacedamount INTEGER,
        bountiesplacedvalue INTEGER,
        bountiescollectedamount INTEGER,
        bountiescollectedvalue INTEGER,
        bountiesreceivedamount INTEGER,
        bountiesreceivedvalue INTEGER,
        itemsusedbooks INTEGER,
        itemsusedboosters INTEGER,
        itemsusedconsumables INTEGER,
        itemsusedcandy INTEGER,
        itemsusedalcohol INTEGER,
        itemsusedenergy INTEGER,
        itemsusedenergydrinks INTEGER,
        itemsusedstatenhancers INTEGER,
        itemsusedeastereggs INTEGER,
        itemsvirusescoded INTEGER,
        traveltotal INTEGER,
        traveltimespent INTEGER,
        travelitemsbought INTEGER,
        travelattackswon INTEGER,
        traveldefendslost INTEGER,
        drugscannabis INTEGER,
        drugsecstasy INTEGER,
        drugsketamine INTEGER,
        drugslsd INTEGER,
        drugsopium INTEGER,
        drugspcp INTEGER,
        drugsshrooms INTEGER,
        drugsspeed INTEGER,
        drugsvicodin INTEGER,
        drugsxanax INTEGER,
        drugstotal INTEGER,
        drugsoverdoses INTEGER,
        drugsrehabilitationsamount INTEGER,
        drugsrehabilitationsfees INTEGER,
        networthtotal INTEGER,
        otheractivitytime INTEGER,
        otheractivitystreakcurrent INTEGER,
        otheractivitystreakbest INTEGER,
        othermeritsbought INTEGER,
        otherrefillsenergy INTEGER,
        otherrefillsnerve INTEGER,
        otherrefillstoken INTEGER,
        otherdonatordays INTEGER,
        level INTEGER,
        honor INTEGER,
        signup TEXT,
        awards INTEGER,
        friends INTEGER,
        enemies INTEGER,
        age INTEGER,
        donator INTEGER,
        playerid INTEGER UNIQUE,
        name TEXT,
        revivable INTEGER,
        lifecurrent INTEGER,
        lifemaximum INTEGER,
        statusdescription TEXT,
        statusdetails TEXT,
        statusstate TEXT,
        statusuntil INTEGER,
        jobcompanyid INTEGER,
        jobcompanyname TEXT,
        jobcompanytype TEXT,
        factionfactionid INTEGER,
        factiondaysinfaction INTEGER,
        factionfactionname TEXT,
        marriedspouseid TEXT,
        marriedspousename TEXT,
        stateshospitaltimestamp INTEGER,
        statesjailtimestamp INTEGER,
        lastactionstatus TEXT,
        lastactiontimestamp INTEGER,
        lastactionrelative TEXT,
        profileupdateon TEXT,
        statsupdatedon TEXT,
        playerlastinteraction TEXT
    )""")
    library.execute_sql("CREATE INDEX IF NOT EXISTS idxpl_player_id ON playerprofile (playerid)")
    library.execute_sql("""CREATE TABLE IF NOT EXISTS bazaar (id INTEGER PRIMARY KEY, player_id INTEGER , player_name TEXT, 
        api TEXT,
        bazaarupdated_unix INTEGER, 
        bazaarupdated_iso TEXT,
        updateon TEXT, item_id INTEGER, name TEXT, type TEXT, quantity INTEGER, price INTEGER, 
        market_price INTEGER, sell_price INTEGER)""")
    library.execute_sql("CREATE INDEX IF NOT EXISTS idxbz_item_id ON bazaar (item_id)")
    library.execute_sql("CREATE INDEX IF NOT EXISTS idxbz_player_id ON bazaar (player_id)")
    
    res = library.get_cur(sql='SELECT count(*) FROM logtype').fetchone()
    rowcount = 0
    if res[0] == 0:
        dlog.message(f"Getting logtype from the Torn API.")
        res = library.get_api(section='torn/logtypes')
        sql = 'INSERT OR IGNORE INTO logtype (logtype_id, title) values (?,?)'
        cur = dbcon.cursor()
        rowcount = 0
        for value in res['logtypes']:
            rowcount += 1
            library.library.print_flush(f"{rowcount} {value['title']}")
            cur.execute(sql, ( 
            value['id'], value['title']
            ))
        print()
        dbcon.commit()
    res = library.get_cur(sql='SELECT count(*) FROM logcategory').fetchone()
    if res[0] == 0:
        dlog.message(f"Getting logcategories from the Torn API.")
        res = library.get_api(section='torn/logcategories')
        sql = 'INSERT OR IGNORE INTO logcategory (logcategory_id, title) values (?,?)'
        cur = dbcon.cursor()
        rowcount = 0
        for value in res['logcategories']:
            rowcount += 1
            library.print_flush(f"{rowcount} {value['title']}")
            cur.execute(sql, (
            value['id'], value['title']
            ))
        print()
        dbcon.commit()
    res = library.get_cur(sql='SELECT count(*) FROM item').fetchone()
    if res[0] == 0:
        dlog.message(f"Getting items from the Torn API.")
        res = library.get_api(section='torn/items')
        sql = """INSERT OR IGNORE INTO item (item_id, updated_on, 
            name, description, effect, 
            requirement , type ,
            sub_type , is_masked, is_tradable , 
            is_found_in_city , vendor_country , vendor_name , 
            buy_price , sell_price , market_price ,
            circulation , category , stealth_level ) 
            values (?,?,
                ?,?,?,
                ?,?,
                ?,?,?,
                ?,?,?,
                ?,?,?,
                ?,?,?
                )"""
        cur = dbcon.cursor()
        rowcount = 0
        for value in res['items']:
            rowcount += 1
            library.print_flush(f"{rowcount} {value['name']}")
            value_param = []
            value_param.append(value['id'])
            value_param.append(datetime.now().isoformat())
            value_param.append(value['name'])
            value_param.append(value['description'])
            value_param.append(value['effect'])
            value_param.append(value['requirement'])
            value_param.append(value['type'])
            value_param.append(value['sub_type'])
            value_param.append(value['is_masked'])
            value_param.append(value['is_tradable'])
            value_param.append(value['is_found_in_city'])
            if value.get('value',None) is not None:
                if value['value'].get('vendor', None) is not None:
                    value_param.append(value['value']['vendor'].get('country',''))
                else:
                    value_param.append(None)
            else:
                value_param.append(None)
            if value.get('value',None) is not None:
                if value['value'].get('vendor', None) is not None:
                    value_param.append(value['value']['vendor'].get('name',''))
                else:
                    value_param.append(None)
            else:
                value_param.append(None)
            value_param.append(value.get('value',{}).get('buy_price',None))
            value_param.append(value.get('value',{}).get('sell_price',None))
            value_param.append(value.get('value',{}).get('market_price',None))
            value_param.append(value['circulation'])
            if value.get('details',None) is not None:
                value_param.append(value['details'].get('category',''))
                value_param.append(value['details'].get('stealth_level',''))
            else:
                value_param.append(None)
                value_param.append(None)
            # 419 = small sc
            # 1086 = driver l
            cur.execute(sql, value_param)
            #value['id'], datetime.now().isoformat(),
            #value['name'], value['description'], value['effect'],
            #value['requirement'],value['type'],
            #value['sub_type'],value['is_masked'],value['is_tradable'],
            #value['is_found_in_city'],value.get('value',{}).get('vendor',{}).get('country',''), value.get('value',{}).get('vendor',{}).get('name',''),
            #value.get('value',{}).get('buy_price',None),value.get('value',{}).get('sell_price',None), value.get('value',{}).get('market_price',None),
            #value['circulation'], value['details']['category'], value['details']['stealth_level']
            #))
        print()
        dbcon.commit()

    # https://api.torn.com/torn/?selections=companies&key=*
    res = library.get_cur(sql='SELECT count(*) FROM company').fetchone()
    if res[0] == 0:
        dlog.message(f"Getting companies from the Torn API.")
        res = library.get_api(section='torn', selections='companies',version=1)
        sql = 'INSERT OR IGNORE INTO company (company_id, name) values (?,?)'
        cur = dbcon.cursor()
        rowcount = 0
        for key, value in res['companies'].items():
            rowcount += 1
            library.print_flush(f"{rowcount} {value['name']}")
            cur.execute(sql, (
            key, value['name']
            ))
        print()
        dbcon.commit()
  
def writelogtodb(thelog, ts_stop = None):
        fieldnames = library.get_cur_list(sql="SELECT name FROM PRAGMA_TABLE_INFO('userlog')")
        sql1 = 'INSERT OR IGNORE INTO userlog (log_id, log_type, title, timestamp, torndatetime, data, params'
        sql2 = ' values (?,?,?,?,?,?,?'
        cur = dbcon.cursor()
        rowcount = 0
        ts_lastread = None
        for key, value in thelog['log'].items():
            value['data'] = value.get('data',{})
            plog = playerlog(value)
            profile = playerprofile(plog.get_playerid())
            rowcount += 1
            library.print_flush(f"{rowcount} {library.timestamptodate(value['timestamp'])} {value['title']}")
            sql3 = sql1
            sql4 = sql2
            theparams = [key, 
                value['log'], value['title'],
                value['timestamp'], library.timestamptodate(value['timestamp']), 
                json.dumps(value['data']), 
                json.dumps(value['params'])]
            valuedata = value['data'].copy()
            if plog.items:
                valuedata.update(plog.items)
            for datakey, datavalue in valuedata.items():
                datakey += '_'
                if type(datavalue) is list:
                    datavalue =  str(datavalue)
                elif type(datavalue) is dict:
                    datavalue =  str(datavalue)
                sql3 += ',' + datakey
                sql4 += ',?'
                theparams.append(datavalue)
                if datakey not in fieldnames:
                    dbcon.execute('ALTER TABLE userlog ADD ' + datakey + ' TEXT')
                    fieldnames.append(datakey)
            sql3 += ') ' + sql4 + ')'
            ts_lastread = value['timestamp']
            if ts_stop and (ts_lastread <= ts_stop):
                dbcon.commit()
                return 'HALT', ts_lastread
            cur.execute(sql3, theparams)
        dbcon.commit()
        return 'OK', ts_lastread

def main():
    global timestart
    if not checkinit():
        print("Error. Stopped")
        sys.exit()
    init_database()
    max_timestamp = None
    min_timestamp = None
    logtypes = []
    res = library.get_cur(sql='SELECT MAX(timestamp) as max_timestamp, MIN(timestamp) as min_timestamp, count(*) FROM userlog').fetchone()
    max_timestamp = res[0]
    min_timestamp = res[1]
    ts_stop = max_timestamp
    ts_lastread = None
    logrowcount = res[2]
    maxcount=5
    itercount = 0
    
    if not args.nolog:
        if (not args.logstart) and (max_timestamp is None):
            print('No downloaded userlog. Getting latest log')    
            writelogtodb( get_log() )
            res = library.get_cur(sql='SELECT MAX(timestamp) as max_timestamp, MIN(timestamp) as min_timestamp, count(*) FROM userlog').fetchone()
            max_timestamp = res[0]
            min_timestamp = res[1]
            logrowcount = res[2]
            print()
            print(f'Latest log entry {max_timestamp} {library.timestamptodate(max_timestamp)}')
            print(f'Earliest log entry {min_timestamp} {library.timestamptodate(min_timestamp)}')
            print(f'Total log rows {logrowcount} ')
        else:
            if not args.logstart:
                print("A log exists in the local database")
                print(f'Latest log entry {max_timestamp} {library.timestamptodate(max_timestamp)}')
                print(f'Earliest log entry {min_timestamp} {library.timestamptodate(min_timestamp)}')
                print(f'Total log rows {logrowcount} ')
            else:
                # 1741088705
                max_timestamp = int(args.logstart)
                dlog.message(f"logstart is {args.logstart} {library.timestamptodate(args.logstart)}")
            reslogcount = 0
            dlog.message(f"Getting most recent log file")
            reslog = library.get_api(section='user',selections='log', )
            while reslog['log']:
                reslogcount += 1
                status, ts_lastread = writelogtodb( reslog , ts_stop = max_timestamp )
                dlog.message(f"Got log file {status} Last log entry is {ts_lastread} {library.timestamptodate(ts_lastread)}")
                if status == 'HALT':
                    dlog.message(f"Got to the existing entry, therefore halting {min_timestamp} {library.timestamptodate(min_timestamp)}")
                    break
                dlog.message(f"Getting log to event {ts_lastread - 1}")
                reslog = library.get_api(section='user',selections='log', ts_to=str(ts_lastread - 1))
                if reslogcount > 5000000:
                    print('Halting due to >50 break ...')
                    sys.exit()
            res = library.get_cur(sql='SELECT MAX(timestamp) as max_timestamp, MIN(timestamp) as min_timestamp, count(*) FROM userlog').fetchone()
            max_timestamp = res[0]
            min_timestamp = res[1]
            logrowcount = res[2]
            print(f"DONE The latest timestamp is {max_timestamp} ({library.timestamptodate(max_timestamp)}, the numer of rows is {logrowcount})")
    
    if args.dryrun:
        thelog =  get_log() 
        fieldnames = library.get_cur_list(sql="SELECT name FROM PRAGMA_TABLE_INFO('userlog')")
        sql1 = 'INSERT OR IGNORE INTO userlog (log_id, log_type, title, timestamp, torndatetime, data, params'
        sql2 = ' values (?,?,?,?,?,?,?'
        rowcount = 0
        for key, value in thelog['log'].items():
            plog = playerlog(value)
            profile = playerprofile(plog.get_playerid())
            rowcount += 1
            if plog.log_type == 1225: # bazaar buy
                print(f"Log type 1225 bazaar buy")
                pass
            else:
                continue
            print(f"{rowcount} {library.timestamptodate(value['timestamp'])} {value['title']}")
            sql3 = sql1
            sql4 = sql2
            theparams = [key, 
                value['log'], value['title'],
                value['timestamp'], library.timestamptodate(value['timestamp']), 
                json.dumps(value['data']), 
                json.dumps(value['params'])]
            valuedata = value['data'].copy()
            if plog.items:
                valuedata.update(plog.items)
            for datakey, datavalue in valuedata.items():
                datakey += '_'
                if type(datavalue) is list:
                    datavalue =  str(datavalue)
                elif type(datavalue) is dict:
                    datavalue =  str(datavalue)
                sql3 += ',' + datakey
                sql4 += ',?'
                theparams.append(datavalue)
                if datakey not in fieldnames:
                    fieldnames.append(datakey)
            sql3 += ') ' + sql4 + ')'
            dlog.debug(f"writing to db {sql3} {theparams}")
            print(f"DRY RUN {sql3} {theparams}")
        
    if args.showsecrets:
        #python3 readlog.py --showsecrets
        print(f"Secrets: {secrets}")

        
    
    timediff = (datetime.now() - library.timestart).total_seconds() / 60
    print(f"Complete. Api called {apicount} times. Started {library.timestart} duration {timediff} minutes. Approximately {apicount / timediff} API per minute.")

class playerprofile:
    playerattribute = {}
    playerid = None
    existsdb = None
    profilejson = None
    fieldnames = None
    profile_age = None    
    personalstatsjson = None
    name = None
    def __init__(self, playerid = None):
        if playerid == 'me':
            self.get_profile_me()
            self.get_personalstats()
        elif playerid is not None:
            self.playerid = playerid
            if not self.exists_db():
                self.insertplayerid()
#    def  
#                if not self.profile_isrecent():
#                self.getapi_playerprofile()
    def getattrib(self, value):
        if self.profilejson.get(value,''):
            return self.profilejson.get(value,'')
        else:
            return self.personalstatsjson.get(value,'')
        return ''
    def exists_db(self):
        if self.existsdb is None:
            dlog.debug(f"playerprofile getting profile age {self.playerid}")
            res = library.get_cur(sql='SELECT (julianday(current_timestamp) -julianday(profileupdateon)) * 24 * 60 , name FROM playerprofile WHERE playerid=?',args=(self.playerid ,)).fetchone()
            if res is not None:
                self.existsdb = True
                self.profile_age = res[0]
                self.name = res[1]
            else:
                self.existsdb = False
        return self.existsdb    
    def get_personalstats_me(self):
        # 'https://api.torn.com/v2/user/personalstats?cat=popular' -- my personal stats
        # 'https://api.torn.com/v2/user/1326025/personalstats?cat=popular&stat=' -- player personal stats
        dlog.message('Getting my personal stats from API')
        self.personalstatsjson = library.get_api(section='user',selections='personalstats')
    def get_personalstats(self):
        # https://api.torn.com/v2/user/1326025/personalstats?cat=popular&stat=
        dlog.message(f'Getting personal stats for {self.playerid} from API')
        self.personalstatsjson = library.get_api(section='user',urlbreadcrumb='personalstats', slug=str(self.playerid), cat='popular')['personalstats']
        self.personalstatsjson = library.flatten_json(self.personalstatsjson,cleankey=True, delimiter='')
        dlog.debug(f'Player personalstats json {self.personalstatsjson}')
        self.update_db()
    def get_profile_me(self):
        # 'https://api.torn.com/v2/user?selections=profile' -- my profile
        dlog.message('Getting my profile from API')
        self.profilejson = library.get_api(section='user',selections='profile')
        self.profilejson = library.flatten_json(self.profilejson,cleankey=True, delimiter='')
        
        dlog.debug(f'my profile json {self.profilejson}')
        self.playerid = self.getattrib('playerid')
        self.name =  self.getattrib('name')
        dlog.debug(f"My playerid = {self.playerid}")
        self.insertplayerid()
        self.update_db()
    def get_profile_age(self):
        self.exists_db()
        return self.profile_age
    def profile_isrecent(self):
        if self.profile_age is None:
            return False
        elif self.profile_age < ( 30 if args.dbage is None else float( args.dbage) ):
            return True
        return False
    def insertplayerid(self):
        sql='INSERT OR IGNORE INTO playerprofile (playerid) VALUES (?)'
        dlog.debug(f"Attempting to insert player id {self.playerid} {sql}")
        timestampnow_iso = datetime.now().isoformat()
        cur = dbcon.cursor()
        cur.execute(sql, (self.playerid, ) )
        dbcon.commit()
    def getapi_playerprofile(self):
        # https://api.torn.com/v2/user?selections=profile&id=1326025
        dlog.message(f"Getting playerprofile from API for {self.playerid}")
        self.profilejson = library.get_api(section='user',selections='profile', id=str(self.playerid))
        self.profilejson = library.flatten_json(self.profilejson,cleankey=True, delimiter='')
        self.name = self.profilejson['name']
        self.update_db()
    def update_db(self):
        # this is why ORMs like Alchemy or Django exist
        timestampnow_iso = datetime.now().isoformat()
        sql = "UPDATE playerprofile SET profileupdateon = ? ,"
        dlog.debug(f"Attempting to update player id {self.playerid} {sql}")
        params = [timestampnow_iso,]
        for key, value in self.profilejson.items():
            if key in self.get_fieldnames():
                if key in ('playerid',):
                    continue
                sql += f" {key} = ? ,"
                params.append(value)
        if self.personalstatsjson:
            for key, value in self.personalstatsjson.items():
                if key in self.get_fieldnames():
                    if key in ('playerid',):
                        continue
                    sql += f" {key} = ? ,"
                    params.append(value)
        sql = sql[:-1]
        params.append(self.playerid)
        sql += " WHERE  playerid = ?"
        cur = dbcon.cursor()
        cur.execute(sql, params )
        dbcon.commit()

    
    
    def get_fieldnames(self):
        if not self.fieldnames:
            self.fieldnames = library.get_cur_list(sql="SELECT name FROM PRAGMA_TABLE_INFO('playerprofile')")
        return self.fieldnames

class playerlog:
    log_type = None
    title = None
    timestamp = None
    timestamp_iso = None
    data = None
    params = None
    items=None ####
    def __init__(self, values):
        self.log_type = values['log']
        self.title = values['title']
        self.timestamp = values['timestamp']
        self.timestamp_iso = library.timestamptodate(self.timestamp)
        self.data = values.get('data',{})
        self.params = values.get('params',{})
        self.items = None
        if self.data.get('items', None):
            self.items = library.flatten_json(self.data['items'],cleankey=True, delimiter='', name='i')
        
    def get_playerid(self):
        if self.log_type == 1225: # bazaar buy
            return self.data['seller']
        elif self.log_type == 8156: # attack mug receive
            return self.data['attacker']
        elif self.log_type == 5361: # bust receive success
            return self.data['buster']
        elif self.log_type == 1113: # item market sell
            return self.data['buyer']
        elif self.log_type == 1112: # item market buy
            return self.data['seller']
        else:
            return None

if __name__ == '__main__':
    main()





