#!/bin/env python

"""This module is to extend the functionality of import_log.py for non standard log rotation and other specific customizations"""


"""This is the todo list for log_loader.py

Featuree To Do list
---------------------
* Can classes be used throughout?
* How to extend import_logs.py using classes?
* Configuration structure
	* General
		* email settings
	* profile
		* include paths by list
		* include paths by file
* SQLITE DB
    * After check for DB, check for tables, if missing tables, re-create
    * Track Errors
    * Track logs
    * Other Stats
    * Remove old log references in SKIP Table
	* create readable log files as output or debug
	* remove old log file entries (6 months?)
* add command line options 
	* to point to a config file or record
	* point to a file of config files
	* select one or more profiles
* use 1.12 verison of import_logs.py
* send reports via e-mail
* User Interface
	* web based
	* piwik module
	* Command Line Interface
* track script usage using PIWIK?

Features list:
--------------
* script to setup and install basic config file
* Configuration structure
	* General
		* Piwik location
		* piwik URL
		* import_logs.py location
		* username
		* password
		* API key
    * profile
		* log location
		* piwik profile
		* URL
		* logfile format with dates
		* exclude paths by list
		* exclude paths by file
		* log format by name
		* log format by regex
		* domain names
* Sqlite DB 
	* to track last lines read
    * track total lines
    * auto create new entries for new log files
    * track site ID and profile numbers

"""

import site
import sys
import ConfigParser
import os
import sqlite3
import subprocess

from optparse import OptionParser
from datetime import date

if __name__ == '__main__' and __package__ is None:
    __package__ = "loganalytics.batch"
   
Configuration="1"

year = str(date.today().year)
year2 = str(date.today().year)[2:]
month = str(date.today().month)
# ensure month is two digits
if len(month) == 1:
    month = "0" + month
#day = str(date.today().day)
day = str("02")
# ensure day is two digits
if len(day) == 1:
    day = "0" + day



def main():
    config = getConfig()
    setupDb(config.get("general","batchDbDir"))
    updateDb(config)
    processLogs()

def processLogs():
    """This function will control the processing of the log files"""
    config = getConfig()
    # ./import_logs.py --url=piwik.example.com /path/to/access.log
    cmd = config.get("general", "piwikMisc") + "/loganalytics/logimport/import_logs.py"
    urlBase = config.get("general","piwikUrl")
    conf = config.get("general", "piwikConfig")
    # Repeat for each section in the config file
    for s in config.sections():
        # Test for sections with "profile" in the name"
        if s.find("profile"):
            pass
        else:
            # do something with each section with 'profile' in the name
            # Grab option value pairs and create variables for insertion
            name = config.get(s, "name")
            idsite = config.get(s, "idsite")
            sourceUrl = config.get(s, "sourceUrl")
            logFile = config.get(s, "logFile")
            logFormatRegex =""
            profile = s
            
            # Build a path to grab exclude file from
            # check to see if a path can be built and then exists
            excludePathFrom = config.get("general", "excludeDir") + "/" + s.replace(" ","") + ".exclude"
            if os.path.exists(excludePathFrom):
                pass
            else:
                # if the exclude file does not exist, then use the generic empty profile0 (zero)
                excludePathFrom = config.get("general", "excludeDir") + "/profile0.exclude"
            # print some output
            print("-----")
            print(s)
            print("-----")
            print("Name: " + name)
            print("")
            # some profiles may have multiple log files to process
            # Grab them one at a time and send to buildCmd() function
            for log in logFile.split(","):
                # grad value for lines to skip processing from
                logFile =log.strip().replace("%YYYY",year).replace("%YY", year2).replace("%MM", month).replace("%DD", day)
                # test to see if logFile exists
                if os.path.exists(logFile):
                    print("Logfile: " + logFile)
                    skip = getSkip(s, logFile)
                    lines = countLines(s, logFile)
                    print("Lines skipped:" + str(skip))
                    print("Lines counted:" + str(lines))
                    print("Lines processed: " + str(lines - skip))
                    buildCmd(profile, cmd, urlBase, idsite, logFile, excludePathFrom, skip, conf)
                # pass on this log file if it does not exist. This allows for a clean fail for missing log files
                else:
                    print("Skipped log File: " + logFile)
                    
