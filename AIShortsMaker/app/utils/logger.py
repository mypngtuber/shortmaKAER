from datetime import datetime


def log_line(message: str) -> str:
    return f'[{datetime.now():%H:%M:%S}] {message}'
