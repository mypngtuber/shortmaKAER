import json
import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field

DEFAULT_MODELS = ['gemini-3.7-flash', 'gemini-3.8-flash', 'gemini-3.5-flash',
                  'gemini-3-flash-preview', 'gemini-3.1-flash-lite',
                  'gemini-3.1-flash-lite-preview', 'gemini-2.5-flash', 'gemini-2.5-flash-lite']


class Settings(BaseModel):
    primary_model: str = 'gemini-3.6-flash'
    fallback_models: list[str] = Field(default_factory=lambda: DEFAULT_MODELS.copy())
    custom_models: list[str] = Field(default_factory=list)
    retry_attempts: int = Field(default=4, ge=1, le=8)
    ffmpeg_path: str = ''
    output_format: str = '9:16'


def settings_dir() -> Path:
    base = os.environ.get('APPDATA') if sys.platform == 'win32' else os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
    return Path(base) / 'AIShortsMaker'


def load_settings() -> Settings:
    path = settings_dir() / 'settings.json'
    try:
        return Settings.model_validate_json(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return Settings()


def save_settings(settings: Settings) -> None:
    folder = settings_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'settings.json'
    path.write_text(settings.model_dump_json(indent=2), encoding='utf-8')


def load_key() -> str:
    # Windows Credential Manager via keyring: key is not stored in settings.json.
    import keyring
    return keyring.get_password('AIShortsMaker', 'gemini_api_key') or ''


def save_key(key: str) -> None:
    import keyring
    keyring.set_password('AIShortsMaker', 'gemini_api_key', key.strip())
