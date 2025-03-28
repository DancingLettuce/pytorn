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
# v18
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
parser.add_argument("--itemstotrack", help="Comma separated item IDs to track. Stored after first use.")
parser.add_argument("--nolog", action="store_true",  help="Skip checking the log and downloading")
parser.add_argument("--getmarketprices", action="store_true",  help="Get the prices for the itemstotrack")
parser.add_argument("--getplayerbyid",  help="Get the details for a specific playerid.  Comma delimit extra text to store in playerprofile.playerlastinteraction")
parser.add_argument("--debug", action="store_true",  help="Show detailed tracing log")
parser.add_argument("--debugsql", action="store_true",  help="Show SQLite execution")
parser.add_argument("--getfaction",   help="Get faction members")
parser.add_argument("--getbazaar",   help="Get bazaar for a given user")
parser.add_argument("--getbazaarfile",   help="Get bazaars for all users in INFILE")
parser.add_argument("--getmarketfile",   help="Get market for all items in INFILE")
parser.add_argument("--truncatebazaar", action="store_true",  help="reload bazaar details")
parser.add_argument("--readtextfiles", action="store_true",  help="Get Player ID etc from text files")
parser.add_argument("--outfile",   help="Export output to file")
parser.add_argument("--outfilehtml",   help="Export output to file but with HTML links ")
parser.add_argument("--dbtocsv",   help="Output DB table to csv, set --outfile if needed")
parser.add_argument("--noplayerstats", action="store_true",  help="Don't refresh player stats")
parser.add_argument("--sleep",   help="How long in seconds to sleep to throttle the API. Default=0.6s")
parser.add_argument("--dbage",   help="API refreshed if age > dbage. Default = 30mins")
parser.add_argument("--showsecrets", action="store_true",  help="List the prepared statement names")
parser.add_argument("--dryrun", action="store_true",  help="Do a run using the last 100 log entries in the base API")




args = parser.parse_args()
secrets = {}
apiurl = 'https://api.torn.com/v2/'
dbcon = sqlite3.connect('pytorn.db')
apicount = 0
timestart = datetime.now()

####################
## some useful defaults

default_itemstotrack = """419
    1350
 """
default_itemstotrack = list(map(int, default_itemstotrack.split() ))
default_itemstotrack = None
## end
####################

class debuglog():
    debuglog = []
    messagelog = []
    def __init__(self, message=''):
        if message:
            print(message)
    def debug(self, message):
        if args.debug:
            print('>' + message)
            self.messagelog.append(message)
    def message(self,message):
        print(message)
        self.messagelog.append(message)
    def print_messagelog(self):
        for line in self.messagelog:
            print(line)

dlog = debuglog()

if args.debugsql:
    # trace calls
    dbcon.set_trace_callback(print)

def readtextfile():
    #python3 readlog.py --readtextfiles --outfile ecstacyprofiles.txt --nolog
    filepaths = ('textfiles',)
    playerids = []

    if True:
        for filepath in filepaths:
            for p in Path(filepath).iterdir():
                #if p.stem != 't':
                #    continue
                print(f"Reading {p.stem} {p.suffix}")
                if p.name.startswith('#'):
                    continue
                if p.name.startswith('@'):
                    continue
                if p.suffix == '.zip':
                    continue
                if p.stat().st_size < 1:
                    continue 
                with open(p) as fin:
                    for line in fin:
                        # regex for mhtml files with newlines
                        #re.findall(r'https:\/\/www\.torn\.com\/bazaar\.php\?user=\WId=3D(.*)#\/', line)
                        # example for html single page <a href="https://www.torn.com/profiles.php?XID=2593057" target="_blank">
                        pid = re.findall(r'https:\/\/www\.torn\.com\/profiles\.php\?XID=(.*)" ', line)
                        if pid:
                            for id in pid:
                                if id not in playerids:
                                    playerids.append(id)
                    print(f"Found {len(playerids)} unique player IDs so far")
    #playerids = [2593057,2654680]
    print(playerids)
    
    playerprofiles = {}
    n = 0
    for id in playerids:
        n+=1
        pp = playerprofile(playerid=id)

        if not pp.exists_db():    
            print(f"Getting profile for {id}")
            pp.getapi_playerprofile()
        
        playerprofiles[id] = pp.name
        print(f"{n}/{len(playerids)} {id} {pp.name}")
    print("wrting")
    if args.outfile:
        with open(args.outfile, "w") as fout:
            for id in playerids:
                fout.write(str(id) + '\n')
        print(f"Written Player IDs to {args.outfile}")

    if args.outfilehtml:
        with open(args.outfilehtml, "w") as fout:
            fout.write("<HTML>\n")
            fout.write("<OL>\n")
            for key, value in playerprofiles.items():
                fout.write("<LI>")
                fout.write(f"""<a href='https://www.torn.com/profiles.php?XID={key}' target='_blank'>{value}</a> """ )
                fout.write("</LI>\n")
            fout.write("</OL>\n")
            fout.write("</HTML>\n")
        print(f"Written Player IDs to {args.outfilehtml}")

