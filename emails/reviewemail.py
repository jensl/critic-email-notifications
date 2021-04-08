# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2017 the Critic contributors, Opera Software ASA
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.

from __future__ import annotations

import email.message
import logging
import textwrap
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)

from critic import api
from . import types


def indented(level: int, *lines: str) -> Sequence[str]:
    indent = " " * level
    return [indent + line for line in lines]


def wrapped(email: types.ReviewEmail, text: str, *, indent: int = 2):
    return indented(indent, *textwrap.wrap(text, email.line_length - indent))


class ReviewEmail(types.ReviewEmail):
    line_length: int
    separator: str
    parent_message_id: Optional[str]
    message_id: str

    sections: List[str]

    async def create(
        group: types.ReviewEmailGroup,
        to_user: api.user.User,
        email_type: types.ReviewEmailType,
        message_id_prefix: str,
    ) -> ReviewEmail:
        email = ReviewEmail(group, to_user, email_type, message_id_prefix)
        email.line_length, _ = await api.usersetting.get(
            to_user.critic, scope="emails", name="lineLength", default=80
        )
        email.separator = "-" * email.line_length
        return email

    def __init__(
        self,
        group: types.ReviewEmailGroup,
        to_user: api.user.User,
        email_type: types.ReviewEmailType,
        message_id_prefix: str,
    ):
        self.group = group
        self.to_user = to_user
        self.type = email_type
        self.parent_message_id = None
        self.message_id = f"{message_id_prefix}.u{to_user.id}"
        self.sections = []

    def __str__(self) -> str:
        return f"{self.type} mail to {self.to_user.email}"

    @property
    async def header(self) -> str:
        lines = [
            self.separator,
            "This is an automatic message generated by the review at:",
        ]
        review = await self.group.event.review
        for url_prefix in await self.to_user.url_prefixes:
            lines.append(f"  {url_prefix}/r/{review.id}")
        lines.append(self.separator)
        return "\n".join(lines)

    @property
    async def subject(self) -> str:
        review = await self.group.event.review
        fmt, _ = await api.usersetting.get(
            review.critic,
            scope="emails",
            name=f"subjectLine.{self.type}",
            default="[r/%(id)d] %(summary)s",
        )
        branch = await review.branch
        assert branch is not None
        return fmt % {
            "id": review.id,
            "summary": review.summary,
            # "progress": str(review.getReviewState(db)),
            "branch": branch.name,
        }

    @property
    async def body(self) -> str:
        return "\n\n\n".join(
            [await self.header] + self.sections + [f"--{self.group.from_user.name}"]
        )

    def add_section(self, *lines: str, wrap_lines: bool = True) -> None:
        actual_lines = []
        for line in lines:
            if not line or not line[0].isalpha():
                actual_lines.append(line)
            else:
                actual_lines.extend(textwrap.wrap(line, self.line_length))
        self.sections.append("\n".join(actual_lines))

    def add_separator(self) -> None:
        self.sections.append(self.separator)

    async def finish(self) -> email.message.EmailMessage:
        message = email.message.EmailMessage()
        message["From"] = self.group.from_user.name
        message["To"] = self.to_user.name
        message["Subject"] = await self.subject
        message["Message-Id"] = self.message_id
        message.set_content(await self.body)
        return message
