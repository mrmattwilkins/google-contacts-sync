# Google Contacts Sync

Sync the contacts of a bunch of google accounts using the People API.

No group syncing is done, just individual contacts.

# Setup

1. [Create a Google Cloud Platform project and enable the people API]
(https://developers.google.com/workspace/guides/create-project).

2. [Create and download credentials](https://developers.google.com/workspace/guides/create-credentials)

3. Install software
```
pip3 install -r requirements.txt
```

4. Run the sync script
```
python sync.py
```
   it will create a default config file that you will need to edit.  The name
   of the config file will be displayed so you know what to edit.

5. Edit the config file (on my system it is
   `~/.local/share/google-contacts-sync/config.ini`).  You should have a 
   stanza for each of your accounts, this example is for three email addresses
   myemail@gmail.com, otheremail@gmail.com, and anotheraccount@gmail.com.  It
   will look like this:
```
[DEFAULT]
last = 2021-07-02T09:44:37.906846+00:00

[account-myemail]
user = myemail@gmail.com
keyfile = /home/mwilkins/.local/share/google-contacts-sync/myemail_keyfile.json
credfile = /home/mwilkins/.local/share/google-contacts-sync/myemail_token

[account-otheremail]
user = otheremail@gmail.com
keyfile = /home/mwilkins/.local/share/google-contacts-sync/otheremail_keyfile.json
credfile = /home/mwilkins/.local/share/google-contacts-sync/otheremail_token

[account-anotheraccount]
user = anotheraccount@gmail.com
keyfile = /home/mwilkins/.local/share/google-contacts-sync/anotheraccount_keyfile.json
credfile = /home/mwilkins/.local/share/google-contacts-sync/anotheraccount_token
```
   You don't need to edit the `last`, that gets updated when the script runs.
   The main thing to set up is the keyfiles.  These need to point to the
   credentials you downloaded.  The credfile is the cached token that the
   script makes.

6. Now run the script again


