import random
import re
import threading
import time
from app.gemini.client import analyze_once, prepare_audio
from app.utils.settings import Settings

_LOCK = threading.Lock()


def _temporary(exc: Exception) -> bool:
    code = getattr(exc, 'code', None)
    if code in (429, 500, 502, 503, 504, 408):
        return True
    return isinstance(exc, (TimeoutError, ConnectionError)) or bool(re.search(r'\b(429|500|502|503|504|timeout|temporarily unavailable)\b', str(exc), re.I))


def run(api_key: str, settings: Settings, prompt: str, srt_text: str | None, audio: str | None, status) -> str:
    models = list(dict.fromkeys([settings.primary_model, *settings.fallback_models]))
    with _LOCK:  # no simultaneous Gemini requests within this process
        status('Preparing audio for Gemini' if audio else 'Analyzing SRT')
        prepared, remote = prepare_audio(api_key, audio)
        try:
            for model in models:
                for attempt in range(settings.retry_attempts):
                    status(f'Using {model} (attempt {attempt + 1}/{settings.retry_attempts})')
                    try:
                        return analyze_once(api_key, model, prompt, srt_text, prepared)
                    except Exception as exc:
                        # Never put exception details in UI/logs; SDK exceptions may include request metadata.
                        if getattr(exc, 'code', None) in (400, 401, 403) or re.search(r'API.key.*invalid|invalid.*API.key', str(exc), re.I):
                            raise ValueError('Gemini API key is invalid or access is denied.') from None
                        if not _temporary(exc):
                            status(f'{model} is unavailable; trying next model')
                            break
                        if attempt + 1 < settings.retry_attempts:
                            delay = min(2 ** (attempt + 1) + random.uniform(0, 0.5), 60)
                            status('Gemini is temporarily unavailable. Retrying...')
                            time.sleep(delay)
                status(f'{model} failed; switching to fallback')
            raise RuntimeError('All configured Gemini models failed. Please try again later or check your API limits.')
        finally:
            if remote:
                client, name = remote
                try:
                    client.files.delete(name=name)
                except Exception:
                    status('Could not remove temporary Gemini audio upload; remove it from your Gemini files if needed.')
                finally:
                    client.close()
