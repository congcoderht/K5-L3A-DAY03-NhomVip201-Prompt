---
name: merge_sources
track: team
kind: local_transform
provider: local
requires_env: []
inputs: [items, dedupe_by, max_items, prefer_source_diversity]
outputs: [items, original_count, returned_count, duplicates_removed, invalid_items_skipped, source_count]
side_effect: false
---
# merge_sources

Normalizes, deduplicates, and optionally diversifies research items that have
already been returned by tools such as `lookup`, `social_search`, `timeline`,
or `papers`.

Use this tool after research data exists and before `format` when duplicate or
over-represented sources need cleanup. It does not search the web, open URLs,
fact-check claims, summarize content, or format a digest.

URL deduplication removes fragments and common tracking parameters, normalizes
the host, and treats `www.example.com/x/` as the same source as
`example.com/x`. When duplicate items contain different fields, the richer item
is retained and missing fields are filled from the other copy.

`dedupe_by` accepts `auto`, `url`, or `title`. `max_items` must be an integer
from 1 to 50. With `prefer_source_diversity=true`, results are interleaved by
source before the limit is applied.
