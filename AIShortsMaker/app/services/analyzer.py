from app.gemini.manager import run
from app.gemini.prompts import request_prompt
from app.models.shorts import Analysis, Job
from app.subtitles.parser import normalized_srt, parse_srt
from app.utils.timestamps import seconds


def select_candidates(analysis: Analysis, count: int, minimum: int, maximum: int, length: float):
    result = []
    for short in analysis.shorts:
        a, b = seconds(short.start), seconds(short.end)
        if a < 0 or b > length + 0.05 or not minimum <= b - a <= maximum:
            continue
        if any(max(0, min(b, seconds(x.end)) - max(a, seconds(x.start))) > min(b-a, x.duration) * .2
               or short.title.strip().lower() == x.title.strip().lower() for x in result):
            continue
        result.append(short.model_copy(update={'id': len(result) + 1}))
        if len(result) >= count:
            break
    return result


def analyze(job: Job, settings, api_key: str, length: float, status):
    text = normalized_srt(parse_srt(job.srt)) if job.mode != 'audio' else None
    audio = job.audio if job.mode != 'srt' else None
    raw = run(api_key, settings, request_prompt(job.count, job.minimum, job.maximum, length, job.mode), text, audio, status)
    analysis = Analysis.model_validate_json(raw)
    status(f'{len(analysis.shorts)} candidates found')
    chosen = select_candidates(analysis, job.count, job.minimum, job.maximum, length)
    if not chosen:
        raise ValueError('Gemini returned no usable clips within the requested duration and video length.')
    return analysis, chosen
