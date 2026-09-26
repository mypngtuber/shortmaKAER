from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.utils.timestamps import seconds


class Short(BaseModel):
    id: int = Field(ge=1)
    start: str
    end: str
    duration: float = Field(gt=0)
    title: str = Field(min_length=1, max_length=160)
    hook: str = ''
    reason: str = ''

    @field_validator('start', 'end')
    @classmethod
    def valid_stamp(cls, value: str) -> str:
        seconds(value)
        return value.replace(',', '.')

    @model_validator(mode='after')
    def valid_span(self):
        actual = seconds(self.end) - seconds(self.start)
        if actual <= 0 or abs(actual - self.duration) > 1.5:
            raise ValueError('Invalid duration or reversed timestamps')
        return self


class Analysis(BaseModel):
    shorts: list[Short]


class Job(BaseModel):
    model_config = ConfigDict(extra='ignore')
    video: str
    srt: str | None = None
    audio: str | None = None
    mode: str
    count: int = Field(ge=1, le=30)
    minimum: int = Field(ge=1)
    maximum: int = Field(ge=1)
    shorts: list[Short] = []

    @model_validator(mode='after')
    def valid_job(self):
        if self.minimum > self.maximum:
            raise ValueError('Minimum duration must not exceed maximum')
        if self.mode not in ('srt', 'audio', 'audio_srt'):
            raise ValueError('Invalid source mode')
        if not Path(self.video).is_file():
            raise ValueError('Video file was not found')
        for path in ([self.srt] if self.mode == 'srt' else [self.audio] if self.mode == 'audio' else [self.audio, self.srt]):
            if not path or not Path(path).is_file():
                raise ValueError('Required content source file was not found')
        return self
