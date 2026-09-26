from pathlib import Path
import srt


def parse_srt(path: str) -> list[srt.Subtitle]:
    try:
        content = Path(path).read_text(encoding='utf-8-sig')
        entries = list(srt.parse(content, ignore_errors=False))
        if not entries or any(x.end <= x.start for x in entries):
            raise ValueError('No valid subtitles')
        return entries
    except (UnicodeError, OSError, ValueError) as exc:
        raise ValueError('Invalid SRT file.') from exc


def normalized_srt(entries: list[srt.Subtitle]) -> str:
    return srt.compose(entries)
