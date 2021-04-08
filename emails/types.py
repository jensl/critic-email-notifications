from __future__ import annotations

from typing import Dict, Literal, Protocol, Any

from critic import api


ReviewEmailType = Literal["newReview", "publishedReview", "updatedReview"]


class ReviewEmail(Protocol):
    line_length: int
    group: ReviewEmailGroup
    to_user: api.user.User
    type: ReviewEmailType

    def add_section(self, *lines: str, wrap_lines: bool = ...) -> None:
        ...


class ReviewEmailGroup(Protocol):
    event: api.reviewevent.ReviewEvent
    from_user: api.user.User

    cache: Dict[str, Any]

    async def generate(
        self, generator: ReviewEmailGenerator, add_review_message_ids: bool = ...
    ) -> None:
        ...


class ReviewEmailGenerator(Protocol):
    async def __call__(self, email: ReviewEmail, /) -> bool:
        ...
