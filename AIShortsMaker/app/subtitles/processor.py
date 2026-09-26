from datetime import timedelta
from pathlib import Path
import srt
from app.utils.timestamps import seconds


def write_segment(entries: list[srt.Subtitle], start: str, end: str, destination: Path) -> bool:
    a, b = seconds(start), seconds(end)
    result = []
    for entry in entries:
        lo = max(entry.start.total_seconds(), a)
        hi = min(entry.end.total_seconds(), b)
        if hi > lo:
            result.append(srt.Subtitle(index=len(result) + 1,
                start=timedelta(seconds=lo - a), end=timedelta(seconds=hi - a), content=entry.content))
    if result:
        destination.write_text(srt.compose(result), encoding='utf-8')
    return bool(result)
