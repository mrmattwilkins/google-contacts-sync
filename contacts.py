#!/usr/bin/env python3

import pickle
import os.path
import dateutil.parser

from time import sleep

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.auth.exceptions


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/contacts']

# The user field that we store a key in to uniquely identify a person across
# accounts
SYNC_TAG = 'csync-uid'

# all personFields, I don't know to programmatically get these, I just got them
# from
# https://developers.google.com/people/api/rest/v1/people.connections/list
all_person_fields = [
    'addresses',
    'ageRanges',
    'biographies',
    'birthdays',
    'calendarUrls',
    'clientData',
    'coverPhotos',
    'emailAddresses',
    'events',
    'externalIds',
    'genders',
    'imClients',
    'interests',
    'locales',
    'locations',
    'memberships',
    'metadata',
    'miscKeywords',
    'names',
    'nicknames',
    'occupations',
    'organizations',
    'phoneNumbers',
    'photos',
    'relations',
    'sipAddresses',
    'skills',
    'urls',
    'userDefined'
]
all_update_person_fields = [
    'addresses',
    'biographies',
    'birthdays',
    'clientData',
    'emailAddresses',
    'events',
    'externalIds',
    'genders',
    'imClients',
    'interests',
    'locales',
    'locations',
    'memberships',
    'miscKeywords',
    'names',
    'nicknames',
    'occupations',
    'organizations',
    'phoneNumbers',
    'relations',
    'sipAddresses',
    'urls',
    'userDefined'
]


