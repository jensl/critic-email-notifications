from typing import Sequence

from critic import api


async def get_recipients(
    event: api.reviewevent.ReviewEvent, email_type: str
) -> Sequence[api.user.User]:
    critic = event.critic
    review = await event.review
    candidates = (
        await review.owners | await review.assigned_reviewers | await review.watchers
    )
    recipients = []

    for candidate in candidates:
        if not candidate.email:
            # User has no (or unverified) email address.
            continue
        with critic.asUser(candidate):
            if not await api.usersetting.get(
                critic, "email", "activated", default=False
            ):
                # User has disabled emails altogether.
                continue
            if not await api.usersetting.get(
                critic, "email", "subjectLine." + email_type, default="enabled"
            ):
                # User has disabled this specific type of email.
                continue
        recipients.append(candidate)

    return recipients