def buildCmd(profile, cmd, urlBase, idsite, logFile, excludePathFrom, skip, conf):
    config=getConfig()
    """ This function will create a custom URL and submit it to the command line to trigger the log loading script. it will also Build the command line call"""            
    
    logFormatName = config.get(profile, "logformatname")
    logFormatRegex = config.get(profile, "logformatregex")
    #paramToken = "--token-auth=8beb3ef154e073f225bc2607e31d2bf1"
    paramToken = "--token-auth=" + config.get("general", "token")
    paramSkip = "--skip=" + str(skip)
    paramExclude = "--exclude-path-from=" + excludePathFrom
    paramUrl = "--url=" + urlBase
    paramConf = "--config=" + conf
    if logFormatName == "None":
        if logFormatRegex == "None":
            paramLogFormat =""
            print("no log format")
        else:
            paramLogFormat = "--log-format-regex="+config.get(profile, "logformatregex")
            print("log format by regex")
    else:
        paramLogFormat = "--log-format-name="+config.get(profile, "logformatname")
        print("log format by name")
        
    #paramRegex = '--log-format-regex=".* (?P<host>[\w\-\.]*:)(?::\d+)? (?P<ip>\S+) \S+ \S+ \[(?P<date>.*?) (?P<timezone>.*?)\] \S+ (?P<path>.*?) \S+ (?P<status>\S+) (?P<length>\S+) (?P<referrer>\S+) (?P<user_agent>.*)"'
    paramLogHost= "--log-hostname=" + config.get(profile, "loghostname") 
    paramSiteId = "--idsite=" + idsite
    
    
    cmdln = cmd + " " + paramSkip + " " + paramLogHost + " " + paramUrl + " "  + paramConf + " " + paramExclude + " " + paramToken + " " + paramSiteId + " " + paramLogFormat +  " "  + logFile
    
    print("Command: " + cmd)
    print("command line call: " + cmdln)
    # add --dry-run param for testing
    subprocess.call([cmdln], shell=True)
    #subprocess.call([cmd, "-d", paramSkip, paramLogHost, paramUrl, paramConf, paramExclude, paramToken, paramSiteId, paramRegex, logFile])

    
def getSkip(profile, logFile):
    """Get the value of lines to skip"""
    # grab the value of the last line count from the sqlite db
    # Test to see if logfile has more lines than last count
    #get info from config file
    config = getConfig()
    dbDir = config.get("general","batchDbDir")
    idsite = config.get(profile, "idsite")
    db = dbDir + "/piwik.db"
    conn = sqlite3.connect(db)
    c = conn.cursor()
    lf = (str(logFile),)
    c.execute('Select last_line from skip where log_file=?',lf)
    lines = c.fetchone()
    if lines[0] == None:
        skip = 0
        #print("skipping last lines: " + str(skip))
    else:
        skip = lines[0] 
        #print("skipping last lines: " + str(skip))
    conn.close()
    # if logfile has less lines than last skip, then assume new log file
    return skip

def callPiwikAPI(cmd):
    """ This function will create a custom URL and submit it to the command line to trigger the log loading script """
    pass
    
def countLines(profile, logFile):
    """This function will count the number of lines in a log file"""
    #get info from config file
    config = getConfig()
    dbDir = config.get("general","batchDbDir")
    idsite = config.get(profile, "idsite")
    db = dbDir + "/piwik.db"
    # count the lines in a log file
    count = sum(1 for line in open(logFile))
    #prepare row information
    row = (count, logFile)
    lf = (logFile,)
    # write the value to the sqlite DB
    conn = sqlite3.connect(db)
    c = conn.cursor()
    # update 'last_line' with value of tot_lines from the last run
    c.execute("UPDATE skip SET last_line=tot_lines where log_file=?", lf)
    conn.commit()
    c.execute("SELECT last_line from skip where log_file=?", lf)
    lastLine = c.fetchone()
    # Test the value of lastLine. if no value then None and overide, otherwise an integer and set
    if lastLine[0] == None:
        lastLine = 0
    else:
        lastLine = lastLine[0] 
    # update 'tot_lines' with new value
    c.execute("UPDATE skip SET tot_lines=? where log_file=?", row)
    conn.commit()
    # confirm info was written
    c.execute("select tot_lines from skip where log_file=?",lf)
    result = c.fetchone()
    #print("counted lines: " + str(count))
    #print("count result: " + str(result[0]))
    # check to see if the value in DB equals the current value
    if result[0] == count:
        print("countlines db update success")
    else:
        print("countlines db update failed")

    diff = count - lastLine
    #print("new count: " + str(count))
    #print("Lines Processed: " + str(diff))
    conn.close()
    # print the result
    #print(row)
    #print("Profile: " + profile)
    #print("Count Lines for " + logFile + ": " + str(count) )
    return count
    
    
