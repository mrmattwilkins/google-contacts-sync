# Google Contacts Sync

Sync the contacts of a bunch of google accounts using the People API.

Groups are not synced, just individual contacts.

# Setup

1. [Create a Google Cloud Platform project and enable the people API](https://developers.google.com/workspace/guides/create-project).

2. [Create and download credentials](https://developers.google.com/workspace/guides/create-credentials)

3. Install software

   ```
   pip3 install -r requirements.txt
   ```

4. Run the sync script

   ```
   python sync.py -v
   ```

   it will create a default config file that you will need to edit.  The name
   of the config file will be displayed so you know what to edit (on my system
   it is `~/.local/share/google-contacts-sync/config.ini`).

5. Edit the config file.  You should have a 
   stanza for each of your accounts, this example is for three email addresses:
   myemail@gmail.com, otheremail@gmail.com, and anotheraccount@gmail.com.  It
   will look like this:

   ```
   [DEFAULT]
   last = 2021-07-02T09:44:37.906846+00:00

   [account-myemail]
   user = myemail@gmail.com
   keyfile = /blah/.local/share/google-contacts-sync/myemail_keyfile.json
   credfile = /blah/.local/share/google-contacts-sync/myemail_token

   [account-otheremail]
   user = otheremail@gmail.com
   keyfile = /blah/.local/share/google-contacts-sync/otheremail_keyfile.json
   credfile = /blah/.local/share/google-contacts-sync/otheremail_token

   [account-anotheraccount]
   user = anotheraccount@gmail.com
   keyfile = /blah/.local/share/google-contacts-sync/anotheraccount_keyfile.json
   credfile = /blah/.local/share/google-contacts-sync/anotheraccount_token
   ```

   You don't need to edit the `last`, that gets updated when the script runs.
   The main thing to set up is the `keyfile`s.  These need to point to the
   credentials you downloaded.  The `credfile` is the cached token that the
   script makes.

6. The script needs to store the `credfile` tokens (unless you have them from a
   previous syncer and just copy them in).  Run the script, a
   browser will be opened up for you to login as each of your accounts in turn
   and accept the access.  You will have to click the Advanced link to say you
   really trust this program.

7. Now you are ready to do syncing.  If you have previously used a google
   contacts syncer that uses the `csync-uid` field 
   (such as [Michael Adlers](https://github.com/michael-adler/sync-google-contacts))
   then you are good to go and can just start running the `sync.py`
   periodically.  However if this is the first time doing syncing then you will
   have to initialize things.  This is where contacts a matched up using their
   names.  Just run

   ```
   python sync.py -v --init
   ```

   and let it run.  It will take ages, but will give you updates.  After this
   every contact will have a `csync-uid` field, unique across all your
   accounts.  So you can change peoples names if you want and syncing will just
   work because the `csync-uid` is used to identify people.  If you ever add
   another account you will have to run the --init again.  

