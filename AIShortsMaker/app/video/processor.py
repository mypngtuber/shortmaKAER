import os
import subprocess
from pathlib import Path
from app.models.shorts import Short
from app.utils.timestamps import seconds
from app.video.ffmpeg import executable


def render(settings, video: str, short: Short, destination: Path, caption: Path | None, progress):
    # Relative caption names avoid FFmpeg filter escaping problems with Windows drive letters.
    filters = ["scale=1080:1920:force_original_aspect_ratio=increase", "crop=1080:1920"]
    if caption:
        filters.append(f"subtitles={caption.name}:force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=140'")
    temporary = destination.with_name(destination.stem + '.partial.mp4')
    command = [executable(settings), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
               '-ss', short.start, '-i', video, '-t', f'{seconds(short.end)-seconds(short.start):.3f}',
               '-vf', ','.join(filters), '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
               '-progress', 'pipe:1', '-nostats', str(temporary)]
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        with subprocess.Popen(command, cwd=destination.parent, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, creationflags=flags) as proc:
            for line in proc.stdout:
                if line.startswith('out_time_us='):
                    try:
                        progress(min(1., int(line.split('=', 1)[1]) / (1000000 * short.duration)))
                    except ValueError:
                        pass
            error = proc.stderr.read()[-1200:]
            if proc.wait() != 0:
                raise RuntimeError('FFmpeg failed to render the video. Check that your FFmpeg build supports subtitles/libass and H.264. ' + error)
        os.replace(temporary, destination)
        progress(1.)
    finally:
        temporary.unlink(missing_ok=True)
