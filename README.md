# pytorn
python torn

Torn City https://www.torn.com/index.php

Execute with python3 readlog.py

First time execute with python3 readlog.py --apikey myapikey
The apikey is written to secrets.json.  Next time do not need the switches

How Much Profit Have I Made?
-----------------------------

Trading confuses me.  To calculate your profit:
* python3 readlog.py
* This creates the database
* python3 sqlitetohtml.py --sqlprepared trading --outfile trading.csv
* This takes the sqlite database and writes the output of the sql to the csv file
* Open the csv in Spreadsheet
  

Userlog

When executed the script builds an SQLite database.  It reads the last 100 log entries and writes them to the userlog table.  The next time the script is run, it works out the most recent log entry and retrieves the next 100 log entries and writes them to the userlog table.  This is repeated until all the log events since the last execution have been downloaded.  The script dynamically creates the fields needed for the ad hoc logs.  The log is generally constructed of a set of static attributes such as log-type, title, ID.  The payload is in the data json which is expanded into columns but also inserted into a TEXT column.  Lists within json are not enumerated.  

Logtype, Logcategory

The helper tables logtype and logcategory are populated which are foreign keys to the userlog table.

Playerprofile

When the script writes the log, it reads the log and creates a playerprofile entry in the playerprofile table.  This records the players interacted with and records the basic profile information such as the name, age, crime and attack data which is also shown in the online profile page of the player.

Item
The item table contains all the items.  It is the foreign key to userlog and features such as Market and Bazaar.

ReadTextFile
Save web pages in the textfile directory and the script will parse the files for player ID numbers and will write the player ID numbers to a file

Torn Tools and the various Tampermonkey scripts are far more useful. I did not know about them before I started this project.

