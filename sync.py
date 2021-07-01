#!/usr/bin/env python3

import sys
import os
import appdirs
import pathlib
import configparser
import argparse
import random
import string
import datetime
import dateutil
import pytz

from contacts import Contacts


all_sync_tags = set([])


def new_tag():
    """Return a new unique sync tag"""
    le = string.ascii_lowercase
    while (t := ''.join(random.choices(le, k=20))) in all_sync_tags:
        pass
    all_sync_tags.add(t)
    return t


def vprint(*a, **vargs):
    if args.verbose:
        print(*a, **vargs)


def load_config(cfile):
    """Return the config, or make a default one.

    Parameters
    ----------
    cfile: pathlib.Path
        Path to the config file

    Returns
    -------
    configparser.ConfigParser:
        The configuration, but only if it already exists and isn't the default,
        otherwise just exit

    """

    # put in default config file if necessary
    if not cfile.exists():
        cp = configparser.ConfigParser()

        cp['DEFAULT'] = {
            'msg': 'You need an account section for each user, please setup'
        }
        cp['account-FIXME'] = {
            'user': 'FIXME@gmail.com',
            'keyfile': f'{cfile.parent}/FIXME_keyfile.json',
            'credfile': f'{cfile.parent}/FIXME_token'
        }
        with open(cfile, 'w') as cfh:
            cp.write(cfh)

        print(f"Made config file {cfile}, you must edit it")
        sys.exit(1)

    cp = configparser.ConfigParser()
    cp.read(cfile)
    if 'account-FIXME' in cp.sections():
        print(f"You must edit {cfile}.  There is an account-FIXME section")
        sys.exit(2)

    return cp


def save_config(cp, cfile):
    """Update the last run, and save"""
    cp['DEFAULT'] = {
        'last': datetime.datetime.utcnow().replace(tzinfo=pytz.utc).isoformat()

    }
    with open(cfile, 'w') as cfh:
        cp.write(cfh)


# parse command line
p = argparse.ArgumentParser(
    description="""
Sync google contacts
    """,
    epilog="""""",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
p.add_argument(
    '-v', '--verbose', action='store_true',
    help="Verbose output"
)
args = p.parse_args()

# get the configuration file
vprint('Loading configuration')
cdir = pathlib.Path(
    appdirs.AppDirs('google-contacts-sync', 'mcw').user_data_dir
)
os.makedirs(cdir, mode=0o755, exist_ok=True)
cfile = cdir / 'config.ini'
cp = load_config(cfile)

# get the contacts for each user
vprint('Getting contacts')
con = {
    cp[s]['user']: Contacts(cp[s]['keyfile'], cp[s]['credfile'])
    for s in cp.sections()
}

# if an account has no sync tags, the user needs to do a --init
vprint('Checking no new accounts')
for email, acc in con.items():
    if all([i['tag'] is None for i in acc.info]):
        print(
            f'{email} has no sync tags.  It looks like this is the first time '
            'running this script for this account.  You need to pass --init '
            'for me to assign the sync tag to each contact'
        )
        sys.exit(2)

# we need a full set of tags so we can detect changes.  ignore those that don't
# have a tag yet, they will be additions
for email, acc in con.items():
    all_sync_tags.update([i['tag'] for i in acc.info if i['tag'] is not None])

# deletions are detected by missing tags, store the tags to delete in here
vprint('Checking what to delete')
todel = set([])
for email, acc in con.items():
    # tags in acc
    tags = set(i['tag'] for i in acc.info if i['tag'] is not None)
    # print(email)
    # print(t2rn)
    rm = all_sync_tags - tags
    if rm:
        vprint(f'{email}: {len(rm)} contact(s) deleted')
    todel.update(rm)
for email, acc in con.items():
    vprint(f'removing contacts from {email}: ', end='')
    for tag in todel:
        acc.delete(tag, verbose=args.verbose)
    vprint('')

# if there was anything deleted, get all contact info again (so those removed
# are gone from our cached lists)
if todel:
    for acc in con.values():
        acc.get_info()

# new people won't have a tag
vprint('Checking for new people')
addedsomeone = False
for email, acc in con.items():
    # maps tag to (rn, name)
    toadd = [
        (i['rn'], i['name'])
        for i in acc.info if i['tag'] is None
    ]
    if toadd:
        addedsomeone = True
        vprint(f'{email}: these are new {list(i[1] for i in toadd)}')
    for i in toadd:
        # assign a new tag to this person
        tag = new_tag()
        acc.update_tag(i[0], tag)
        newcontact = acc.get(i[0])
        # now add them to all the other accounts
        for otheremail, other in con.items():
            if other == acc:
                continue
            vprint(f'adding {i[1]} to {otheremail}')
            other.add(newcontact)

# updates.  we want to see who has been modified since last run.  of course
# anyone just added will have been modified.  to avoid updating them, we just
# quit if there have been any additions.  it just makes things easier to only
# perform updates when there have been no deletions/additions.  after all this
# is a sync program that runs frequently.
if todel or addedsomeone:
    save_config(cp, cfile)
    sys.exit(0)


lastupdate = dateutil.parser.isoparse(cp['DEFAULT']['last'])

# maps tag to [(acc, update)] where update must be newer than our last run
t2au = {}

for email, acc in con.items():
    for i in acc.info:
        print(i['updated'], lastupdate)


for email, acc in con.items():
    tu = [
        (i['tag'], i['update'])
        for i in acc.info if i['updated'] > lastupdate
    ]
    for t, u in tu:
        t2au.setdefault(t, []).append((acc, u))

vprint(f"There are {len(t2au)} contacts to update")
for tag, aus in t2au.items():
    # find the account with most recent update
    newest = max(aus, key=lambda x: x[1])[0]
    contact = newest.get(tag)
    for email, acc in con.items():
        if acc == newest:
            continue
        acc.update(tag, contact, verbose=args.verbose)






# now let us check for anyone who has been modified since 
sys.exit(0)



matt = Contacts(
    '/home/m/mwilkins/.google/mrmattwilkins_keyfile.json',
    'mrmattwilkins_creds'
)

cn = matt.contacts

# get a random person
rn = list(cn.keys())[0]
luke = matt.get(rn)

luke['names'][0]['displayName'] = 'Luke Foooy'
luke['names'][0]['familyName'] = 'Foooy'

print("FDFD")
for k, v in luke.items():
    print(k, v)

# import sys
# sys.exit(0)

matt.add(luke)


print("After")
for k, v in luke.items():
    print(k, v)
