#!/usr/bin/env python3
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
import json
import sys
from datetime import datetime
from tzlocal import get_localzone


class ProcessCanvasJSON:
    def __init__(self, filename):
        self.filename = filename
        self.data = []

def load_json_lines(filename):
    """Reads a JSON Lines (NDJSON) file and returns a list of dictionaries."""
    data = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip()
                if clean_line:
                    data.append(json.loads(clean_line))
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(
            f"Error: Failed to parse JSON in file '{filename}'.",
            file=sys.stderr,
        )
        sys.exit(1)
    return data


def process_canvas_json():
    argument_parser = argparse.ArgumentParser(
        description="Match and combine Canvas JSON data files."
    )
    argument_parser.add_argument(
        "accounts_filename",
        type=str,
        help="Path to the Canvas accounts JSON file",
    )
    argument_parser.add_argument(
        "roles_filename", type=str, help="Path to the Canvas roles JSON file"
    )
    argument_parser.add_argument(
        "users_filename", type=str, help="Path to the users JSON file"
    )
    argument_parser.add_argument(
        "account_users_filename",
        type=str,
        help="Path to the Canvas accounts / users / roles mapping JSON file",
    )
    argument_parser.add_argument(
        "conversations_filename",
        type=str,
        help="Path to the conversations JSON file",
    )
    argument_parser.add_argument(
        "conversation_messages_filename",
        type=str,
        help="Path to the conversation messages JSON file",
    )
    argument_parser.add_argument(
        "conversation_participants_filename",
        type=str,
        help="Path to the conversation participants JSON file",
    )
    argument_parser.add_argument(
        "conversation_message_participants_filename",
        type=str,
        help="Path to the conversation message participants JSON file",
    )
    argument_parser.add_argument(
        "communication_channels_filename",
        type=str,
        help="Path to the communication channels JSON file",
    )
    args = argument_parser.parse_args()

    # Batch load all datasets using the helper function
    accounts_data = load_json_lines(args.accounts_filename)
    roles_data = load_json_lines(args.roles_filename)
    account_users_data = load_json_lines(args.account_users_filename)
    users_data = load_json_lines(args.users_filename)
    conversations_data = load_json_lines(args.conversations_filename)
    conversation_messages_data = load_json_lines(
        args.conversation_messages_filename
    )
    conversation_participants_data = load_json_lines(
        args.conversation_participants_filename
    )
    conversation_message_participants_data = load_json_lines(
        args.conversation_message_participants_filename
    )
    communication_channels_data = load_json_lines(
        args.communication_channels_filename
    )

    accounts_dict = {}
    for data_item in accounts_data:
        accounts_dict[data_item["key"]["id"]] = data_item["value"]

    roles_dict = {}
    for data_item in roles_data:
        roles_dict[data_item["key"]["id"]] = data_item["value"]

    account_users_dict = {}
    for data_item in account_users_data:
        account_users_dict[data_item["key"]["id"]] = data_item["value"]
    
    users_dict = {}
    for data_item in users_data:
        users_dict[data_item["key"]["id"]] = data_item["value"]

    conversations_dict = {}
    for data_item in conversations_data:
        conversations_dict[data_item["key"]["id"]] = data_item["value"]

    conversation_participants_dict = {}
    for data_item in conversation_participants_data:
        conversation_participants_dict[data_item["key"]["id"]] = data_item["value"]

    conversation_message_participants_dict = {}
    for data_item in conversation_message_participants_data:
        conversation_message_participants_dict[data_item["key"]["id"]] = data_item["value"]

    communication_channels_dict = {}
    for data_item in communication_channels_data:
        communication_channels_dict[data_item["key"]["id"]] = data_item["value"]

    channels_users_dict = {}
    for key in communication_channels_dict.keys():
        channels_users_dict[communication_channels_dict[key]["user_id"]] = key

    for data_item in conversation_messages_data:
        local_tz = get_localzone()
        clean_message_creation_timestamp = data_item["value"]["created_at"].replace("Z", "+00:00")
        utc_message_creation_datetime = datetime.fromisoformat(clean_message_creation_timestamp)
        local_message_creation_datetime = utc_message_creation_datetime.astimezone(local_tz)

        if not "subject" in conversations_dict[data_item["value"]["conversation_id"]]:
            conversations_dict[data_item["value"]["conversation_id"]]["subject"] = "<No subject>"
        if not data_item["value"]["author_id"] in users_dict:
            users_dict[data_item["value"]["author_id"]]["sortable_name"] = "<non-existent user>"
        if not data_item["value"]["author_id"] in channels_users_dict:
            communication_channels_dict[channels_users_dict[data_item["value"]["author_id"]]]["path"] = \
                "<non-existent channel>"

        output_str = f'{data_item["key"]["id"]},'
        output_str += f'{data_item["value"]["conversation_id"]},'
        output_str += f'{local_message_creation_datetime.strftime("%Y-%m-%d")},'
        output_str += f'{local_message_creation_datetime.strftime("%H:%M:%S")},'
        output_str += f'{data_item["value"]["author_id"]},'
        output_str += f'"{users_dict[data_item["value"]["author_id"]]["sortable_name"]}",'
        output_str += f'"{communication_channels_dict[channels_users_dict[data_item["value"]["author_id"]]]["path"]}",'
        output_str += f'"{conversations_dict[data_item["value"]["conversation_id"]]["subject"]}",'

        print(output_str)

if __name__ == "__main__":
    process_canvas_json()