#!/usr/bin/env python3

import sys
import os
import appdirs
import pathlib
import configparser
import argparse


from contacts import Contacts


def load_config(cfile, users=[]):
    # put in default config file if necessary
    if not cfile.exists():
        print(f"Making a default config file {cfile}, you need to edit it")

        cp = configparser.ConfigParser()

        cp['DEFAULT'] = {
            'msg': 'You need an account section for each user, please setup',
            'state': cfile.parent / 'state'
        }

        if len(users) == 0:
            users = ['FIXME']
        for u in users:
            cp[f'account-{u}'] = {
                'user': f'{u}@gmail.com',
                'keyfile': f'{cfile.parent / u}_keyfile.json',
                'credfile': f'{cfile.parent / u}_token'
            }

        with open(cfile, 'w') as cfh:
            cp.write(cfh)

        sys.exit(1)

    cp = configparser.ConfigParser()
    cp.read(cfile)
    return cp


# parse command line
p = argparse.ArgumentParser(
    description="""
Sync google contacts
    """,
    epilog="""""",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
p.add_argument(
    'username', type=str, nargs='+',
    help="The usernames to sync, without the @gmail.com"
)
p.add_argument(
    '-v', '--verbose', action='store_true',
    help="Verbose output"
)
args = p.parse_args()

# get the configuration file
cdir = pathlib.Path(
    appdirs.AppDirs('google-contacts-sync', 'mcw').user_data_dir
)
os.makedirs(cdir, mode=0o755, exist_ok=True)
cfile = cdir / 'config.ini'
cp = load_config(cfile, users=args.username)

# get the contacts for each user
con = {
    cp[s]['user']: Contacts(cp[s]['keyfile'], cp[s]['credfile'])
    for s in cp.sections()
}


print(con)

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
