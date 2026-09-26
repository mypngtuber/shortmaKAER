from pathlib import Path
from app.subtitles.parser import parse_srt
from app.subtitles.processor import write_segment


def caption_file(srt_path: str | None, start: str, end: str, folder: Path, stem: str) -> Path | None:
    if not srt_path:
        return None
    path = folder / f'{stem}.srt'
    if write_segment(parse_srt(srt_path), start, end, path):
        return path
    return None
