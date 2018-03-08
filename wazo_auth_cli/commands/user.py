# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import json

from cliff.command import Command
from cliff.lister import Lister

from ..helpers import ListBuildingMixin, PolicyIdentifierMixin, UserIdentifierMixin


class UserAdd(UserIdentifierMixin, PolicyIdentifierMixin, Command):

    def get_parser(self, *args, **kwargs):
        parser = super().get_parser(*args, **kwargs)
        relation = parser.add_mutually_exclusive_group(required=True)
        relation.add_argument('--policy',
                              help='The name or UUID of the policy to add to this user')
        parser.add_argument('identifier', help='username or UUID')
        return parser

    def take_action(self, parsed_args):
        uuid = self.get_user_uuid(self.app.client, parsed_args.identifier)

        if parsed_args.policy:
            return self._add_policy(uuid, parsed_args)

    def _add_policy(self, uuid, parsed_args):
        policy_uuid = self.get_policy_uuid(self.app.client, parsed_args.policy)
        self.app.client.users.add_policy(uuid, policy_uuid)


class UserCreate(Command):

    def get_parser(self, prog_name):
        parser = super(UserCreate, self).get_parser(prog_name)
        parser.add_argument('--uuid', help="The user's UUID when matching a PBX user")
        parser.add_argument('--password', help="the user's password", required=True)
        parser.add_argument('--email', help="the user's main email address")
        parser.add_argument('--firstname', help="The user's firstname")
        parser.add_argument('--lastname', help="The user's lastname")
        parser.add_argument('name', help="the user's username")
        return parser

    def take_action(self, parsed_args):
        self.app.LOG.debug(parsed_args)
        body = dict(
            username=parsed_args.name,
            password=parsed_args.password,
        )
        if parsed_args.uuid:
            body['uuid'] = parsed_args.uuid
        if parsed_args.email:
            body['email_address'] = parsed_args.email
        if parsed_args.firstname:
            body['firstname'] = parsed_args.firstname
        if parsed_args.lastname:
            body['lastname'] = parsed_args.lastname

        self.app.LOG.debug('Creating user %s', body)
        user = self.app.client.users.new(**body)
        self.app.LOG.info(user)
        self.app.stdout.write(user['uuid'] + '\n')


class UserDelete(UserIdentifierMixin, Command):

    def get_parser(self, *args, **kwargs):
        parser = super().get_parser(*args, **kwargs)
        parser.add_argument('identifier', help="The username or UUID of the user to delete")
        return parser

    def take_action(self, parsed_args):
        uuid = self.get_user_uuid(self.app.client, parsed_args.identifier)
        self.app.LOG.debug('Deleting user %s', uuid)
        self.app.client.users.delete(uuid)


class UserList(ListBuildingMixin, Lister):

    _columns = ['uuid', 'username', 'email']
    _removed_columns = ['emails']

    def take_action(self, parsed_args):
        result = self.app.client.users.list()
        if not result['items']:
            return (), ()

        raw_items = self._add_email_column(result['items'])
        headers = self.extract_column_headers(raw_items[0])
        items = self.extract_items(headers, raw_items)
        return headers, items

    def _add_email_column(self, items):
        for item in items:
            email = self._main_email(item['emails']) or self._first_email(item['emails'])
            item['email'] = email
        return items

    @staticmethod
    def _main_email(emails):
        for email in emails:
            if email['main']:
                return email['address']
        return ''

    @staticmethod
    def _first_email(emails):
        for email in emails:
            return email['address']
        return ''


class UserRemove(UserIdentifierMixin, PolicyIdentifierMixin, Command):

    def get_parser(self, *args, **kwargs):
        parser = super().get_parser(*args, **kwargs)
        relation = parser.add_mutually_exclusive_group(required=True)
        relation.add_argument('--policy',
                              help='The name or UUID of the policy to remove from this user')
        parser.add_argument('identifier', help='username or UUID')
        return parser

    def take_action(self, parsed_args):
        uuid = self.get_user_uuid(self.app.client, parsed_args.identifier)

        if parsed_args.policy:
            return self._remove_policy(uuid, parsed_args)

    def _remove_policy(self, uuid, parsed_args):
        policy_uuid = self.get_policy_uuid(self.app.client, parsed_args.policy)
        self.app.client.users.remove_policy(uuid, policy_uuid)


class UserShow(UserIdentifierMixin, Command):

    def get_parser(self, *args, **kwargs):
        parser = super().get_parser(*args, **kwargs)
        parser.add_argument('identifier', help='username or UUID')
        return parser

    def take_action(self, parsed_args):
        uuid = self.get_user_uuid(self.app.client, parsed_args.identifier)
        user = self.app.client.users.get(uuid)
        user['policies'] = self.app.client.users.get_policies(uuid)['items']
        user['tenants'] = self.app.client.users.get_tenants(uuid)['items']
        user['groups'] = self.app.client.users.get_groups(uuid)['items']
        self.app.stdout.write(json.dumps(user, indent=True, sort_keys=True) + '\n')
