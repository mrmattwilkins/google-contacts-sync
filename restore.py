import sys
import pickle
from os.path import exists
import pathlib
from turtle import back
import appdirs
from sqlalchemy import null

print('Loading configuration')
if exists("PORTABLE.md"):
    cdir = pathlib.Path(
        "conf"
    )
else:
    cdir = pathlib.Path(
        appdirs.AppDirs('google-contacts-sync', 'mcw').user_data_dir
    )


#TODO: find a way to select the backup to restore
backup_file_path=cdir / 'backups' / '1.bak'
if not exists(backup_file_path):
    print("backup file not found")
    sys.exit(1)
backup=None
with open(backup_file_path, 'rb') as file_reader:
    backup = pickle.load(file_reader)


#TODO:
#consider that the accounts are "empty"? do i have to empty them?
#analyze the contacts and create a list of common ContactGroup
#create the ContactGroup in the accounts and get the new sync tag
#create a common contact list
#for each account, for each contact:
#   retrieve the old group tags
#   "convert" them to the new tag  
#   save it.

#TODO: v2
#analyze all contacts and create a "synchronized" list
#create a CSV file ( to directly create the csv in the sync phase? )
#import the CSV file into an account
#empty other accounts
#re-initialize accounts
