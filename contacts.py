#!/usr/bin/env python3

import pickle
import os.path
import dateutil.parser

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

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


class Contacts():

    def __init__(self, keyfile, credfile):

        creds = None

        # The file token.pickle stores the user's access and refresh tokens,
        # and is created automatically when the authorization flow completes
        # for the first time.
        if os.path.exists(credfile):
            with open(credfile, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
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
        """Return a person body without photos/metadata and other things

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
            Like body but without resourceName, etag, photos and metadata
            fields.  Also no metadata in each field (eg
            ['names'][0]['metadata']).
        """

        # keep all_person_fields, but not photos/metadata
        tokeep = set(all_person_fields) - set(['metadata', 'photos'])
        ret = {k: v for k, v in body.items() if k in tokeep}

        # all the other fields are lists of dicts, we must drop the metadata
        # key from any of those dicts
        for k, v in ret.items():
            for i in v:
                i.pop('metadata', None)

        return ret

    def get_info(self):
        """Store a list of contact info

        Returns
        -------
        list:
            A list of dicts containing rn, tag, updated, name, eg
            [
                {
                    'rn': resource name,
                    'tag': the csync_id,
                    'updated': datetime,
                    'name': the display name
                } ...
            ]
        """

        self.info = [
            {
                'rn': p['resourceName'],
                'tag': tagls[0] if (tagls := [
                        kv['value']
                        for kv in p.get('clientData', {})
                        if kv.get('key', None) == SYNC_TAG
                ])
                else None,
                'updated': dateutil.parser.isoparse(
                    p['metadata']['sources'][0]['updateTime']
                ),
                'name': p['names'][0]['displayName']
            }
            for p in self.__get_all_contacts()
        ]

    def __get_all_contacts(self):
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
                        personFields='names,clientData,metadata',
                        pageToken=next_page_token
                        ).execute()
                connections_list += results.get('connections', [])
                next_page_token = results.get('nextPageToken')
            else:
                break
        return connections_list

    def delete(self, tag: str, verbose=False):
        """Delete a person

        Parameters
        ----------
        tag: str
            This is a tag to delete

        """
        # need to find the resource name
        rnn = [(i['rn'], i['name']) for i in self.info if i['tag'] == tag]
        for rn, n in rnn:
            if verbose:
                print(f'{n} ', end='')
            self.service.people().deleteContact(resourceName=rn).execute()

    def update_tag(self, rn: str, tag: str):
        """Update the tag for a contact

        Parameters
        ---------
        rn: str
            The resource name of person to add tag to

        tag: str
            The tag to add.  No check on uniques is made, but it better be

        """
        # get the current etag and clientData
        p = self.service.people().get(
            resourceName=rn,
            personFields='clientData'
        ).execute()

        # get the clientData without the tag dict
        wout = [
            i
            for i in p.get('clientData', [])
            if i.get('key', None) != SYNC_TAG
        ]
        wout.append({'key': SYNC_TAG, 'value': tag})

        self.service.people().updateContact(
            resourceName=rn,
            updatePersonFields='clientData',
            body={'etag': p['etag'], 'clientData': wout}
        ).execute()

    def add(self, body):
        """Add a person with this body

        Parameters
        ----------
        body: dict
            Maps all_person_fields to lists of dicts with info in them.

        """

        new_contact = self.service.people().createContact(
            body=body
        ).execute()
        return new_contact

    def update(self, tag: str, body: dict, verbose=False):
        # need to find the resource name
        rnn = [(i['rn'], i['name']) for i in self.info if i['tag'] == tag][0]
        if verbose:
            print(f'{rnn[1]} ', end='')

        # get the current etag
        p = self.service.people().get(
            resourceName=rnn[0],
        ).execute()

        print(p)

        body.update({'etag': p['etag']})
        self.service.people().updateContact(
            resourceName=rnn[0],
            updatePersonFields=','.join(all_person_fields),
            body=body
        ).execute()

    def get(self, rn):
        """Return a person body, stripped of resourceName/etag etc"""

        p = self.service.people().get(
            resourceName=rn,
            personFields=','.join(all_person_fields)
        ).execute()
        return self.__strip_body(p)
