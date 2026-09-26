from app.utils.files import output_dir, safe_name
from app.video.captions import caption_file
from app.video.processor import render


def export_one(job, short, settings, progress):
    folder = output_dir(job.video)
    stem = f'short_{short.id:02}_{safe_name(short.title)}'
    caption = caption_file(job.srt if job.mode != 'audio' else None, short.start, short.end, folder, stem)
    destination = folder / f'{stem}.mp4'
    render(settings, job.video, short, destination, caption, progress)
    return destination
