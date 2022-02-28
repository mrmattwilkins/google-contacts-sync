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
import copy

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
    vprint(f"loaded {cfile}")
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

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever


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
    cp[s]['user']: Contacts(cp[s]['keyfile'], cp[s]['credfile'], cp[s]['user'],args.verbose)
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









#
#======================================
#Sync ContactGroup
#======================================
#


vprint("ContactGroups synchronization...")
all_sync_tags_ContactGroups = set([])
for email, acc in con.items():
    all_sync_tags_ContactGroups.update([
        v['tag'] for v in acc.infoGroup.values() if v['tag'] is not None
    ])


# deletions are detected by missing tags, store the tags to delete in here
vprint('ContactGroups - Checking what to delete')
todel = set([])
for email, acc in con.items():
    # tags in acc
    tags = set(v['tag'] for v in acc.infoGroup.values() if v['tag'] is not None)
    rm = all_sync_tags_ContactGroups - tags
    if rm:
        print(f'{email}: {len(rm)} ContactGroup(s) deleted')
    todel.update(rm)
if todel:
    for email, acc in con.items():
        print(f'removing ContactGroups from {email}: ', end='')
        for tag in todel:
            acc.deleteContactGroup(tag)
        vprint('')


# if there was anything deleted, get all contact info again (so those removed
# are gone from our cached lists)
if todel:
    for acc in con.values():
        acc.get_info()


# new group won't have a tag
vprint('Checking for new ContactGroup')
added = []
for email, acc in con.items():
    # maps tag to (rn, name)
    toadd = [
        (rn, v['name'])
        for rn, v in acc.infoGroup.items() if v['tag'] is None
    ]
    if toadd:
        vprint(f'{email}: these are new {list(i[1] for i in toadd)}')
    for rn, name in toadd:

        # assign a new tag to this ContactGroup
        tag = new_tag()
        acc.updateContactGroup_tag(rn, tag)
        newcontact = acc.getContactGroup(rn)

        # record this is a new ContactGroup so we won't try syncing them laster
        added.append((acc, rn))

        # now add them to all the other accounts
        for otheremail, other in con.items():
            if other == acc:
                continue
            vprint(f'adding {name} to {otheremail}')

            tmp={"contactGroup":{"name":newcontact["name"],"clientData":newcontact["clientData"]}}
            p = other.addContactGroup(tmp)
            added.append((other, p['resourceName']))



# updates.  we want to see who has been modified since last run.  of course
# anyone just added will have been modified, so ignore those in added

lastupdate = dateutil.parser.isoparse(cp['DEFAULT']['last'])

# maps tag to [(acc, rn, updated)] where update must be newer than our last run
t2aru = {}

for email, acc in con.items():
    tru = [
        (v['tag'], rn, v['updated'])
        for rn, v in acc.infoGroup.items()
        if v['updated'] > lastupdate and (acc, rn) not in added
    ]
    for t, rn, u in tru:
        t2aru.setdefault(t, []).append((acc, rn, u))

vprint(f"There are {len(t2aru)} contacts to update")
for tag, val in t2aru.items():
    # find the account with most recent update
    newest = max(val, key=lambda x: x[2])
    acc, rn = newest[:2]
    vprint(f"{acc.infoGroup[rn]['name']}: ", end='')
    contactGroup = acc.getContactGroup(rn)
    for otheremail, otheracc in con.items():
        if otheracc == acc:
            continue
        vprint(f"{otheremail} ", end='')
        otheracc.updateContactGroup(tag, contactGroup)
    vprint('')






#
#======================================
#Sync Contact
#======================================
#



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

            #AGGIUNTA PERSONA CON TAG
            #prima di aggiungere una nuova persona, controllo in quali ContactGroup è
            #se è solo in quello standard ( non ha label ) proseguo così
            #se ne è 1 o più -> recupero il tag di sync dell'etichetta
            #ricerco il tag nella lista delle etichette dell'altro account ( recupero il ResourceName )
            # imposto il resource name corretto 

        #recupero i RN delle label ( non myContacts)
        groupRNs=[ 
                group["contactGroupMembership"]["contactGroupResourceName"] 
                for group in newcontact["memberships"] 
                if group["contactGroupMembership"]["contactGroupId"]!="myContacts"
                ]
        #recupero le syncTag di ogni RN
        groupTags=[ acc.rn_to_tag_ContactGroup(groupRN) for groupRN in groupRNs ] 


        #tolgo tutte le label  ( non myContacts)
        newcontact["memberships"] = [
            group
            for group in newcontact["memberships"] 
            if group["contactGroupMembership"]["contactGroupId"]=="myContacts" 
        ] 

        p=None

        # now add them to all the other accounts
        for otheremail, other in con.items():

            if other == acc:
                continue
            vprint(f'adding {name} to {otheremail}')

            #se ci sono tag da sync 
            if len(groupTags)>0:
                newcontactCopy = copy.deepcopy(newcontact)
                for groupTag in groupTags:
                    #recupero il RN del client destinatario in base al tag di sync 
                    groupRN_other= other.tag_to_rn_ContactGroup(groupTag)
                    #lo aggiungi al contatto

                    groupID_other=remove_prefix(groupRN_other,"contactGroups/")
                    newcontactCopy["memberships"].append( {'contactGroupMembership': {'contactGroupId': groupID_other, 'contactGroupResourceName': groupRN_other}})
                    
                p = other.add(newcontactCopy)


            else:   #se non ci sono , aggiungo e basta
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

     #TODO:
        #prima di mandare l'update
        #prendo tutti i RN delle label non mycontacts ( controllo che non vengano puliti prima...)
        #recupero gli ID di sync delle Label
        #per ciascuno sostituisco

    #recupero i RN delle label ( non myContacts)
    groupRNs=[ 
            group["contactGroupMembership"]["contactGroupResourceName"] 
            for group in contact["memberships"] 
            if group["contactGroupMembership"]["contactGroupId"]!="myContacts"
            ]
    #recupero le syncTag di ogni RN
    groupTags=[ acc.rn_to_tag_ContactGroup(groupRN) for groupRN in groupRNs ] 


    #tolgo tutte le label  ( non myContacts)
    contact["memberships"] = [
        group
        for group in contact["memberships"] 
        if group["contactGroupMembership"]["contactGroupId"]=="myContacts" 
    ] 

  


    for otheremail, otheracc in con.items():
        if otheracc == acc:
            continue
        vprint(f"{otheremail} ", end='')

        if len(groupTags)>0:
                contactCopy = copy.deepcopy(contact)
                for groupTag in groupTags:
                    #recupero il RN del client destinatario in base al tag di sync 
                    groupRN_other= otheracc.tag_to_rn_ContactGroup(groupTag)
                    #lo aggiungi al contatto

                    groupID_other=remove_prefix(groupRN_other,"contactGroups/")
                    contactCopy["memberships"].append( {'contactGroupMembership': {'contactGroupId': groupID_other, 'contactGroupResourceName': groupRN_other}})
                    
                otheracc.update(tag, contactCopy, verbose=args.verbose)
        else:
            otheracc.update(tag, contact, verbose=args.verbose)
    vprint('')

# update the last updated field
save_config(cp, cfile)
