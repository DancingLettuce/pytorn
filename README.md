# pytorn
python torn

Torn City https://www.torn.com/index.php

Execute with `python3 readlog.py`

First time you run, execute with `python3 readlog.py --apikey myapikey` providing your private API key.
The apikey is written to secrets.json.  Next time it is run, you do not need to provide the API key.

The script will read your Torn log and will download it into a local SQLite database **pytorn.db** so that you can query it directly with SQL.

`python3 readlog.py`

<img src="https://github.com/user-attachments/assets/a80201bd-cb1f-486d-af60-f61a8957fa98" width="700">


You can open the SQLite database with tools like this [https://sqliteviewer.app/ ](https://sqliteviewer.app/#/pytorn.db/table/userlog/)

How Much Profit Have I Made?
-----------------------------

To analyse trades:
* Download the latest log `python3 readlog.py`
* Export the log to CSV.  The helper script `python3 sqlitetohtml.py --sqlprepared trading --outfile trading.csv` will do this.  You can change the SQL in the prepared SQL statement if you want different columns or if you want to group, calculate maximum etc.
* Open in Google Sheets

<img src="https://github.com/user-attachments/assets/0093b7b8-ee09-40b6-996f-9b26ebb046ec" width="700">


![image](https://github.com/user-attachments/assets/aeef2f37-877c-4fee-b4eb-78f4fe1eee44)
  

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

