import hashlib
import json
import os
from pathlib import Path
from app.models.shorts import Analysis, Job
from app.utils.files import output_dir


def signature(job: Job) -> str:
    h = hashlib.sha256()
    h.update(json.dumps({'video': str(Path(job.video).resolve()), 'mode': job.mode, 'count': job.count,
                         'minimum': job.minimum, 'maximum': job.maximum}, sort_keys=True).encode())
    video = Path(job.video).stat()
    h.update(f'{video.st_size}:{video.st_mtime_ns}'.encode())
    for file in (job.srt if job.mode != 'audio' else None, job.audio if job.mode != 'srt' else None):
        if file:
            with open(file, 'rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block)
    return h.hexdigest()


def _save(path: Path, payload: dict):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def save_project(job: Job):
    _save(output_dir(job.video) / 'project.json', job.model_dump())


def load_project(path: str) -> Job:
    return Job.model_validate_json(Path(path).read_text(encoding='utf-8'))


def save_analysis(job: Job, analysis: Analysis, selected):
    folder = output_dir(job.video)
    _save(folder / 'analysis.json', {'signature': signature(job), 'candidates': analysis.model_dump(),
                                     'selected': [x.model_dump() for x in selected]})
    job.shorts = list(selected)
    save_project(job)


def update_selected(job: Job):
    path = output_dir(job.video) / 'analysis.json'
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data['signature'] == signature(job):
            data['selected'] = [short.model_dump() for short in job.shorts]
            _save(path, data)
    except (ValueError, KeyError, OSError):
        pass


def cached_analysis(job: Job):
    path = output_dir(job.video) / 'analysis.json'
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data['signature'] == signature(job):
            return Analysis.model_validate(data['candidates']), Analysis.model_validate({'shorts': data['selected']}).shorts
    except (ValueError, KeyError, OSError):
        pass
    return None
