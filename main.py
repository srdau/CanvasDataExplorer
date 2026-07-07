#!/opt/homebrew/bin/python3
#
# This program will read some JSON table dumps from the Canvas Data 2 API
# and produce a single canvas_conversations.json file with improved
# human readability.
#
# Stephen Darragh July 2026
#
# Licensed under GPLv3
#

import argparse
import sys
import json

argument_parser = argparse.ArgumentParser(description="Match and combine Canvas JSON data files.")
argument_parser.add_argument('accounts_filename', type=str, help="Path to the Canvas accounts JSON file")
argument_parser.add_argument('roles_filename', type=str, help="Path to the Canvas roles JSON file")
argument_parser.add_argument('users_filename', type=str, help="Path to the users JSON file")
argument_parser.add_argument('account_users_filename', type=str, help="Path to the Canvas accounts / users / roles mapping JSON file")
argument_parser.add_argument('conversations_filename', type=str, help="Path to the conversations JSON file")
argument_parser.add_argument('conversation_messages_filename', type=str, help="Path to the conversation messages JSON file")
argument_parser.add_argument('conversation_participants_filename', type=str, help="Path to the conversation participants JSON file")
argument_parser.add_argument('conversation_message_participants_filename', type=str, help="Path to the conversation message participants JSON file")
args = argument_parser.parse_args()


accounts_data = []
with open(args.accounts_filename, 'r') as f:
    for line in f:
        # Strip trailing whitespaces and ignore empty lines
        clean_line = line.strip()
        if clean_line:
            # Parse the single line string into a Python dict
            obj = json.loads(clean_line)
            accounts_data.append(obj)

roles_data = []
with open(args.roles_filename, 'r') as f:
    for line in f:
        # Strip trailing whitespaces and ignore empty lines
        clean_line = line.strip()
        if clean_line:
            # Parse the single line string into a Python dict
            obj = json.loads(clean_line)
            roles_data.append(obj)

account_users_data = []
with open(args.account_users_filename, 'r') as f:
    for line in f:
        # Strip trailing whitespaces and ignore empty lines
        clean_line = line.strip()
        if clean_line:
            # Parse the single line string into a Python dict
            obj = json.loads(clean_line)
            account_users_data.append(obj)

users_data = []
with open(args.users_filename, 'r') as f:
    for line in f:
        # Strip trailing whitespaces and ignore empty lines
        clean_line = line.strip()
        if clean_line:
            # Parse the single line string into a Python dict
            obj = json.loads(clean_line)
            users_data.append(obj)

conversations_data = []
with open(args.conversations_filename, 'r') as f:
    for line in f:
        # Strip trailing whitespaces and ignore empty lines
        clean_line = line.strip()
        if clean_line:
            # Parse the single line string into a Python dict
            obj = json.loads(clean_line)
            conversations_data.append(obj)

conversation_messages_data = []
with open(args.conversation_messages_filename, 'r') as f:
    for line in f:
        # Strip trailing whitespaces and ignore empty lines
        clean_line = line.strip()
        if clean_line:
            # Parse the single line string into a Python dict
            obj = json.loads(clean_line)
            conversation_messages_data.append(obj)

conversation_participants_data = []
with open(args.conversation_participants_filename, 'r') as f:
    for line in f:
        # Strip trailing whitespaces and ignore empty lines
        clean_line = line.strip()
        if clean_line:
            # Parse the single line string into a Python dict
            obj = json.loads(clean_line)
            conversation_participants_data.append(obj)

conversation_message_participants_data = []
with open(args.conversation_message_participants_filename, 'r') as f:
    for line in f:
        # Strip trailing whitespaces and ignore empty lines
        clean_line = line.strip()
        if clean_line:
            # Parse the single line string into a Python dict
            obj = json.loads(clean_line)
            conversation_message_participants_data.append(obj)

