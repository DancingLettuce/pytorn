import argparse
import sys
import json
from pathlib import Path
import requests #sudo apt-get install python3-requests
from datetime import datetime
import sqlite3
 
# v 09




parser = argparse.ArgumentParser()
parser.add_argument("-api", "--apikey", help="Api key. Stored after first use")
parser.add_argument("--reloadreference", action="store_true",  help="Reload and rebuild the reference tables Item, Logtype, LogCategory.")
parser.add_argument("--truncateplayerprofile", action="store_true",  help="Delete and re-create the playerprofile table.")
parser.add_argument("--itemstotrack", help="Comma separated item IDs to track. Stored after first use.")
parser.add_argument("--nolog", action="store_true",  help="Skip checking the log and downloading")
parser.add_argument("--getmarketprices", action="store_true",  help="Get the prices for the itemstotrack")
parser.add_argument("--getplayerbyid",  help="Get the details for a specific playerid.  Comma delimit extra text to store in playerprofile.playerlastinteraction")
parser.add_argument("--debug", action="store_true",  help="Show detailed tracing log")
parser.add_argument("--debugsql", action="store_true",  help="Show SQLite execution")
parser.add_argument("--reloadcompany", action="store_true",  help="reload company details")
parser.add_argument("--getfaction",   help="Get faction members")

args = parser.parse_args()
secrets = {}
apiurl = 'https://api.torn.com/v2/'
dbcon = sqlite3.connect('pytorn.db')

####################
## some useful defaults
default_itemstotrack = None
default_itemstotrack = """419
    1350
 """
default_itemstotrack = list(map(int, default_itemstotrack.split() ))
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

def get_api(section, selections='', cat='', ts_to='', ts_from='', id='', slug='', urlbreadcrumb=''):
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
    dlog.debug(f"Calling api {apiendpoint}")
    headers = {'Authorization':'ApiKey '+ secrets['apikey']}
    response = requests.get(apiendpoint, headers = headers)
    meme = response.json()
    return meme
    
def get_api_v1(section='',selections=''):
    apiurl_v1 = 'https://api.torn.com/'
    apiendpoint = (apiurl_v1 + section + '/?' + 
        (('&selections=' + selections ) if selections else '') + 
        ('&key=' + secrets['apikey'] )  
        )
    dlog.debug(f"Calling api_v1 {apiendpoint}")
    response = requests.get(apiendpoint)
    meme = response.json()
    return meme
