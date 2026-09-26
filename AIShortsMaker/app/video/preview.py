from pathlib import Path
from app.video.captions import caption_file
from app.video.processor import render


def create_preview(job, short, settings, progress) -> Path:
    folder = Path(job.video).resolve().parent / 'Shorts'
    folder.mkdir(exist_ok=True)
    stem = f'preview_{short.id:02}'
    caption = caption_file(job.srt if job.mode != 'audio' else None, short.start, short.end, folder, stem)
    destination = folder / f'{stem}.mp4'
    render(settings, job.video, short, destination, caption, progress)
    return destination
