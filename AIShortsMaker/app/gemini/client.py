import mimetypes
import time
from pathlib import Path
from google import genai
from google.genai import types
from app.gemini.prompts import SYSTEM_PROMPT
from app.gemini.schemas import RESPONSE_SCHEMA


def audio_mime(file: Path) -> str:
    return {'.flac': 'audio/flac', '.aac': 'audio/aac'}.get(file.suffix.lower(), mimetypes.guess_type(file.name)[0] or 'audio/mpeg')


def prepare_audio(api_key: str, audio: str | None):
    """Return (inline path or Gemini file part, temporary remote file handle).

    Video is never accepted by this function. Large audio is removed after analysis.
    """
    if not audio:
        return None, None
    file = Path(audio)
    if file.suffix.lower() not in {'.mp3', '.wav', '.m4a', '.aac', '.flac'}:
        raise ValueError('Please select a supported audio file.')
    if file.stat().st_size <= 15 * 1024 * 1024:
        return audio, None
    client = genai.Client(api_key=api_key)
    uploaded = None
    try:
        uploaded = client.files.upload(file=str(file), config={'mime_type': audio_mime(file)})
        for _ in range(30):
            state = getattr(uploaded.state, 'name', str(uploaded.state))
            if state == 'ACTIVE':
                return types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type), (client, uploaded.name)
            if state == 'FAILED':
                raise RuntimeError('Gemini could not process the audio file.')
            time.sleep(2)
            uploaded = client.files.get(name=uploaded.name)
        raise TimeoutError('Gemini audio processing timed out.')
    except Exception:
        if uploaded is not None:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass
        client.close()
        raise


def analyze_once(api_key: str, model: str, prompt: str, srt_text: str | None, audio: str | types.Part | None) -> str:
    # There is deliberately no video parameter in this API boundary.
    parts = [types.Part.from_text(text=prompt)]
    if srt_text:
        parts.append(types.Part.from_text(text='Timestamped SRT:\n' + srt_text))
    if isinstance(audio, types.Part):
        parts.append(audio)
    elif audio:
        file = Path(audio)
        parts.append(types.Part.from_bytes(data=file.read_bytes(), mime_type=audio_mime(file)))
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(model=model, contents=[types.Content(role='user', parts=parts)],
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, response_mime_type='application/json',
                response_json_schema=RESPONSE_SCHEMA, temperature=0.35))
        if not response.text:
            raise ValueError('Gemini returned an empty response.')
        return response.text
    finally:
        client.close()
