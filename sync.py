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
    t = ''.join(random.choices(le, k=20))
    while t in all_sync_tags:
        t = ''.join(random.choices(le, k=20))
    all_sync_tags.add(t)
    return t


def duplicates(ls: list):
    """Return a set of duplicates in a list."""

    seen = set([])
    dups = set([])

    for x in ls:
        if x in seen:
            dups.add(x)
        else:
            seen.add(x)

    return dups


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
    print(f"loaded {cfile}")
    # put in default config file if necessary
    if not cfile.exists():
        cp = configparser.ConfigParser()

        cp['DEFAULT'] = {
            'msg': 'You need an account section for each user, please setup',
            'last': '1972-01-01:T00:00:00+00.00'
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
Sync google contacts.

If you have previously used github.com/michael-adler/sync-google-contacts which
uses the csync-uid, after enabling the People API on all your accounts,
editting your config file (you will be prompted about that), you should be all
good to go.

If you haven't synced contacts before you will have to go through an --init
phase, again you will be prompted.

For full instructions see
https://github.com/mrmattwilkins/google-contacts-sync
    """,
    epilog="""""",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
p.add_argument(
    '--init', action='store_true',
    help="Initialize by syncing using names"
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
    cp[s]['user']: Contacts(cp[s]['keyfile'], cp[s]['credfile'], cp[s]['user'])
    for s in cp.sections()
}

if args.init:
    print("Setting up syncing using names to identify identical contacts")

    # get all the names to see if there are duplicates
    for email, acc in con.items():
        dups = duplicates([i['name'] for i in acc.info.values()])
        if dups:
            print('')
            print(
                f"These contacts ({','.join(dups)}) are duplicated in account "
                f"{email}. I will not continue, this will cause confusion"
            )
            print('')
            print("Please remove your duplicates and try again")
            sys.exit(1)

    # keep track of who we have synced so we don't redo them on next account
    done = set([])
    for email, acc in con.items():
        # number seen before by this account, and number pushed
        ndone = 0
        nsync = 0
        for rn, p in acc.info.items():
            if p['name'] in done:
                ndone += 1
            else:
                if p['tag'] is None:
                    p['tag'] = new_tag()
                    acc.update_tag(rn, p['tag'])
                newcontact = acc.get(rn)
                for otheremail, otheracc in con.items():
                    if otheracc == acc:
                        continue
                    rn = otheracc.name_to_rn(p['name'])
                    if rn:
                        otheracc.update_tag(rn, p['tag'])
                        otheracc.update(p['tag'], newcontact, args.verbose)
                    else:
                        otheracc.add(newcontact)
                done.add(p['name'])
                nsync += 1

            print(
                f"Pushing {email} (tot {len(acc.info)}): "
                f"synced {nsync}, done before {ndone}",
                end='\r',
                flush=True
            )
        print('')

    # update the last updated field
    save_config(cp, cfile)
    sys.exit(0)

# if an account has no sync tags, the user needs to do a --init
vprint('Checking no new accounts')
for email, acc in con.items():
    if all([v['tag'] is None for v in acc.info.values()]):
        print(
            f'{email} has no sync tags.  It looks like this is the first time '
            'running this script for this account.  You need to pass --init '
            'for me to assign the sync tag to each contact'
        )
        sys.exit(2)

# we need a full set of tags so we can detect changes.  ignore those that don't
# have a tag yet, they will be additions
for email, acc in con.items():
    all_sync_tags.update([
        v['tag'] for v in acc.info.values() if v['tag'] is not None
    ])

# deletions are detected by missing tags, store the tags to delete in here
vprint('Checking what to delete')
todel = set([])
for email, acc in con.items():
    # tags in acc
    tags = set(v['tag'] for v in acc.info.values() if v['tag'] is not None)
    rm = all_sync_tags - tags
    if rm:
        vprint(f'{email}: {len(rm)} contact(s) deleted')
    todel.update(rm)
if todel:
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
added = []
for email, acc in con.items():
    # maps tag to (rn, name)
    toadd = [
        (rn, v['name'])
        for rn, v in acc.info.items() if v['tag'] is None
    ]
    if toadd:
        vprint(f'{email}: these are new {list(i[1] for i in toadd)}')
    for rn, name in toadd:

        # assign a new tag to this person
        tag = new_tag()
        acc.update_tag(rn, tag)
        newcontact = acc.get(rn)

        # record this is a new person so we won't try syncing them laster
        added.append((acc, rn))

        # now add them to all the other accounts
        for otheremail, other in con.items():
            if other == acc:
                continue
            vprint(f'adding {name} to {otheremail}')
            p = other.add(newcontact)
            added.append((other, p['resourceName']))

# updates.  we want to see who has been modified since last run.  of course
# anyone just added will have been modified, so ignore those in added

lastupdate = dateutil.parser.isoparse(cp['DEFAULT']['last'])

# maps tag to [(acc, rn, updated)] where update must be newer than our last run
t2aru = {}

for email, acc in con.items():
    tru = [
        (v['tag'], rn, v['updated'])
        for rn, v in acc.info.items()
        if v['updated'] > lastupdate and (acc, rn) not in added
    ]
    for t, rn, u in tru:
        t2aru.setdefault(t, []).append((acc, rn, u))

vprint(f"There are {len(t2aru)} contacts to update")
for tag, val in t2aru.items():
    # find the account with most recent update
    newest = max(val, key=lambda x: x[2])
    acc, rn = newest[:2]
    vprint(f"{acc.info[rn]['name']}: ", end='')
    contact = acc.get(rn)
    for otheremail, otheracc in con.items():
        if otheracc == acc:
            continue
        vprint(f"{otheremail} ", end='')
        otheracc.update(tag, contact, verbose=args.verbose)
    vprint('')

# update the last updated field
save_config(cp, cfile)