def get_api(section, selections='', cat='', ts_to='', ts_from='', id='', slug='', urlbreadcrumb='', version=2):
    global apicount
    timediff = (datetime.now() - timestart).total_seconds() / 60
    if apicount / timediff >= 97:
        print(f"Pausing for {'0.6' if args.sleep is None else args.sleep} seconds")
        time.sleep(0.6 if args.sleep is None else float(args.sleep))
    headers = None
    if version == 1:
        apiurl_v1 = 'https://api.torn.com/'
        apiendpoint = (apiurl_v1 + section + '/?' + 
            (('&selections=' + selections ) if selections else '') + 
            ('&key=' + secrets['apikey'] )  
            )
        headers = None
    else:
        # ts_to = timestamp to, ts_from = timestamp from
        apiendpoint = (apiurl + section + 
            (('/' + slug  ) if slug else '') + 
            (('/' + urlbreadcrumb  ) if urlbreadcrumb else '') + 
            '?' + 
            ((('&selections=' + selections ) if selections else '') + 
            (('&cat=' + cat ) if cat else '') + 
            (('&to=' + ts_to ) if ts_to else '')  + 
            (('&from=' + ts_from ) if ts_from else '') ) +
            (('&id=' + id ) if id else '') 
            )
        headers = {'Authorization':'ApiKey '+ secrets['apikey']}    
    dlog.debug(f">{apicount} Calling api v{version} {apiendpoint} " +
        (f"ts_from={timestamptodate(ts_from)}" if ts_from else '') + 
        (f"ts_to={timestamptodate(ts_to)}" if ts_to else '') )
    #print(f"{apicount} Calling api v{version} {apiendpoint}")
    
    response = requests.get(apiendpoint, headers = headers)
    apicount += 1
    timediff = (datetime.now() - timestart).total_seconds() / 60
    dlog.debug(f"Api called {apicount} times. Started {timestart} duration {timediff} minutes. Approximately {apicount / timediff} API per minute.")
    #print("got response")
    dlog.debug(f"Response code is {response}")
    meme = None
    try:
        meme = response.json()
    except Exception as e:
        print(f"Error {response} calling api {apiendpoint} {e}")
        return None
    dlog.debug(f">Got api response {meme}")
    return meme
     
def flatten_json(y,cleankey=False, delimiter = '.', name=''):
    out = {}
    def flatten(x, name=name):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + delimiter)
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + delimiter)
                i += 1
        else:
            if cleankey:
                name = name.replace('_','')
            if len(delimiter) >0:
                out[name[:-len(delimiter)]] = x
            else:
                out[name] = x
    flatten(y)
    return out

def print_flush(message):
    """Print a string and do not move the cursor for progress-type displays"""
    message = message + (' ' * 80)
    message = message[:80]
    print ( f"{message }", end= "\r", flush=True )
    #print ( f"{message } {' ' * 80 }", end= "\r", flush=True )
    
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
    res=get_api(section='user',selections='log')
    return res

def timestamptodate(ts):
    if ts:
        ts=int(ts)
        return datetime.fromtimestamp(ts).isoformat()
    else:
        return None

