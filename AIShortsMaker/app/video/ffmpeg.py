import json
import os
import shutil
import subprocess
from pathlib import Path
from app.utils.settings import Settings


def executable(settings: Settings) -> str:
    candidate = settings.ffmpeg_path.strip() or shutil.which('ffmpeg')
    if not candidate or not Path(candidate).is_file():
        raise FileNotFoundError('FFmpeg was not found. Please select ffmpeg.exe from Settings.')
    return str(candidate)


def probe_executable(settings: Settings) -> str:
    ffmpeg = Path(executable(settings))
    neighbor = ffmpeg.with_name('ffprobe.exe' if os.name == 'nt' else 'ffprobe')
    result = str(neighbor) if neighbor.is_file() else shutil.which('ffprobe')
    if not result:
        raise FileNotFoundError('ffprobe was not found. Install FFmpeg with ffprobe in the same folder.')
    return result


def test(settings: Settings) -> str:
    proc = subprocess.run([executable(settings), '-version'], capture_output=True, text=True, timeout=10,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if proc.returncode:
        raise RuntimeError('FFmpeg could not start. Check its path in Settings.')
    return proc.stdout.splitlines()[0]


def video_length(settings: Settings, video: str) -> float:
    proc = subprocess.run([probe_executable(settings), '-v', 'error', '-show_entries', 'format=duration',
                           '-of', 'json', video], capture_output=True, text=True, timeout=30,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if proc.returncode:
        raise RuntimeError('Unable to read video duration with ffprobe.')
    length = float(json.loads(proc.stdout)['format']['duration'])
    if length <= 0:
        raise ValueError('Video duration is invalid.')
    return length
