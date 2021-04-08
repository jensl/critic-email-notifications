from typing import Tuple

from critic import api

from .types import ReviewEmail


async def changed_lines_per_file(email: ReviewEmail, rfcs, *, indent="  "):
    counts_per_file: dict[api.file.File, Tuple[int, int]] = {}

    for rfc in rfcs:
        file = await rfc.file
        deleted, inserted = counts_per_file.get(file, (0, 0))
        deleted += rfc.deleted_lines
        inserted += rfc.inserted_lines
        counts_per_file[file] = (deleted, inserted)

    max_path_length = max(len(file.path) for file in counts_per_file)
    max_deleted = max(deleted for deleted, _ in counts_per_file.values())
    deleted_width = len(str(max_deleted))
    max_inserted = max(inserted for _, inserted in counts_per_file.values())
    inserted_width = len(str(max_inserted))

    counts_fmt = f"  -%{deleted_width}d/+%{inserted_width}d"
    path_width = min(
        email.line_length - (len(indent) + len(counts_fmt % (0, 0))), max_path_length
    )
    path_fmt = f"%-{path_width}s"

    def pad_path(path):
        padded = path_fmt % path
        if len(padded) > path_width:
            left = (path_width - 5) / 2
            right = (path_width - 5) - left
            return padded[:left] + " ... " + padded[-right:]
        return padded

    lines = []
    for file, counts in sorted(counts_per_file.items(), key=lambda item: item[0].path):
        lines.append(indent + (path_fmt % file.path) + (counts_fmt % counts))
    return lines