def flatten_json(y,cleankey=False, delimiter = '.'):
    out = {}
    def flatten(x, name=''):
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
    # sqlite viewer online with export-to-csv https://inloop.github.io/sqlite-viewer/
    # sqlite viewer with refresh https://sqliteviewer.app/#/pytorn.db/table/userlog/
    # json viewer https://jsonformatter.org/

    if args.truncateplayerprofile:
        dbcon.execute("DROP TABLE playerprofile")
    if args.reloadreference:
        dbcon.execute("DROP TABLE IF EXISTS item")
        dbcon.execute("DROP TABLE IF EXISTS logtype")
        dbcon.execute("DROP TABLE IF EXISTS logcategory")
        dbcon.execute("DROP TABLE IF EXISTS company")
    if args.reloadcompany:
        dbcon.execute("DROP TABLE IF EXISTS company")
    
    #dbcon.execute("DROP TABLE userlog")
    dbcon.execute("""CREATE TABLE IF NOT EXISTS userlog (id INTEGER PRIMARY KEY, log_id TEXT UNIQUE, log_type TEXT, title TEXT, 
        timestamp INTEGER, torndatetime TEXT,
        data TEXT, params TEXT )""")
    dbcon.execute("""CREATE TABLE IF NOT EXISTS logtype (id INTEGER PRIMARY KEY, logtype_id INTEGER UNIQUE, title TEXT )""")
    dbcon.execute("""CREATE TABLE IF NOT EXISTS logcategory (id INTEGER PRIMARY KEY, logcategory_id INTEGER UNIQUE, title TEXT )""")
    dbcon.execute("""CREATE TABLE IF NOT EXISTS company (id INTEGER PRIMARY KEY, company_id INTEGER UNIQUE, name TEXT )""")
    dbcon.execute("""CREATE TABLE IF NOT EXISTS item (id INTEGER PRIMARY KEY, updated_on TEXT, 
        item_id INTEGER UNIQUE, name TEXT ,
        description TEXT, effect TEXT, requirement TEXT, type TEXT ,
        sub_type TEXT, is_masked TEXT, is_tradable TEXT, 
        is_found_in_city TEXT, vendor_country TEXT, vendor_name TEXT, 
        buy_price INTEGER, sell_price INTEGER, market_price INTEGER,
        circulation INTEGER, category TEXT, stealth_level INTEGER )""")
    dbcon.execute("""CREATE TABLE IF NOT EXISTS playerprofile (id INTEGER PRIMARY KEY, 
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
        res = get_api_v1(section='torn', selections='companies')
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

def writelogtodb(thelog):
        fieldnames = get_cur_list(sql="SELECT name FROM PRAGMA_TABLE_INFO('userlog')")
        sql1 = 'INSERT OR IGNORE INTO userlog (log_id, log_type, title, timestamp, torndatetime, data, params'
        sql2 = ' values (?,?,?,?,?,?,?'
        cur = dbcon.cursor()
        rowcount = 0
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
            for datakey, datavalue in value['data'].items():
                datakey += '_'
                if type(datavalue) is list:
                    datavalue =  str(datavalue)
                sql3 += ',' + datakey
                sql4 += ',?'
                theparams.append(datavalue)
                if datakey not in fieldnames:
                    dbcon.execute('ALTER TABLE userlog ADD ' + datakey + ' TEXT')
                    fieldnames.append(datakey)
            sql3 += ') ' + sql4 + ')'
            cur.execute(sql3, theparams)
        dbcon.commit()

def main():
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
    logrowcount = res[2]
    maxcount=5
    itercount = 0
    
    if not args.nolog:
        if max_timestamp is None:
            print('No downloaded userlog. Getting lastest log')    
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
            reslog = get_api(section='user',selections='log', ts_from=str(max_timestamp +1))
            while reslog['log']:
                reslogcount += 1
                print(f"{reslogcount} Getting next log batch from {max_timestamp} ({timestamptodate(max_timestamp + 1)})")
                writelogtodb( reslog )
                res = get_cur(sql='SELECT MAX(timestamp) as max_timestamp, MIN(timestamp) as min_timestamp, count(*) FROM userlog').fetchone()
                max_timestamp = res[0]
                min_timestamp = res[1]
                logrowcount = res[2]
                print(f"The latest timestamp is {max_timestamp} ({timestamptodate(max_timestamp)}, the numer of rows is {logrowcount})")
                reslog = get_api(section='user',selections='log', ts_from=str(max_timestamp + 1))
                if reslogcount > 10:
                    print('Halting...')
                    sys.exit()
    
    if args.getmarketprices:
        summary = []
        for itemtotrack in secrets['itemstotrack']:
            #res = get_cur(sql="SELECT item_id, name, sell_price FROM item WHERE item_id in (?)",args= (secrets['itemstotrack'],))
            res = get_cur(sql="SELECT item_id, name, sell_price FROM item WHERE item_id in (" + str(itemtotrack) +")")
            ncount = 4
            marketitems = []
            for row in res:
                thestockitem = stockitem(item_id=row[0], name=row[1],sell_price=row[2])
                #itm = item(item_id=row[0])
                mkt = marketplace()
                mkt.getitemlisting(row[0])
                n = 0
                for item in mkt.listing:
                    if n >= ncount:
                        break
                    
                    themarketitem = marketitem(stockitem=thestockitem, market_price=item['price'], market_amount=item['amount'])
                    if themarketitem.is_profit():
                        if n==0 :
                            print(f"{thestockitem.name} sell_price={thestockitem.get_sell_price():,}")
                            summary.append(f"{thestockitem.name}, sell_price={thestockitem.get_sell_price():,} Profit={themarketitem.get_profit():,} market_amount={themarketitem.market_amount:,}")
                        print(f"\tProfit={themarketitem.get_profit():,} market_amount={themarketitem.market_amount:,}")
                        n += 1
                    else:
                        if n == 0:
                            print(f"{thestockitem.name} sell_price={thestockitem.get_sell_price():,} market_price={themarketitem.get_market_price():,} No items to buy")
                        break
        print("--------------------------------")
        if summary:
            for line in summary:
                print(line)
        else:
            print(f"Nothing to buy")

                    #item_id=row[0], name=row[1],sell_price=row[2], market_price=item['price'])
                    #print(f"Price: {item['price']}, Amount: {item['amount']}, ")
                    
    if args.getplayerbyid:
        if args.getplayerbyid == 'me':
            pp = playerprofile('me',forceapi=True)
            print(f"""Player {pp.getattrib('name')}, level {pp.getattrib('level')}, age {pp.getattrib('age')} {pp.getattrib('statusdescription')} 
            Attacks {pp.getattrib('attackingattackswon')}, Drugs {pp.getattrib('drugstotal')}, Xan {pp.getattrib('drugsxanax')}""")

        else:
            playerselection = (args.getplayerbyid + ',,').split(',')
            pp = playerprofile(playerselection[0],forceapi=True)
            print(f"""Player {pp.getattrib('name')}, level {pp.getattrib('level')}, age {pp.getattrib('age')} {pp.getattrib('statusdescription')} 
            Attacks {pp.getattrib('attackingattackswon')}, Drugs {pp.getattrib('drugstotal')}, Xan {pp.getattrib('drugsxanax')}""")

    if args.getfaction:
        f = faction(faction_id=args.getfaction)
        f.get_faction_members()
        f.print_faction_members()
        pass


    print("Complete.")

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
    forceapi = False
    personalstatsjson = None
    def __init__(self, playerid = None, forceapi=False):
        self.forceapi = forceapi
        if playerid == 'me':
            self.get_profile_me()
            self.get_personalstats()
        elif playerid is not None:
            self.playerid = playerid
            if not self.exists_db():
                self.insertplayerid()
            if not self.profile_isrecent():
                self.getapi_playerprofile()
    def getattrib(self, value):
        if self.profilejson.get(value,''):
            return self.profilejson.get(value,'')
        else:
            return self.personalstatsjson.get(value,'')
        return ''
    def exists_db(self):
        if self.existsdb is None:
            debuglog(self.playerid)
            res = get_cur(sql='SELECT (julianday(current_timestamp) -julianday(profileupdateon)) * 24 * 60  FROM playerprofile WHERE playerid=?',args=(self.playerid ,)).fetchone()
            if res is not None:
                self.existsdb = True
                self.profile_age = res[0]
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
        self.update_playerprofile()
    def get_profile_me(self):
        # 'https://api.torn.com/v2/user?selections=profile' -- my profile
        dlog.message('Getting my profile from API')
        self.profilejson = get_api(section='user',selections='profile')
        self.profilejson = flatten_json(self.profilejson,cleankey=True, delimiter='')
        
        dlog.debug(f'my profile json {self.profilejson}')
        self.playerid = self.getattrib('playerid')
        dlog.debug(f"My playerid = {self.playerid}")
        self.insertplayerid()
        self.update_playerprofile()
    def get_profile_age(self):
        self.exists_db()
        return self.profile_age
    def profile_isrecent(self):
        if self.forceapi:
            return False
        if self.profile_age is None:
            return False
        elif self.profile_age < 30:
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
        self.update_playerprofile()
    def update_playerprofile(self):
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
    def __init__(self, values):
        self.log_type = values['log']
        self.title = values['title']
        self.timestamp = values['timestamp']
        self.timestamp_iso = timestamptodate(self.timestamp)
        self.data = values['data']
        self.params = values['params']
    def get_playerid(self):
        if self.log_type == 1225: # bazaar buy
            return self.data['seller']
        elif self.log_type == 8156: # bazaar buy
            return self.data['attacker']
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

    def __init__(self,**kwargs):
    # call the super by using super().__init__(**kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
    def get_sell_price(self):
        if self.sell_price is None:
            return 0
        else:
            return self.sell_price
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


if __name__ == '__main__':
    main()





