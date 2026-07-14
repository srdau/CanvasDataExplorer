#!/usr/bin/env python3
"""Export Canvas Data 2 conversation dumps to a single, human-readable CSV.

Reads the JSON Lines (NDJSON) table dumps produced by the Canvas Data 2 API
and writes a `canvas_conversations.csv`-style report to stdout, joining
conversations, messages, participants, users, and communication channels
so each row is self-describing (author name/email, subject, recipients,
etc.) rather than a set of opaque foreign keys.

Stephen Darragh, July 2026
Licensed under GPLv3
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import wrap
from typing import Any

from tzlocal import get_localzone

logger = logging.getLogger(__name__)

# Canvas truncates conversation message bodies into rows/pages of roughly
# this many characters when exporting; we mirror that here so a single
# logical message can span multiple output rows without exceeding it.
MAX_BODY_PART_LENGTH = 1016

# Email domain suffixes used to classify an author as staff or student.
STAFF_EMAIL_SUFFIX = "det.nsw.edu.au"
STUDENT_EMAIL_SUFFIX = "education.nsw.gov.au"

UNKNOWN_USER_TYPE = "Unknown"
STAFF_USER_TYPE = "Staff"
STUDENT_USER_TYPE = "Student"
OTHER_USER_TYPE = "Other"

NO_SUBJECT_PLACEHOLDER = "<No subject>"
NON_EXISTENT_USER_NAME = "<non-existent user>"
NON_EXISTENT_CHANNEL_PATH = "<non-existent channel>"

CSV_COLUMNS = [
    "message ID",
    "body part",
    "total parts",
    "conversation ID",
    "date",
    "time",
    "timezone offset",
    "author user ID",
    "role",
    "author name",
    "author email",
    "subject",
    "has attachments",
    "recipients",
    "message body",
]


@dataclass
class CanvasDataset:
    """All the Canvas Data 2 tables this report needs, already loaded."""

    accounts: list[dict[str, Any]]
    roles: list[dict[str, Any]]
    users: list[dict[str, Any]]
    account_users: list[dict[str, Any]]
    conversations: list[dict[str, Any]]
    conversation_messages: list[dict[str, Any]]
    conversation_participants: list[dict[str, Any]]
    conversation_message_participants: list[dict[str, Any]]
    communication_channels: list[dict[str, Any]]
    enrollments: list[dict[str, Any]]


def load_json_lines(filename: str) -> list[dict[str, Any]]:
    """Read a JSON Lines (NDJSON) file and return a list of dictionaries.

    Exits the program with an error message if the file is missing or
    contains invalid JSON, matching the original script's behaviour.
    """
    records: list[dict[str, Any]] = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
    except FileNotFoundError:
        logger.error("The file '%s' was not found.", filename)
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON in file '%s'.", filename)
        sys.exit(1)
    return records


def index_by_key_id(records: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    """Build a {key.id: value} lookup from a Canvas Data 2 table dump."""
    return {record["key"]["id"]: record["value"] for record in records}


def build_user_to_account_user(
    account_users: dict[Any, dict[str, Any]],
) -> dict[Any, Any]:
    """Map user_id -> account_user key, inverting the account_users table."""
    return {value["user_id"]: key for key, value in account_users.items()}


def build_message_recipients(
    conversation_message_participants: list[dict[str, Any]],
) -> dict[Any, list[Any]]:
    """Group participant user_ids by the conversation_message_id they belong to."""
    recipients: dict[Any, list[Any]] = {}
    for record in conversation_message_participants:
        value = record["value"]
        recipients.setdefault(value["conversation_message_id"], []).append(
            value["user_id"]
        )
    return recipients


def build_user_email_index(
    communication_channels: dict[Any, dict[str, Any]],
) -> dict[Any, Any]:
    """Map user_id -> communication_channels key, for that user's email channel."""
    return {
        channel["user_id"]: key
        for key, channel in communication_channels.items()
        if channel["path_type"] == "email"
    }


def build_course_users(
    enrollments: list[dict[str, Any]],
) -> dict[Any, dict[Any, str]]:
    """Map course_id -> {user_id: enrollment type}."""
    course_users: dict[Any, dict[Any, str]] = {}
    for record in enrollments:
        value = record["value"]
        course_users.setdefault(value["course_id"], {})[value["user_id"]] = value[
            "type"
        ]
    return course_users


def classify_user_type(email_path: str | None) -> str:
    """Classify an author as Staff, Student, Other, or Unknown by email domain."""
    if email_path is None:
        return UNKNOWN_USER_TYPE
    if email_path.endswith(STAFF_EMAIL_SUFFIX):
        return STAFF_USER_TYPE
    if email_path.endswith(STUDENT_EMAIL_SUFFIX):
        return STUDENT_USER_TYPE
    return OTHER_USER_TYPE


