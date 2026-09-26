import re
from pathlib import Path

VIDEO = {'.mp4', '.mov', '.mkv', '.avi', '.webm'}
AUDIO = {'.mp3', '.wav', '.m4a', '.aac', '.flac'}


def require_file(path: str, extensions: set[str]) -> Path:
    file = Path(path).expanduser().resolve()
    if not file.is_file() or file.suffix.lower() not in extensions:
        raise ValueError(f'Please select an existing {", ".join(sorted(extensions))} file.')
    return file


def safe_name(title: str) -> str:
    name = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')[:55]
    return name or 'untitled'


def output_dir(video: str) -> Path:
    directory = Path(video).resolve().parent / 'Shorts'
    directory.mkdir(exist_ok=True)
    return directory
