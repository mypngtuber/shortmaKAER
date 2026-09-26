# AI Shorts Maker

A **local Windows desktop application** (Python 3.11+, CustomTkinter) for finding and exporting vertical Shorts. No web server or login. The original video is never sent to Gemini: only the selected SRT, audio, or both are submitted during analysis. FFmpeg processes video locally.

## Install and run on Windows

1. Install Python 3.11+ (64-bit), FFmpeg **with ffprobe and libass/subtitles support**, and 64-bit [VLC media player](https://www.videolan.org/vlc/). Add FFmpeg's `bin` folder to PATH, or select `ffmpeg.exe` in Settings. VLC must match the application's architecture; if VLC is not found, add its installation directory to PATH before starting the app.
2. In PowerShell, from this directory:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python main.py
   ```

3. In Settings, enter a Gemini API key, choose a working model, optionally test the API, select FFmpeg if needed, and Save. The key is stored in the **Windows Credential Manager** via `keyring`; settings (models, retries, FFmpeg path) are stored in `%APPDATA%\AIShortsMaker\settings.json`. No key is written to project JSON or logs.
4. Select a local video and a source mode (SRT, Audio, Audio + SRT). Select the required source files. Choose clip count and minimum/maximum durations. Click **FIND SHORTS**. Results are cached; **Re-analyze** explicitly makes a new request.
5. In results, edit timestamps/title, create a local preview, play/pause/seek/adjust volume/fullscreen with VLC, select shorts, then export. `Shorts/` is created **next to the video**, with MP4s, shifted SRTs when supplied, `project.json`, and `analysis.json`. **Open Project** reopens a saved `project.json` without Gemini.

Audio-only mode does not create captions (no transcription service is called). To burn captions, supply an SRT. Audio files up to 15 MiB are sent inline; larger audio files are temporarily uploaded to the **Gemini Files API** and deleted after analysis (or after a failed attempt). Uploads consume data and may be subject to Gemini file limits. Only audio, never video, is uploaded. SRT and audio must be synchronized with the video for accurate cuts. The list of requested default models includes future model names; unavailable models are skipped in order. Select a model your key can access (for example `gemini-2.5-flash`). Calls are serialized and transient errors are retried with exponential backoff. One analysis call normally returns all candidates; previews/edits/exports do not call Gemini.

## Build Windows executable

Run on **Windows** in the activated virtual environment:

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name "AI Shorts Maker" --collect-all customtkinter --collect-all keyring --collect-all google.genai main.py
```

The result is `dist\AI Shorts Maker.exe`. Install VLC and FFmpeg separately on target machines (or use the FFmpeg path selector). The EXE does not bundle those native executables. For a standalone distribution, test on a clean Windows computer with the same VLC architecture. **Do not build a Windows EXE on Linux**; PyInstaller produces binaries for its host OS.

## Tests

```powershell
python -m unittest discover -s tests -v
```

FFmpeg integration test requires FFmpeg and ffprobe on PATH. Real Gemini requests and VLC UI need a key, network and desktop and are not exercised by automated tests. No test sends video anywhere.