def resolve_author(
    author_id: Any,
    users: dict[Any, dict[str, Any]],
    user_email_channels: dict[Any, Any],
    communication_channels: dict[Any, dict[str, Any]],
) -> tuple[str, str, str]:
    """Return (author_name, author_email, user_type) for a message author.

    Falls back to placeholder values if the author or their email channel
    is missing from the exported data (this happens for deleted users).
    """
    user = users.get(author_id)
    author_name = user["sortable_name"] if user else NON_EXISTENT_USER_NAME

    channel_key = user_email_channels.get(author_id)
    if channel_key is None:
        return author_name, NON_EXISTENT_CHANNEL_PATH, UNKNOWN_USER_TYPE

    author_email = communication_channels[channel_key]["path"]
    return author_name, author_email, classify_user_type(author_email)


def split_message_body(body: str) -> list[str]:
    """Collapse a message body to one line and wrap it into fixed-size parts."""
    single_line_body = " ".join(body.splitlines())
    escaped_body = single_line_body.replace('"', "'")
    return wrap(escaped_body, width=MAX_BODY_PART_LENGTH, break_long_words=True)


def build_conversation_rows(
    dataset: CanvasDataset,
) -> list[list[Any]]:
    """Join every table and produce one CSV row per (message, body part)."""
    users = index_by_key_id(dataset.users)
    conversations = index_by_key_id(dataset.conversations)
    communication_channels = index_by_key_id(dataset.communication_channels)
    message_recipients = build_message_recipients(
        dataset.conversation_message_participants
    )
    user_email_channels = build_user_email_index(communication_channels)

    local_tz = get_localzone()
    rows: list[list[Any]] = []

    for record in dataset.conversation_messages:
        message_id = record["key"]["id"]
        message = record["value"]

        conversation = conversations.setdefault(message["conversation_id"], {})
        if not conversation.get("subject"):
            conversation["subject"] = NO_SUBJECT_PLACEHOLDER

        created_at = message["created_at"].replace("Z", "+00:00")
        local_created_at = datetime.fromisoformat(created_at).astimezone(local_tz)

        author_name, author_email, user_type = resolve_author(
            message["author_id"], users, user_email_channels, communication_channels
        )

        body_parts = split_message_body(message["body"])
        total_parts = len(body_parts)
        recipients = message_recipients.get(message_id, [])

        for part_index, body_part in enumerate(body_parts, start=1):
            rows.append(
                [
                    message_id,
                    part_index,
                    total_parts,
                    message["conversation_id"],
                    local_created_at.strftime("%Y-%m-%d"),
                    local_created_at.strftime("%H:%M:%S"),
                    local_created_at.strftime("%z"),
                    message["author_id"],
                    user_type,
                    author_name,
                    author_email,
                    conversation["subject"],
                    message["has_attachments"],
                    recipients,
                    body_part,
                ]
            )

    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Match and combine Canvas Data 2 JSON table dumps into a "
        "single, human-readable conversations report."
    )
    parser.add_argument("accounts_filename", help="Path to the Canvas accounts JSON file")
    parser.add_argument("roles_filename", help="Path to the Canvas roles JSON file")
    parser.add_argument("users_filename", help="Path to the users JSON file")
    parser.add_argument(
        "account_users_filename",
        help="Path to the Canvas accounts / users / roles mapping JSON file",
    )
    parser.add_argument("conversations_filename", help="Path to the conversations JSON file")
    parser.add_argument(
        "conversation_messages_filename",
        help="Path to the conversation messages JSON file",
    )
    parser.add_argument(
        "conversation_participants_filename",
        help="Path to the conversation participants JSON file",
    )
    parser.add_argument(
        "conversation_message_participants_filename",
        help="Path to the conversation message participants JSON file",
    )
    parser.add_argument(
        "communication_channels_filename",
        help="Path to the communication channels JSON file",
    )
    parser.add_argument("enrollments_filename", help="Path to the enrollments JSON file")
    return parser.parse_args(argv)


def load_dataset(args: argparse.Namespace) -> CanvasDataset:
    return CanvasDataset(
        accounts=load_json_lines(args.accounts_filename),
        roles=load_json_lines(args.roles_filename),
        users=load_json_lines(args.users_filename),
        account_users=load_json_lines(args.account_users_filename),
        conversations=load_json_lines(args.conversations_filename),
        conversation_messages=load_json_lines(args.conversation_messages_filename),
        conversation_participants=load_json_lines(
            args.conversation_participants_filename
        ),
        conversation_message_participants=load_json_lines(
            args.conversation_message_participants_filename
        ),
        communication_channels=load_json_lines(args.communication_channels_filename),
        enrollments=load_json_lines(args.enrollments_filename),
    )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    dataset = load_dataset(args)
    rows = build_conversation_rows(dataset)

    writer = csv.writer(sys.stdout, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(CSV_COLUMNS)
    writer.writerows(rows)


if __name__ == "__main__":
    main()
