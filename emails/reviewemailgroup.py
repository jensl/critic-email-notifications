import logging
from datetime import datetime
from typing import Any, Dict, List, TypedDict

logger = logging.getLogger(__name__)

from critic import api
from critic import pubsub

from . import types
from .getrecipients import get_recipients
from .reviewemail import ReviewEmail


class ReviewMessageIdValue(TypedDict):
    review: api.review.Review
    user: api.user.User
    message_id: str


async def generate_message_id_prefix(event: api.reviewevent.ReviewEvent) -> str:
    review = await event.review

    timestamp = event.timestamp.strftime("%Y%m%d%H%M%S")
    timestamp_us = "%06d" % event.timestamp.microsecond

    return f"{timestamp}.{timestamp_us}.r{review.id}.e{event.id}"


class ReviewEmailGroup:
    email_type: types.ReviewEmailType
    emails: List[ReviewEmail]
    parent_message_ids: Dict[api.user.User, str]
    reviewmessageids_values: List[ReviewMessageIdValue]
    cache: Dict[str, Any]

    def __init__(
        self,
        event: api.reviewevent.ReviewEvent,
        from_user: api.user.User,
        email_type: types.ReviewEmailType,
    ):
        self.event = event
        self.from_user = from_user
        self.email_type = email_type
        self.emails = []
        self.parent_message_ids = {}  # { user => str }
        self.reviewmessageids_values = []
        self.cache = {}

    async def generate(
        self,
        generator: types.ReviewEmailGenerator,
        add_review_message_ids: bool = False,
    ) -> None:
        messsage_id_prefix = await generate_message_id_prefix(self.event)
        recipients = await get_recipients(self.event, self.email_type)

        for to_user in recipients:
            email = await ReviewEmail.create(
                self, to_user, self.email_type, messsage_id_prefix
            )

            email.parent_message_id = self.parent_message_ids.get(to_user)
            logger.debug("generating %s", email)

            if await generator(email):
                self.emails.append(email)
            else:
                logger.debug("  - skipped by generator")

    # async def ensure_parent_message_ids(self):
    #     from .handlepublished import generate

    #     review = await self.event.review

    #     async with self.event.critic.query(
    #         """SELECT uid, messageid
    #              FROM reviewmessageids
    #             WHERE review={review}""",
    #         review=review,
    #     ) as result:
    #         message_ids = dict(await result.all())
    #         logger.debug("message_ids: %r", message_ids)

    #     needs_placeholder = set()
    #     recipients = await get_recipients(self.event, self.email_type)
    #     for to_user in recipients:
    #         if to_user.id in message_ids:
    #             self.parent_message_ids[to_user] = message_ids[to_user.id]
    #         else:
    #             needs_placeholder.add(to_user)
    #     for to_user in needs_placeholder:
    #         mail = ReviewMail(self, to_user, "newishReview")
    #         await mail.initialize()
    #         logger.debug("generating %s", mail)
    #         if (await generate(mail)) is False:
    #             logger.debug("  - skipped by generator")
    #         else:
    #             queued_mail = mailutils.queueMail(
    #                 self.from_user,
    #                 to_user,
    #                 recipients,
    #                 await mail.subject,
    #                 await mail.body,
    #             )
    #             self.emails.append(queued_mail)
    #             self.reviewmessageids_values.append(
    #                 dict(
    #                     review=review.id,
    #                     user=to_user.id,
    #                     message_id=queued_mail.message_id,
    #                 )
    #             )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            critic = self.event.critic
            messages = [await email.finish() for email in self.emails]
            await pubsub.publish(critic, "EmailNotifications", *messages)
