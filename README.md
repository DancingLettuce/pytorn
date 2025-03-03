# pytorn
python+torn

Torn City https://www.torn.com/index.php

Execute with python3 readlog.py

First time execute with python3 readlog.py --apikey myapikey
The apikey is written to secrets.json.  Next time do not need the switches

Userlog
When executed the script builds an SQLite database.  It reads the last 100 log entries and writes them to the userlog table.  The next time the script is run, it works out the most recent log entry and retrieves the next 100 log entries and writes them to the userlog table.  This is repeated until all the log events since the last execution have been downloaded.  The script dynamically creates the fields needed for the ad hoc logs.  The log is generally constructed of a set of static attributes such as log-type, title, ID.  The payload is in the data json which is expanded into columns but also inserted into a TEXT column.  Lists within json are not enumerated.  

Logtype, Logcategory
The helper tables logtype and logcategory are populated which are foreign keys to the userlog table.

Playerprofile
When the script writes the log, it reads the log and creates a playerprofile entry in the playerprofile table.  This records the players interacted with and records the basic profile information such as the name, age, crime and attack data which is also shown in the online profile page of the player.

Item
The item table contains all the items.  It is the foreign key to userlog and features such as Market and Bazaar.