class Contacts():

    def __init__(self, keyfile, credfile, user, verbose):

        creds = None

        # The file token.pickle stores the user's access and refresh tokens,
        # and is created automatically when the authorization flow completes
        # for the first time.
        if os.path.exists(credfile):
            with open(credfile, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            managedToRefresh=False
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    managedToRefresh=True
                except google.auth.exceptions.RefreshError:
                    print("can't refresh token; relogin")

            if not managedToRefresh:
                if verbose:
                    print("login into:", user)

                flow = InstalledAppFlow.from_client_secrets_file(
                    keyfile, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(credfile, 'wb') as token:
                pickle.dump(creds, token)

        creds = creds
        self.service = build('people', 'v1', credentials=creds)

        self.get_info()

    def __strip_body(self, body):
        """Return a person body without coverPhotos/photos/metadata
        and some other things

        We need just this info about a person when we do an update or add, the
        photos field doesn't work with People API at the moment, and you don't
        pass metadata for add/update.

        Parameters
        ----------
        body: dict
            A dict returned from people api.  Looks something like

            {
                'resourceName': 'people/blah',
                'etag': 'blah',
                'metadata': {
                    'sources': [
                        {
                            'type': 'CONTACT',
                            'id': 'blah',
                            'etag': 'blah',
                            'updateTime': '2016-06-05T18:56:16.972001Z'
                        }
                    ],
                    'objectType': 'PERSON'
                },
                'names': [
                    {
                        'metadata':
                            {
                                'primary': True,
                                'source': {'type': 'CONTACT', 'id': 'blah'}
                            },
                        'displayName': 'John Smith',
                        'familyName': 'Smith',
                        'givenName': 'John',
                        'displayNameLastFirst': 'Smith, John',
                        'unstructuredName': 'John Smith'
                    }
                ],
                'photos': [
                    blah
                ]
                blah
            }


        Returns
        -------
        dict:
            Like body but without resourceName, etag, coverPhotos, photos and
            metadata fields.  Also no metadata in each field (eg
            ['names'][0]['metadata']).  So the above example would be stripped
            to
            {
                'names': [
                    {
                        'displayName': 'John Smith',
                        'familyName': 'Smith',
                        'givenName': 'John',
                        'displayNameLastFirst': 'Smith, John',
                        'unstructuredName': 'John Smith'
                    }
                ],
                blah
            }

        """

        # keep all_person_fields, but not photos/metadata
        bad = set(['metadata', 'coverPhotos', 'photos'])
        tokeep = set(all_person_fields) - bad
        ret = {k: v for k, v in body.items() if k in tokeep}

        # all the other fields are lists of dicts, we must drop the metadata
        # key from any of those dicts
        for k, v in ret.items():
            for i in v:
                i.pop('metadata', None)

        # for some reason some of my contacts have more than one name.  remove
        # anything except the first.  same problem with genders and birthdays

        if 'names' in ret:
            ret['names'] = [ret['names'][0]]

        if 'genders' in ret:
            ret['genders'] = [ret['genders'][0]]
        if "birthdays" in ret:
            ret["birthdays"] = [ret["birthdays"][0]]

        return ret

    def get_info(self):
        """Store a dict of contact info

        Returns
        -------
        dict:
            A dict of dicts tag, etag, updated, name
            {
                'rn0':
                    {
                        'etag': str
                        'tag': the csync_id (possibly None for newly added)
                        'updated': datetime,
                        'name': the display name
                    },
                'rn1':
                    {
                        'etag': str
                        'tag': the csync_id (possibly None for newly added)
                        'updated': datetime,
                        'name': the display name
                    },
                ...
            }
        """

        self.info = {}
        for p in self.get_all_contacts():
            tagls = [
                kv['value']
                for kv in p.get('clientData', {})
                if kv.get('key', None) == SYNC_TAG
            ]
            if not ('names' in p or 'organizations' in p):
                continue

            self.info[p['resourceName']] = {
                'etag': p['etag'],
                'tag': tagls[0] if tagls else None,
                'updated': dateutil.parser.isoparse(
                    p['metadata']['sources'][0]['updateTime']
                ),
                'name': (
                    p['names'][0]['displayName']
                    if 'names' in p else p['organizations'][0]['name']
                )
            }

        self.info_group = {}
        for p in self.get_contactGroups():
            
            if p["groupType"] != "USER_CONTACT_GROUP":
                continue

            tagls = [
                kv['value']
                for kv in p.get('clientData', {})
                if kv.get('key', None) == SYNC_TAG
            ]

            self.info_group_add(p,tagls)
            """self.info_group[p['resourceName']] = {
                'etag': p['etag'],
                'tag': tagls[0] if tagls else None,
                'updated': dateutil.parser.isoparse(
                    p['metadata']['updateTime']
                ),
                'name': p['name']
            }"""

    def info_group_add(self,p,tagls=None):
        """add or update a group into the "global" info_group group"""

        self.info_group[p['resourceName']] = {
                'etag': p['etag'],
                'tag': tagls[0] if tagls else None,
                'updated': dateutil.parser.isoparse(
                    p['metadata']['updateTime']
                ),
                'name': p['name']
        }


    def get_all_contacts(
        self, fields=['names', 'organizations', 'clientData', 'metadata']
    ):
        """Return a list of all the contacts."""

        # Keep getting 1000 connections until the nextPageToken becomes None
        connections_list = []
        next_page_token = ''
        while True:
            if not (next_page_token is None):
                # Call the People API
                results = self.service.people().connections().list(
                        resourceName='people/me',
                        pageSize=1000,
                        personFields=','.join(fields),
                        pageToken=next_page_token
                        ).execute()
                connections_list += results.get('connections', [])
                next_page_token = results.get('nextPageToken')
            else:
                break
        return connections_list

    def tag_to_rn(self, tag):
        """Return the resourceName for this tag, or None"""
        rn = [rn for rn, v in self.info.items() if v['tag'] == tag]         #TODO: once did not find the tag - the next day he found it!!!! WTF?!
        if not rn:
            return None
        assert(len(rn) == 1)
        return rn[0]

    def name_to_rn(self, name):
        """Return the resourceName for this name, or None"""
        rn = [
            rn
            for rn, v in self.info.items()
            if v['name'].lower() == name.lower()
        ]
        if not rn:
            return None
        assert(len(rn) == 1)
        return rn[0]

    def delete(self, tag: str, verbose=False):
        """Delete a person

        Parameters
        ----------
        tag: str
            This is a tag to delete

        """
        # need to find the resource name
        rn = self.tag_to_rn(tag)
        if rn is None:
            return

        if verbose:
            print(f"{self.info[rn]['name']} ", end='')

        tts=0.5 #500 ms start -> exponential backoff
        while True:
            try:
                self.service.people().deleteContact(resourceName=rn).execute()
                return
            except HttpError:
                # sleep to avoid 429 HTTP error because rate limit with tts
                sleep(tts)
                tts*=2


    def update_tag(self, rn: str, tag: str):
        """Update the tag for a contact

        Parameters
        ---------
        rn: str
            The resource name of person to add tag to

        tag: str
            The tag to add.  No check on uniques is made, but it better be

        """

        tts=0.5 #500 ms start -> exponential backoff
        while True:
            # get the current clientData
            try:
                p = self.service.people().get(
                    resourceName=rn,
                    personFields='clientData'
                ).execute()

                # the clientData without the tag dict
                wout = [
                    i
                    for i in p.get('clientData', [])
                    if i.get('key', None) != SYNC_TAG
                ]
                wout.append({'key': SYNC_TAG, 'value': tag})

                self.service.people().updateContact(
                    resourceName=rn,
                    updatePersonFields='clientData',
                    body={'etag': self.info[rn]['etag'], 'clientData': wout}
                ).execute()
                return
            except HttpError:
                # sleep to avoid 429 HTTP error because rate limit with tts
                sleep(tts)
                tts*=2

    def add(self, body):
        """Add a person with this body

        Parameters
        ----------
        body: dict
            Maps all_person_fields to lists of dicts with info in them.

        """
        tts=0.5 #500 ms start -> exponential backoff
        while True:
            # get the current clientData
            try:
                new_contact = self.service.people().createContact(
                    body=body
                ).execute()
                return new_contact
            except HttpError:
                # sleep to avoid 429 HTTP error because rate limit with tts
                sleep(tts)
                tts*=2

    def update(self, tag: str, body: dict, verbose=False):
        rn = self.tag_to_rn(tag)

        if rn is not None:
            tts=0.5 #500 ms start -> exponential backoff
            while True:
                try:
                    body.update({'etag': self.info[rn]['etag']})
                    self.service.people().updateContact(
                        resourceName=rn,
                        updatePersonFields=','.join(all_update_person_fields),
                        body=body
                    ).execute()
                    return
                except HttpError as e:
                    # sleep to avoid 429 HTTP error because rate limit with tts
                    if verbose:
                        print("\n","[ERROR] ", e)
                    sleep(tts)
                    tts*=2

    def get(self, rn, verbose=False):
        """Return a person body, stripped of resourceName/etag etc"""
        tts=0.5 #500 ms start -> exponential backoff
        while True:
            try:
                p = self.service.people().get(
                    resourceName=rn,
                    personFields=','.join(all_person_fields)
                ).execute()
                return self.__strip_body(p)
            except HttpError as e:
                if verbose:
                    print("\n","[ERROR] ", e)
                sleep(tts)
                tts*=2

    def rn_to_tag_contactGroup(self, rn):
        """Return the resourceName for this tag, or None"""

        tag = [
            v['tag']
            for rn_loc, v in self.info_group.items() if rn_loc == rn
        ]
        if not tag:
            return None
        assert(len(tag) == 1)
        return tag[0]

    def tag_to_rn_contactGroup(self, tag):
        """Return the resourceName for this tag, or None"""
        rn = [rn for rn, v in self.info_group.items() if v['tag'] == tag]
        if not rn:
            return None
        assert(len(rn) == 1)
        return rn[0]

    def add_contactGroup(self, body, verbose=False):
        """Add a person with this body

        Parameters
        ----------
        body: dict


        """

        tts=0.5 #500 ms start -> exponential backoff
        while True:
            try:
                body["readGroupFields"] = "clientData,groupType,metadata,name"
                new_contact = self.service.contactGroups().create(
                    body=body
                ).execute()
                return new_contact
            except HttpError as e:
                if verbose:
                    print("\n","[ERROR] ", e)
                sleep(tts)
                tts*=2


    def get_contactGroups(self, verbose=False):
        """Return a list of all the ContactGroup."""

        # Keep getting 1000 connections until the nextPageToken becomes None
        ContactGroup_list = []
        next_page_token = ''
        while True:
            if not (next_page_token is None):

                tts=0.5 #500 ms start -> exponential backoff
                while True:
                    try:
                        # Call the People API
                        results = self.service.contactGroups().list(
                            pageSize=1000,
                            pageToken=next_page_token,
                            groupFields="clientData,name,metadata,groupType"
                        ).execute()
                        break
                    except HttpError as e:
                        if verbose:
                            print("\n","[ERROR] ", e)
                        sleep(tts)
                        tts*=2

                ContactGroup_list += results.get('contactGroups', [])
                next_page_token = results.get('nextPageToken')
            else:
                break
        return ContactGroup_list

    def get_contactGroup(self, rn, verbose=False):
        """Return a person body, stripped of resourceName/etag etc"""
        tts=0.5 #500 ms start -> exponential backoff
        while True:
            try:
                p = self.service.contactGroups().get(
                    resourceName=rn,
                    groupFields="clientData,groupType,metadata,name"
                ).execute()
                return p
            except HttpError as e:
                if verbose:
                    print("\n","[ERROR] ", e)
                sleep(tts)
                tts*=2

    def get_contactGroup_wait_SYNC_TAG(self, rn, verbose=False):
        """
        continues requesting a contact Group until the SYNC_TAG is found
        ( sometimes, just after updating the clientData with the SYNC_TAG inside, the stored SYNC_TAG is not returned at subsequent get_contactGroups)
        """
        cont=None
        tts=0.5 #500 ms start -> exponential backoff
        while True:
                cont = self.get_contactGroup(rn)
                if "clientData" in cont: 
                    k = [i for i in cont["clientData"] if "key" in i and i["key"]==SYNC_TAG]
                    if len(k)>0:
                        break
                else:
                    if verbose:
                        print("\n","[ERROR] ", "SYNC_TAG missing")
                    sleep(tts)
                    tts*=2
        return cont
    

    def update_contactGroup_tag(self, rn: str, tag: str):
        """Update the tag for a contact

        Parameters
        ---------
        rn: str
            The resource name of ContactGroup to add tag to

        tag: str
            The tag to add.  No check on uniques is made, but it better be

        """
        # get the current clientData
        tts=0.5 #500 ms start -> exponential backoff
        while True:
            try:
                p = self.service.contactGroups().get(
                    resourceName=rn,
                    groupFields='clientData'
                ).execute()

                # the clientData without the tag dict
                wout = [
                    i
                    for i in p.get('clientData', [])
                    if i.get('key', None) != SYNC_TAG
                ]
                wout.append({'key': SYNC_TAG, 'value': tag})

                self.service.contactGroups().update(
                    resourceName=rn,
                    body={
                        "contactGroup": {
                            'etag': self.info_group[rn]['etag'],
                            'clientData': wout
                        },
                        "updateGroupFields": "clientData",
                        "readGroupFields": "clientData,groupType,metadata,name"
                    }
                ).execute()
                return
            except HttpError as e:
                if e.status_code==409 and "Contact group etag is outdated" in e.reason: #etag "expired" ( or someone has changed something)
                    #re-get the group
                    p = self.get_contactGroup(rn)
                    self.info_group_add(p,None)             #TODO: check if is correct to insert the tag...?  None <-> tag


                print("\n","[ERROR] ", e)
                sleep(tts)
                tts*=2

    def update_contactGroup(self, tag: str, body: dict):
        rn = self.tag_to_rn_contactGroup(tag)

        if rn is not None:
            tts=0.5 #500 ms start -> exponential backoff
            while True:
                try:
                    self.service.contactGroups().update(
                        resourceName=rn,
                        body={
                            "contactGroup": {
                                'etag': self.info_group[rn]['etag'],
                                'name': body["name"]
                            },
                            "readGroupFields": "clientData,groupType,metadata,name"
                        }
                    ).execute()
                    return
                except HttpError as e:
                    print("\n","[ERROR] ", e)
                    sleep(tts)
                    tts*=2

    def delete_contactGroup(self, tag: str):
        # need to find the resource name
        rn = self.tag_to_rn_contactGroup(tag)
        if rn is None:
            return

        # print(f"{self.info_group[rn]['name']} ", end='')

        tts=0.5 #500 ms start -> exponential backoff
        while True:
            try:
                self.service.contactGroups().delete(
                    resourceName=rn, deleteContacts=False
                ).execute()
                return
            except HttpError as e:
                print("\n","[ERROR] ", e)
                sleep(tts)
                tts*=2
