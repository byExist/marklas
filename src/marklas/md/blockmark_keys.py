"""Param-key names shared by the block-mark encode (`block_marks_params` +
media renderers) and decode (`parse_block_marks`) sides, so the two can't
silently disagree — a mismatched key drops the mark on round-trip with no error.

These are the MD-`params` layer keys only; the ADF JSON layer has its own
strings that coincide for some marks (e.g. `"fontSize"`) but are a separate
format, intentionally not shared here.
"""

from __future__ import annotations

ALIGN = "align"
INDENT = "indent"
BREAKOUT_MODE = "breakoutMode"
BREAKOUT_WIDTH = "breakoutWidth"
DATA_CONSUMER_SOURCES = "dataConsumerSources"
BORDER_SIZE = "borderSize"
BORDER_COLOR = "borderColor"
FONT_SIZE = "fontSize"
UNKNOWN_MARKS = "unknownMarks"
