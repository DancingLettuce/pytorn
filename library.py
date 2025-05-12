from datetime import datetime
from pathlib import Path
import json
import requests #sudo apt-get install python3-requests

timestart = None 
apicount = None
secrets = None
dlog = None
args = None
dbcon = None
timestart = None
libraryversion = '1'
def libversion():
    print("library v1")

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

def get_api(section, selections='', cat='', ts_to='', ts_from='', id='', slug='', urlbreadcrumb='', version=2):
    global apicount
    global timestart
    timediff = (datetime.now() - timestart).total_seconds() / 60
    if apicount / timediff >= 90:
        print(f"Pausing for {'5' if args.sleep is None else args.sleep} seconds")
        time.sleep(5 if args.sleep is None else float(args.sleep))
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
        apiendpoint = ('https://api.torn.com/v2/' + section + 
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

def savesecrets():
    secretfile = 'secrets.json'
    with open(secretfile, 'w') as ff:
        json.dump(secrets, ff)

def loadsecrets():
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

def timestamptodate(ts):
    if ts:
        ts=int(ts)
        return datetime.fromtimestamp(ts).isoformat()
    else:
        return None

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
