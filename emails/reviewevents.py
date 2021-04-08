import logging

logger = logging.getLogger(__name__)

from critic import api
from critic import pubsub
from critic.extension import Message, Subscription

from .handlepublished import handle_published


async def handle_reviewevent(
    critic: api.critic.Critic, event: api.reviewevent.ReviewEvent
) -> None:
    if event.type == "published":
        await handle_published(critic, event)
    else:
        logger.debug("review event not handled: %r", event)


async def main(critic: api.critic.Critic, subscription: Subscription) -> None:
    async for message_handle in subscription.messages:
        async with message_handle as message:
            payload = message.payload

            if not isinstance(payload, api.transaction.protocol.CreatedReviewEvent):
                logger.debug("payload not handled: %r", payload)
                continue

            try:
                event = api.reviewevent.fetch(critic, payload.object_id)
            except api.reviewevent.InvalidId:
                logger.error("invalid payload id: %r", payload)
            else:
                await handle_reviewevent(critic, event)