def get_log_createevnet():
    accountcreatelog=get_api(section='user',selections='log', cat='1')
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
    print(timestamptodate(accountcreationevent))

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
                secrets = json.load(ff)
        except Exception as e:
            print(f"ERROR: Cannot load secrets {e}")
            return False
    if args.apikey:
        secrets['apikey'] = args.apikey
    if default_itemstotrack:
        secrets['itemstotrack'] = default_itemstotrack
    if args.itemstotrack:
        secrets['itemstotrack'] = list(map(int, args.itemstotrack.split(',') ))
    if not secrets.get('apikey',None):
        print("ERROR: there is no API key. Initialise with the --apikey argument.")
        return False
    savesecrets()
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
        execute_sql("DROP TABLE playerprofile")
    if args.truncatereference:
        execute_sql("DROP TABLE IF EXISTS item")
        dexecute_sql("DROP TABLE IF EXISTS logtype")
        execute_sql("DROP TABLE IF EXISTS logcategory")
        execute_sql("DROP TABLE IF EXISTS company")
    if args.truncatecompany:
        execute_sql("DROP TABLE IF EXISTS company")
    if args.truncatebazaar:
        execute_sql("DROP TABLE IF EXISTS bazaar")
    if args.truncateitem:
        execute_sql("DROP TABLE IF EXISTS item")
    #dbcon.execute("DROP TABLE userlog")
    execute_sql("""CREATE TABLE IF NOT EXISTS userlog (id INTEGER PRIMARY KEY, log_id TEXT UNIQUE, log_type TEXT, title TEXT, 
        timestamp INTEGER, torndatetime TEXT,
        data TEXT, params TEXT )""")
    execute_sql("""CREATE TABLE IF NOT EXISTS logtype (id INTEGER PRIMARY KEY, logtype_id INTEGER UNIQUE, title TEXT )""")
    execute_sql("""CREATE TABLE IF NOT EXISTS logcategory (id INTEGER PRIMARY KEY, logcategory_id INTEGER UNIQUE, title TEXT )""")
    execute_sql("CREATE INDEX IF NOT EXISTS idxlc_logcategory_id ON logcategory (logcategory_id)")
    execute_sql("""CREATE TABLE IF NOT EXISTS company (id INTEGER PRIMARY KEY, company_id INTEGER UNIQUE, name TEXT )""")
    execute_sql("CREATE INDEX IF NOT EXISTS idxco_company_id ON company (company_id)")
    execute_sql("""CREATE TABLE IF NOT EXISTS item (id INTEGER PRIMARY KEY, updated_on TEXT, 
        item_id INTEGER UNIQUE, name TEXT ,
        description TEXT, effect TEXT, requirement TEXT, type TEXT ,
        sub_type TEXT, is_masked TEXT, is_tradable TEXT, 
        is_found_in_city TEXT, vendor_country TEXT, vendor_name TEXT, 
        buy_price INTEGER, sell_price INTEGER, market_price INTEGER,
        circulation INTEGER, category TEXT, stealth_level INTEGER,
        label TEXT DEFAULT '',
        monitorprice INTEGER  )""")
    execute_sql("CREATE INDEX IF NOT EXISTS idxitm_item_id ON item (item_id)")
    execute_sql("""CREATE TABLE IF NOT EXISTS playerprofile (id INTEGER PRIMARY KEY, 
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
    execute_sql("CREATE INDEX IF NOT EXISTS idxpl_player_id ON playerprofile (playerid)")
    execute_sql("""CREATE TABLE IF NOT EXISTS bazaar (id INTEGER PRIMARY KEY, player_id INTEGER , 
        updateon TEXT, item_id INTEGER, name TEXT, type TEXT, quantity INTEGER, price INTEGER, market_price INTEGER, sell_price INTEGER)""")
    execute_sql("CREATE INDEX IF NOT EXISTS idxbz_item_id ON bazaar (item_id)")
    execute_sql("CREATE INDEX IF NOT EXISTS idxbz_player_id ON bazaar (player_id)")
    
    res = get_cur(sql='SELECT count(*) FROM logtype').fetchone()
    rowcount = 0
    if res[0] == 0:
        dlog.message(f"Getting logtype from the Torn API.")
        res = get_api(section='torn/logtypes')
        sql = 'INSERT OR IGNORE INTO logtype (logtype_id, title) values (?,?)'
        cur = dbcon.cursor()
        rowcount = 0
        for value in res['logtypes']:
            rowcount += 1
            print_flush(f"{rowcount} {value['title']}")
            cur.execute(sql, ( 
            value['id'], value['title']
            ))
        print()
        dbcon.commit()
    res = get_cur(sql='SELECT count(*) FROM logcategory').fetchone()
    if res[0] == 0:
        dlog.message(f"Getting logcategories from the Torn API.")
        res = get_api(section='torn/logcategories')
        sql = 'INSERT OR IGNORE INTO logcategory (logcategory_id, title) values (?,?)'
        cur = dbcon.cursor()
        rowcount = 0
        for value in res['logcategories']:
            rowcount += 1
            print_flush(f"{rowcount} {value['title']}")
            cur.execute(sql, (
            value['id'], value['title']
            ))
        print()
        dbcon.commit()
    res = get_cur(sql='SELECT count(*) FROM item').fetchone()
    if res[0] == 0:
        dlog.message(f"Getting items from the Torn API.")
        res = get_api(section='torn/items')
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
            print_flush(f"{rowcount} {value['name']}")
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
    res = get_cur(sql='SELECT count(*) FROM company').fetchone()
    if res[0] == 0:
        dlog.message(f"Getting companies from the Torn API.")
        res = get_api(section='torn', selections='companies',version=1)
        sql = 'INSERT OR IGNORE INTO company (company_id, name) values (?,?)'
        cur = dbcon.cursor()
        rowcount = 0
        for key, value in res['companies'].items():
            rowcount += 1
            print_flush(f"{rowcount} {value['name']}")
            cur.execute(sql, (
            key, value['name']
            ))
        print()
        dbcon.commit()
  
def get_cur(sql, args=None):
    cur = dbcon.cursor()
    dlog.debug(f"get_cur {sql} {args}")
    if args:
        return(cur.execute(sql, args))
    else:    
        return(cur.execute(sql))

def get_cur_list(sql):
    cur = dbcon.cursor()
    #cur.row_factory = lambda cursor, row: {field: row[0]}
    #cur.row_factory = sqlite3.Row
    cur.row_factory = lambda cursor, row: row[0]
    return(cur.execute(sql).fetchall())

def execute_sql(sql, args=None, many=False):
    #dlog.debug(f"Executing {sql} {args} {many}")
    #print(args)
    dlog.debug(f"Executing {sql} argcount={len(args) if args is not None else None} {many}")
    if args is None:
        dbcon.execute(sql)
    elif many:
        dbcon.executemany(sql, args)
    else:
        dbcon.execute(sql, args)
    dbcon.commit()

def writelogtodb(thelog, ts_stop = None):
        fieldnames = get_cur_list(sql="SELECT name FROM PRAGMA_TABLE_INFO('userlog')")
        sql1 = 'INSERT OR IGNORE INTO userlog (log_id, log_type, title, timestamp, torndatetime, data, params'
        sql2 = ' values (?,?,?,?,?,?,?'
        cur = dbcon.cursor()
        rowcount = 0
        ts_lastread = None
        for key, value in thelog['log'].items():
            plog = playerlog(value)
            profile = playerprofile(plog.get_playerid())
            rowcount += 1
            print_flush(f"{rowcount} {timestamptodate(value['timestamp'])} {value['title']}")
            sql3 = sql1
            sql4 = sql2
            theparams = [key, 
                value['log'], value['title'],
                value['timestamp'], timestamptodate(value['timestamp']), 
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
            #dlog.debug(f"writing to db {sql3} {theparams}")
            #print(f"{rowcount} {timestamptodate(value['timestamp'])} {value['title']} ")
            ts_lastread = value['timestamp']
            if ts_lastread <= ts_stop:
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
    res = get_cur(sql='SELECT MAX(timestamp) as max_timestamp, MIN(timestamp) as min_timestamp, count(*) FROM userlog').fetchone()
    max_timestamp = res[0]
    min_timestamp = res[1]
    ts_stop = max_timestamp
    ts_lastread = None
    logrowcount = res[2]
    maxcount=5
    itercount = 0
    
    if not args.nolog:
        if max_timestamp is None:
            print('No downloaded userlog. Getting latest log')    
            writelogtodb( get_log() )
            res = get_cur(sql='SELECT MAX(timestamp) as max_timestamp, MIN(timestamp) as min_timestamp, count(*) FROM userlog').fetchone()
            max_timestamp = res[0]
            min_timestamp = res[1]
            logrowcount = res[2]
            print()
            print(f'Latest log entry {max_timestamp} {timestamptodate(max_timestamp)}')
            print(f'Earliest log entry {min_timestamp} {timestamptodate(min_timestamp)}')
            print(f'Total log rows {logrowcount} ')
        else:
            print("A log exists in the local database")
            print(f'Latest log entry {max_timestamp} {timestamptodate(max_timestamp)}')
            print(f'Earliest log entry {min_timestamp} {timestamptodate(min_timestamp)}')
            print(f'Total log rows {logrowcount} ')
            reslogcount = 0
            reslog = get_api(section='user',selections='log', )
            while reslog['log']:
                reslogcount += 1
                dlog.message(f"{reslogcount} Getting next log batch from {max_timestamp} ({timestamptodate(max_timestamp + 1)})")
                status, ts_lastread = writelogtodb( reslog , ts_stop = max_timestamp )
                dlog.debug(f"{status} {ts_lastread} {timestamptodate(ts_lastread)}")
                if status == 'HALT':
                    dlog.message(f"Got to the existing entry, therefore halting {min_timestamp} {timestamptodate(min_timestamp)}")
                    break
                reslog = get_api(section='user',selections='log', ts_to=str(ts_lastread - 1))
                if reslogcount > 50:
                    print('Halting due to >50 break ...')
                    sys.exit()
            res = get_cur(sql='SELECT MAX(timestamp) as max_timestamp, MIN(timestamp) as min_timestamp, count(*) FROM userlog').fetchone()
            max_timestamp = res[0]
            min_timestamp = res[1]
            logrowcount = res[2]
            print(f"DONE The latest timestamp is {max_timestamp} ({timestamptodate(max_timestamp)}, the numer of rows is {logrowcount})")
    
    if args.dryrun:
        thelog =  get_log() 
        fieldnames = get_cur_list(sql="SELECT name FROM PRAGMA_TABLE_INFO('userlog')")
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
            #print_flush(f"{rowcount} {timestamptodate(value['timestamp'])} {value['title']}")
            print(f"{rowcount} {timestamptodate(value['timestamp'])} {value['title']}")
            sql3 = sql1
            sql4 = sql2
            theparams = [key, 
                value['log'], value['title'],
                value['timestamp'], timestamptodate(value['timestamp']), 
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

    if args.getmarketprices or args.getmarketfile:
        #python3 readlog.py --getmarketprices
        summary = []
        #for itemtotrack in secrets['itemstotrack']:
        items = []
        if args.getmarketfile:
            with open(args.getmarketfile) as fin:
                items = fin.read().splitlines()
        else:
            items = secrets['itemstotrack']
        print(f"Getting prices for market and bazaar for {items}")
        
        top3items = []
        for itemtotrack in items:
            #res = get_cur(sql="SELECT item_id, name, sell_price FROM item WHERE item_id in (?)",args= (secrets['itemstotrack'],))
#            res = get_cur(sql="SELECT item_id, name, sell_price FROM item WHERE item_id in (" + str(itemtotrack) +")")
            ncount = 4
            marketitems = []
            #thestockitem = stockitem(item_id=row[0], name=row[1],sell_price=row[2])
            thestockitem = stockitem(item_id = itemtotrack)
            thestockitem.get_attrib_fromdb()
            print(f"Getting details for {thestockitem.name} {thestockitem.item_id}")
            #itm = item(item_id=row[0])
            mkt = marketplace()
            mkt.getitemlisting(itemtotrack)
            n = 0
            for item in mkt.listing:
                if n >= ncount:
                    break
                themarketitem = marketitem(stockitem=thestockitem, market_price=item['price'], market_amount=item['amount'])
                top3items.append(f"{thestockitem.name} sell_price={thestockitem.get_sell_price():,}")
                if themarketitem.is_profit():
                    if n==0 :
                        print(f"{thestockitem.name} sell_price={thestockitem.get_sell_price():,}")
                        summary.append(f"{thestockitem.name}, sell_price={thestockitem.get_sell_price():,} Profit={themarketitem.get_profit():,} market_amount={themarketitem.market_amount:,}")
                    print(f"\tProfit={themarketitem.get_profit():,} market_amount={themarketitem.market_amount:,}")
                    n += 1
                else:
                    print(f"{thestockitem.name} {themarketitem.market_price:,} {thestockitem.sell_price:} x {themarketitem.market_amount }")
                    if n == 0:
                        print(f"{thestockitem.name} sell_price={thestockitem.get_sell_price():,} market_price={themarketitem.get_market_price():,} No items to buy")
                    break
        for line in top3items:
            print(line)
        print("--------------------------------")
        if summary:
            for line in summary:
                print(line)
        else:
            print(f"Nothing to buy")
        #python3 readlog.py --getmarketprices --nolog --itemstotrack 419,45,197,206
        
        if False:
            print(f"Bazaar")
            for itemtotrack in items:
                res = get_cur('SELECT player_id, name , price, quantity FROM bazaar WHERE item_id = ? ORDER BY price', args=( itemtotrack,))
                thestockitem = stockitem(item_id = itemtotrack)
                thestockitem.get_attrib_fromdb()
                for row in res:
                    print(f"{row[0]} {row[1]} {row[2]} x {row[3]} ")
            print("Done Bazaar")

                    #item_id=row[0], name=row[1],sell_price=row[2], market_price=item['price'])
                    #print(f"Price: {item['price']}, Amount: {item['amount']}, ")
                    
    if args.getplayerbyid:
        if args.getplayerbyid == 'me':
            pp = playerprofile('me')
            print(pp.getattrib('lastactionstatus'), pp.getattrib('lastactionrelative'),  timestamptodate(pp.getattrib('lastactiontimestamp')), 
            pp.getattrib('otheractivitytime') 
            )
            seconds = pp.getattrib('otheractivitytime')
            #d = seconds // 60 * 60 * 24
            #h = (seconds-d*60*60 * 24)// (60 * 60)
            #m = (seconds-h*60*60)//60
            #s = seconds-(h*60*60)-(m*60)

            #print(f"{seconds}: {d}D { h }H {m}M {s}S ")

            print(f"""Player {pp.getattrib('name')}, level {pp.getattrib('level')}, age {pp.getattrib('age')} {pp.getattrib('statusdescription')} 
            Attacks {pp.getattrib('attackingattackswon')}, Drugs {pp.getattrib('drugstotal')}, Xan {pp.getattrib('drugsxanax')}""")

        else:
            playerselection = (args.getplayerbyid + ',,').split(',')
            pp = playerprofile(playerselection[0])
            if not pp.profile_isrecent():
                pp.getapi_playerprofile()
            print(f"""Player {pp.getattrib('name')}, level {pp.getattrib('level')}, age {pp.getattrib('age')} {pp.getattrib('statusdescription')} 
            Attacks {pp.getattrib('attackingattackswon')}, Drugs {pp.getattrib('drugstotal')}, Xan {pp.getattrib('drugsxanax')}""")

    if args.getfaction:
        f = faction(faction_id=args.getfaction)
        f.get_faction_members()
        f.print_faction_members()

    if args.getbazaar or args.getbazaarfile:
        #python3 readlog.py --getbazaarfile marketsellers.txt
        #python3 readlog.py --getbazaarfile ecstacyprofiles.txt
        playerids = []
        if args.getbazaarfile:
            with open(args.getbazaarfile) as fin:
                playeridsfile = fin.read().splitlines()
            for pid in playeridsfile:
                if pid.startswith('#'):
                    continue
                pid = pid.split('#')[0].strip()
                if not pid:
                    continue
                if pid in playerids:
                    continue
                else:
                    playerids.append(pid)
        else:
            playerids = (args.getbazaar,)
        n = 0
        for pid in playerids:
            n+=1
            timediff = (datetime.now() - timestart).total_seconds() / 60
            #
            pp = playerprofile(playerid=pid)
            if not pp.exists_db():
                pp.getapi_playerprofile()
            #print(f"{n}/{len(playerids) }Processing player {pid} {pp.name}")
            f = bazaar(player_id=pid) 
            if f.get_bazaar_age() is not None and f.get_bazaar_age() < ( 30 if args.dbage is None else float( args.dbage)):
                print(f"{n}/{len(playerids)} Skipping player {pp.name} {pid} because the bazaar is <{'30' if args.dbage is None else args.dbage} mins old it is {f.get_bazaar_age() }")
                continue
            f.delete_bazaar_items()
            f.get_bazaar_items()
            f.update_db()
            bitems = {}
            print(f"{n}/{len(playerids)} {pp.name} {pid} Total bazaar items = {len(f.items_list)} Api called {apicount} times, approximately {apicount / timediff} per min.")
            #for i in f.items_list:
            #    print(f"{i.name} Price={i.price} Sell={i.sell_price} profit={i.get_profit()}" )
            #    if i.get_profit() is not None and i.get_profit()>=0 and i.price >1:
            #        print(f"{i.name} ispr") 
            #        bitems[i.name] = f"Price={i.price} Sell={i.sell_price} profit={i.get_profit()}" 
            for key,value in bitems.items():
                print(f"{key} {value}" )
        sql = "UPDATE bazaar SET sell_price = i.sell_price FROM (select item_id, sell_price FROM item) as i where i.item_id = bazaar.item_id"
        execute_sql(sql)

        sql = """SELECT i.player_id , p.name as player_name, i.name as item_name ,i. price,( i.sell_price - i.price) as profit 
        FROM bazaar i INNER JOIN playerprofile p on i.player_id = p.playerid
        WHERE (i.sell_price - i.price) > 1000 and i.price > 1
        """
        res = get_cur(sql)
        print(f"Bazaar items that can be sold at a profit")
        for row in res:
            print (f"{row[0]}/{row[1]} {row[2]} {row[4]}")
        items = []
        if args.getmarketfile:
            with open(args.getmarketfile) as fin:
                items = fin.read().splitlines()
        else:
            items = secrets['itemstotrack']
        for itemtotrack in items:
            res = get_cur('SELECT player_id, name , price, quantity FROM bazaar WHERE item_id = ? ORDER BY price', args=( itemtotrack,)).fetchone()
            thestockitem = stockitem(item_id = itemtotrack)
            thestockitem.get_attrib_fromdb()
            for row in res:
                print(f"{res[0]} {res[1]} {res[2]} x {res[3]} ")
        print("Done Bazaar")

    if args.readtextfiles:
        #python3 readlog.py --readtextfiles --outfile warmembers.txt
        readtextfile()

    if args.dbtocsv:
        if args.dbtocsv == 'bazaar':
            print("bazaar")
            sql = "SELECT player_id, updateon, item_id, name, type, quantity, price, market_price, sell_price FROM bazaar ORDER BY player_id, item_id"
            sql = "select player_id, item_id, name, sell_price, price, sell_price - price as profit FROM bazaar WHERE price > 1 AND (sell_price - price) > 10 order by sell_price - price;"
            res = get_cur (sql)
            fields = [col[0] for col in res.description]
        else:
            print("nothing to do")
               
        if res:
            if args.outfile:
                with open(args.outfile, 'w', newline='') as cf:
                    writer = csv.writer(cf)
                    writer.writerow(fields)
                    for row in res:
                        writer.writerow(row)

    timediff = (datetime.now() - timestart).total_seconds() / 60
    print(f"Complete. Api called {apicount} times. Started {timestart} duration {timediff} minutes. Approximately {apicount / timediff} API per minute.")

def flattenjson():
    jsonfields = []
    n=0
    for key, values in thelog['log'].items():
        n+=1
        print(f"{n} {key}")
        for key in flatten_json(values).keys():
            if not key in jsonfields:
                jsonfields.append(key)
    print(f"The keys are {jsonfields}")


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
            res = get_cur(sql='SELECT (julianday(current_timestamp) -julianday(profileupdateon)) * 24 * 60 , name FROM playerprofile WHERE playerid=?',args=(self.playerid ,)).fetchone()
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
        self.personalstatsjson = get_api(section='user',selections='personalstats')
    def get_personalstats(self):
        # https://api.torn.com/v2/user/1326025/personalstats?cat=popular&stat=
        dlog.message(f'Getting personal stats for {self.playerid} from API')
        self.personalstatsjson = get_api(section='user',urlbreadcrumb='personalstats', slug=str(self.playerid), cat='popular')['personalstats']
        self.personalstatsjson = flatten_json(self.personalstatsjson,cleankey=True, delimiter='')
        dlog.debug(f'Player personalstats json {self.personalstatsjson}')
        self.update_db()
    def get_profile_me(self):
        # 'https://api.torn.com/v2/user?selections=profile' -- my profile
        dlog.message('Getting my profile from API')
        self.profilejson = get_api(section='user',selections='profile')
        self.profilejson = flatten_json(self.profilejson,cleankey=True, delimiter='')
        
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
        self.profilejson = get_api(section='user',selections='profile', id=str(self.playerid))
        self.profilejson = flatten_json(self.profilejson,cleankey=True, delimiter='')
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
            self.fieldnames = get_cur_list(sql="SELECT name FROM PRAGMA_TABLE_INFO('playerprofile')")
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
        self.timestamp_iso = timestamptodate(self.timestamp)
        self.data = values['data']
        self.params = values['params']
        self.items = None
        if self.data.get('items', None):
            self.items = flatten_json(self.data['items'],cleankey=True, delimiter='', name='i')
    
        
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

class marketplace:
    listing = []
    def __init__(self,**kwargs):
    # call the super by using super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
    def getitemlisting(self, itemid):
        # https://api.torn.com/v2/market/175/itemmarket
        res = get_api(section='market', slug=str(itemid),urlbreadcrumb='itemmarket' )
        self.listing = res['itemmarket']['listings']
        dlog.debug(f"Market listing {self.listing}")

class stockitem:
    item_id = None
    name = None
    sell_price = 0
    buy_price = None
    market_price = None 
    monitorprice = None
    label = None
    updated_on = None
    def __init__(self,**kwargs):
    # call the super by using super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
    def get_sell_price(self):
        if self.sell_price is None:
            return 0
        else:
            return self.sell_price
    def get_attrib_fromdb(self):
        res = get_cur('SELECT updated_on, name, buy_price, sell_price, market_price, monitorprice, label FROM item WHERE item_id = ?', (self.item_id,)).fetchone()
        self.updated_on = res[0]
        self.name = res[1]
        self.buy_price = res[2]
        self.sell_price = res[3]
        self.market_price = res[4]
        self.monitorprice = res[5]
        self.label = res[6]
        return res
class marketitem(stockitem):
    stockitem = None
    market_price = 0
    market_amount = None
    profit = None 
    def __init__(self,**kwargs):
        #super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
    def get_profit(self):
        return self.stockitem.get_sell_price() - self.get_market_price()
    def is_profit(self):
        return self.get_profit() >= 0
    def get_market_price(self):
        if self.market_price is None:
            return 0
        else:
            return self.market_price


class faction:
    faction_id = None
    faction_name = None
    members_json = None
    members_list = []
    def __init__(self,**kwargs):
        #super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
    def get_faction_members(self):
        # https://api.torn.com/v2/faction/25335/members
        self.members_json = get_api(section='faction', slug=str(self.faction_id), urlbreadcrumb='members')['members']
        for member in self.members_json:
            fm = factionmember()
            fm.attribfromjson(member)
            self.members_list.append(fm)
    def print_faction_members(self):
        for member in self.members_list:
            print(f"{member.name}:{member.level} Life={member.life_current}/{member.life_maximum}" )

class factionmember:
    member_id = None
    name = None
    level = None
    action = None
    action_timestamp = None
    action_relative = None
    status_state = None
    life_current = None
    life_maximum = None
    revive_setting = None
    def __init__(self,**kwargs):
        #super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
    def attribfromjson(self,ajson):
        self.member_id = ajson.get('id','')
        self.name = ajson.get('name','')
        self.level = ajson.get('level','')
        self.action = ajson['last_action']['status']
        self.action_timestamp = ajson['last_action']['timestamp']
        self.action_relative = ajson['last_action']['relative']
        self.status_state = ajson['status']['state']
        self.life_current = ajson['life']['current']
        self.life_maximum = ajson['life']['maximum']

class bazaar:
    # https://api.torn.com/v2/user?selections=bazaar&id=1526458
    player_id = None
    items_json = None
    items_list = []
    bazaar_age = None
    def __init__(self,**kwargs):
        #super().__init__(**kwargs)
        self.items_list = []
        for k,v in kwargs.items():
            setattr(self,k,v)
        
    def get_bazaar_items(self):

        resp=None
        try:
            resp=  get_api(section='user', selections='bazaar', id=str(self.player_id))
            self.items_json = resp['bazaar']

        except Exception as e:
            print(f"!! ERROR getting bazaar_items for {self.player_id} {e} json={self.items_json} response={resp} !!")
            sys.exit()
        if not self.items_json:
            return None
        for bitem in self.items_json:
            bi = bazaaritem()
            bi.attribfromjson(bitem)
            # remove for perf
            #self.get_sell_price()
            self.items_list.append(bi)
    def delete_bazaar_items(self):
        execute_sql("DELETE FROM bazaar WHERE player_id = ?", (self.player_id, ))
    def get_bazaar_age(self):
        if self.bazaar_age is None:
            dlog.debug(f"Getting age of bazaar for {self.player_id}")
            res = get_cur(sql='SELECT (julianday(current_timestamp) - min(julianday(updateon))) * 24 * 60  FROM bazaar WHERE player_id=?',
                args=(self.player_id ,)).fetchone()
            if res is not None: 
                self.bazaar_age = res[0]
        return self.bazaar_age
    def update_db(self):
        # this is why ORMs like Alchemy or Django exist
        timestampnow_iso = datetime.now().isoformat()
        sql = "INSERT INTO bazaar (player_id, updateon,"
        sql_p = '?,?,'
        params = [self.player_id, timestampnow_iso,]
        for fi in ('item_id', 'name', 'type', 'quantity', 'price', 'market_price', 'sell_price'):
            sql += f"{fi},"
            sql_p += '?,'
        sql = sql[:-1]
        sql_p = sql_p[:-1]
        sql += ") VALUES (" + sql_p + ")"

        paramslist = []
        for bi in self.items_list:
            params = [self.player_id, timestampnow_iso,]
            for fi in ('item_id', 'name', 'type', 'quantity', 'price', 'market_price', 'sell_price'):
                params.append(getattr(bi,fi, None))
            paramslist.append(params)
        dlog.debug(f"Attempting to update bazaar for player id {self.player_id} {sql} ")
        execute_sql(sql, args=paramslist,many=True )
    

class bazaaritem:
    item_id = None
    name = None
    type= None
    quantity = None
    price = None
    market_price = None
    sell_price = None
    def __init__(self,**kwargs):
        #super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
    def attribfromjson(self,ajson):
        self.item_id = ajson.get('ID','')
        self.name = ajson.get('name','')
        self.type = ajson.get('type','')
        self.quantity = ajson.get('quantity','')
        self.price = ajson.get('price','')
        self.market_price = ajson.get('market_price','')
        
    def get_sell_price(self):
        if self.sell_price is None:
            res = get_cur(sql='SELECT sell_price FROM item WHERE item_id = ?', args=(self.item_id,)).fetchone()
            self.sell_price = res[0]
        return self.sell_price
    def get_profit(self):
        if self.price is not None and self.sell_price is not None:
            return self.sell_price - self.price
        else:
            return None

if __name__ == '__main__':
    main()