def setupDb(dbDir):
    """This function will setup the sqlite DB used to manage various things like line counts"""
    db = dbDir + "/piwik.db"
    # check to see if it exists
    if os.path.exists(db):
        print("DB Exists. Moving on.")
        pass
    else:
        print("DB Does not exist and will be created")
        # read content from SQL file to created DB
        sqlFile = open(dbDir + "/piwikDbCreate.sql", "r")
        sql = sqlFile.read()
        print(sql)
        conn = sqlite3.connect(db)
        c = conn.cursor()
        for s in sql.split(";"):
            c.execute(s)
        print("Executed SQL")
    
def getLastLine():
	print("Getting Last Line")

def outputLog():
	print("Outputting log")

def getOptions():
	print("Getting Arguments")
	parser = OptionParser()
	parser.add_option('-c','--config', dest="config", help="Name of Configuration file")
	parser.add_option('-p','--profile', dest="profile", help="Profile name to process")
	parser.add_option('-i','--idsite', dest="indsite", help="Piwik idSite profile number")

	(options, args) = parser.parse_args()
	print("Your arguments are: ", args)
	print("your options are: ", options)

"""class Configuration(Configuration):
    "Extends Configuration Class from import_logs"
    def __init__(self):
        pass
"""

def install():
	print("Installing Scrip")

def updateDb(config):
    """Update the sqlite DB with latest information from config"""
    print("updating DB with new config values")
    dbDir = config.get("general","batchDbDir")
    db = dbDir + "/piwik.db"
    for s in config.sections():
        # Test for sections with "profile" in the name"
        if s.find("profile"):
            pass
        else:
            #print(s)
            profile = s       
            idsite = config.get(s,"idsite")
            logList = config.get(s,"logfile")
            #prepare DB
            conn = sqlite3.connect(db)
            c = conn.cursor()
            for log in logList.split(","):
                logFile =log.strip().replace("%YYYY",year).replace("%YY", year2).replace("%MM", month).replace("%DD", day)
                lf = (logFile, )
                #prepare row information
                row = (profile, idsite, logFile)
                #print("log file: " + logFile)
                #print("lf: " + str(lf))
                #print("row: " + str(row))
                # check to see if row exists in DB
                c.execute("select exists (select * from skip where log_file=?)", lf)
                # capture return status of above execute command. if (1,) then exists, otherwise it does not
                rowStat = c.fetchone()
                if rowStat[0] == 1:
                    print("logfile " + logFile + " exists")
                    pass
                else:
                    print("Log File " + logFile + " Does not Exist")
                    # write the value to the sqlite DB if the row does not exist
                    try:
                        print("Trying to enter logfile in DB")
                        c.execute("INSERT INTO skip ('profile','site_id','log_file') VALUES (?,?,?)", row)
                        conn.commit()
                        print("countlines db success")
                    except:
                        print("countlines db failed")
                        pass
            conn.close()
    
    
    
    
def updateLogDb():
    """ Update the sqlite log Database with results"""
    pass

def getConfig():
    """Read the configuration file"""
    config = ConfigParser.ConfigParser()
    config.readfp(open('batch.cfg'))
    return config
    


if __name__=="__main__":
	"""try:
	    config=Configuration()
	    
	except KeyboardInterrupt:
	    pass
	"""
	main() 

	    
