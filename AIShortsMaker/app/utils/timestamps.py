import re

_PATTERN = re.compile(r"^(\d{2,}):(\d{2}):(\d{2})[.,](\d{3})$")


def seconds(value: str) -> float:
    match = _PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Invalid timestamp: {value}")
    hours, minutes, secs, millis = map(int, match.groups())
    if minutes >= 60 or secs >= 60:
        raise ValueError(f"Invalid timestamp: {value}")
    return hours * 3600 + minutes * 60 + secs + millis / 1000


def stamp(value: float, separator: str = '.') -> str:
    if value < 0:
        raise ValueError('Negative timestamp')
    ms = round(value * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02}{separator}{ms:03}'
