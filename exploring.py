#!/usr/bin/env python3

import pickle
import os.path
import dateutil.parser

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/contacts']

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

        self.contacts = self.__get_contacts()

    def __strip_body(self, body):
        """Return a person body without photos/metadata and other things

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
            fields.  Also any value dict doesn't have metadata either (eg
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

    def __get_contacts(self):
        """Return a dict of contacts, key is resourceName

        Returns
        -------
        dict:
            A dict from resourceName to a dict of info, eg
            {
                'rname0':
                    {
                        'last_update': datetime
                        'body': { ... }
                    },
                'rname1':
                    {
                        'last_update': datetime
                        'body': { ... }
                    },
                ...
            }

            the body itself is a dict that has been sanitized so it doesn't
            include metadata, etag fields, and moreover each of the values
            doesn't have metadata in it.  This is so we can use it for
            adding/updating
        """

        return {
            p['resourceName']: {
                'last_update': dateutil.parser.isoparse(
                    p['metadata']['sources'][0]['updateTime']
                ),
                'body': self.__strip_body(p)
            }
            for p in self.__get_all_contacts()
        }

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
                        personFields='names,metadata',
                        pageToken=next_page_token
                        ).execute()
                connections_list += results.get('connections', [])
                next_page_token = results.get('nextPageToken')
            else:
                break
        return connections_list

    def delete(self, id):
        """Delete a person

        Parameters
        ----------
        id: str
            This is the resourceName of the person to delete

        """
        self.service.people().deleteContact(resourceName=id).execute()

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

    def update(self, id, foo):
        pass

    def get(self, id):
        """Return a person body, stripped of resourceName/etag etc"""

        p = self.service.people().get(
            resourceName=id,
            personFields=','.join(all_person_fields)
        ).execute()
        return self.__strip_body(p)


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


# foo = matt.last_update()
# for k, v in foo.items():
#     print(k, v, dateutil.parser.isoparse(v))

# daibutsu = Contacts(
#     '/home/m/mwilkins/.google/daibutsu_keyfile.json',
#     'daibutsu_creds'
# )
# rn = daibutsu.resource_names()
# print(len(rn))
# dairn = set(rn)
# print(len(dairn))

# print(dairn)

# heather = Contacts(
#     '/home/m/mwilkins/.google/heatherkjenkins_keyfile.json',
#     'heather_creds'
# )
# rn = heather.resource_names()
# print(len(rn))
# heatherrn = set(rn)
# print(len(heatherrn))

# print(heatherrn)

# print(mattrn.intersection(heatherrn))
# sync_contacts.print_all_contacts()
