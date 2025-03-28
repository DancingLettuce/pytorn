# sqlite to html templating
# output to csv 
# v1

import argparse
import sys
import json
from pathlib import Path
import pathlib
from datetime import datetime
import sqlite3
import os
import re
import time
import csv

    # sqlite viewer online with export-to-csv https://inloop.github.io/sqlite-viewer/
    # sqlite viewer with refresh https://sqliteviewer.app/#/pytorn.db/table/userlog/
    # json viewer https://jsonformatter.org/

parser = argparse.ArgumentParser()
parser.add_argument("--dbfile", help="Database file name. Stored after first use")
parser.add_argument("--debug", action="store_true",  help="Show detailed tracing log")
parser.add_argument("--debugsql", action="store_true",  help="Show SQLite execution")
parser.add_argument("--sqlexec",  help="Execute ad hoc sql")
parser.add_argument("--sqlprepared",  help="Execute prepared SQL, pass in name")
parser.add_argument("--showprepared", action="store_true",  help="List the prepared statement names")
parser.add_argument("--showsecrets", action="store_true",  help="List the prepared statement names")
parser.add_argument("--outfile",   help="Export output to file")
parser.add_argument("--template",   help="Template to format HTML")
parser.add_argument("--infile",   help="Import from a file")
parser.add_argument("--updatetable",   help="Update table from file")



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

# some quick globals
args = parser.parse_args()
secrets = {}
dbcon = None
timestart = datetime.now()
dlog = debuglog()
SQLPREPARED={'allitems':"SELECT item_id, name, sell_price , label, monitorprice FROM item ORDER BY item_id",
    'allcompany': 'SELECT company_id, name FROM COMPANY ORDER BY company_id',
    '1dsellers':"""SELECT b.player_id, p.name , COUNT(*) as total 
    FROM bazaar b 
    LEFT JOIN playerprofile p ON b.player_id = p.playerid  
    WHERE price =1 GROUP BY b.player_id, p.name order by 3 desc;""",
    'trading':"""SELECT ll.torndatetime, ll.title, i.name, ll.quantity, ll.value, ll.total_value, ll.fee 
            FROM (
            SELECT l.timestamp, l.log_type, l.title, l.torndatetime, l.fee_ as fee, 
            CASE
                WHEN l.log_type in (4201, 4200, 4210) THEN item_
                WHEN l.log_type in (1113, 1226, 1112, 1225) THEN i0id_
                ELSE -999
            END as item_id,
            CASE
                WHEN l.log_type in (4201, 4200, 4210) THEN quantity_
                WHEN l.log_type in (1113, 1226, 1112, 1225) THEN i0qty_
                ELSE -999
            END as quantity,
            CASE
                WHEN l.log_type in (4210) THEN value_each_
                WHEN l.log_type in (1113, 1226, 1112, 1225, 4200, 4201) THEN cost_each_
                ELSE -999
            END as value,
            CASE
                WHEN l.log_type in (4210) THEN total_value_
                WHEN l.log_type in (1113, 1226, 1112, 1225, 4200, 4201) THEN cost_total_
                ELSE -999
            END as total_value
            FROM userlog as l
            WHERE l.log_type in (1113, 4210, 1226, 1112, 1225, 4200, 4201)
            ) AS ll
            LEFT JOIN item i ON ll.item_id = i.item_id
            ORDER BY ll.timestamp DESC
        """}


if args.debugsql:
    # trace calls
    dbcon.set_trace_callback(print)

def savesecrets():
    secretfile = 'secrets.json'
    with open(secretfile, 'w') as ff:
        json.dump(secrets, ff)

def loadsecrets():
    global secrets
    secretfile = 'secrets.json'
    secretfilep = Path(secretfile)
    if secretfilep.is_file():
        try:
            with open(secretfile, 'r') as ff:
                secrets = json.load(ff)
        except Exception as e:
            print(f"ERROR: Cannot load secrets {e}")
            sys.exit()
    return secrets

def get_cur(sql, args=None, rowfactory=None):
    cur = dbcon.cursor()
    if rowfactory:
        cur.row_factory = sqlite3.Row
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


## main
def main():
    
    global secrets
    global dbcon
    loadsecrets()
    if args.dbfile:
        secrets['dbfile'] = args.dbfile
    dbcon = sqlite3.connect(secrets['dbfile'] )
    savesecrets()

    if args.showprepared:
        print(f"The prepared statements are: {SQLPREPARED.keys()}")

    if args.showsecrets:
        #python3 readlog.py --showsecrets
        print(f"Secrets: {secrets}")

    if args.outfile:
        if 'csv' in args.outfile:
            if args.sqlprepared:
                res = get_cur(SQLPREPARED[args.sqlprepared])
                fields = [col[0] for col in res.description]
                print(fields)
                with open(args.outfile, 'w', newline='') as outf:
                    #csvwriter = csv.DictWriter(outf , fieldnames = fields , delimiter = ',')
                    csvwriter = csv.writer(outf , delimiter = ',')
                    csvwriter.writerow(fields)
                    for row in res:
                        csvwriter.writerow(row)
                        print(row)
                print(f"Output written to {args.outfile} as CSV")
        elif 'html' in args.outfile:
            if args.sqlprepared:
                res = get_cur(SQLPREPARED[args.sqlprepared], rowfactory='row')
                fields = [col[0] for col in res.description]
                with open(args.outfile, 'w', newline='') as outf:
                    outf.write('<HTML>\n')
                    outf.write('<OL>\n')
                    for row in res:
                        if args.template == 'playerbazaar':
                            #https://www.torn.com/bazaar.php?userId=2749171#/
                            #https://www.torn.com/profiles.php?XID=2749171
                            #https://torn.bzimor.dev/user_bazaar/2749171
                            st = '<LI>'
                            st += f"<a href='https://www.torn.com/profiles.php?XID={row['player_id']}' target='_blank'>{row['name']}</a>  "
                            st += f"<a href='https://www.torn.com/bazaar.php?userId={row['player_id']}#/' target='_blank'>Bazaar</a> {row['total']} items"
                            st += '</LI>\n'
                            outf.write(st)
                    outf.write('<UL>\n')
                    outf.write('<HTML>\n')
                print(f"Output written to {args.outfile} as HTML")
        else:
            print(f"Outfile {args.outfile} type can not be inferred.")

    if args.updatetable:
        if args.updatetable == 'item':
            sql = 'UPDATE item SET label = ?, monitorprice=? WHERE item_id = ?'
            params=[]
            if 'tsv' in args.infile:
                delimiter = '\t'
            else:
                delimiter = ','
            with open(args.infile, newline='', ) as fin:
                reader = csv.DictReader(fin, delimiter=delimiter)          
                for row in reader:
                    params = (row['label'], row['monitorprice'], row['item_id'])
                    execute_sql(sql, params)
            print(f"Updated {args.updatetable}")
        

        #The only issue with https://torn.bzimor.dev/items/1dollar is that it lists the results by item and I can't see how to just list all the users with one-dollar bazaars.  So I wrote a Python script to extract the names and then put them into a useable format.


    print(f"Complete")

## main
if __name__ == '__main__':
    main()