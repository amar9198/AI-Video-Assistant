import re
import os
import tempfile
import time
import shutil
import yt_dlp
from pydub import AudioSegment
import subprocess
from pathlib import Path

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)




def ensure_deno() -> str:
    install_dir = Path.home() / ".deno"
    deno_path = install_dir / "bin" / "deno"

    # Already installed from an earlier run
    if deno_path.is_file():
        return str(deno_path)

    found = shutil.which("deno")
    if found:
        return found

    env = os.environ.copy()
    env["DENO_INSTALL"] = str(install_dir)
    try:
        subprocess.run(
            ["sh", "-c", "curl -fsSL https://deno.land/install.sh | sh"],
            check=True, timeout=180, env=env,
        )
    except Exception as exc:
        raise RuntimeError(f"Deno installation failed: {exc}") from exc

    if not deno_path.is_file():
        raise RuntimeError(f"Deno was not installed at {deno_path}.")
    return str(deno_path)


def _video_id(url: str):
    m = re.search(r"(?:youtu\.be/|v=|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def _build_opts(deno_path: str, clients: list, cookies):
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "js_runtimes": {"deno": {"path": deno_path}},
        "remote_components": {"ejs:npm"},
        "extractor_args": {"youtube": {"player_client": clients}},
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "wav"}
        ],
        "postprocessor_args": {
            "ffmpegextractaudio": ["-ac", "1", "-ar", "16000"]
        },
    }
    if cookies:
        opts["cookiefile"] = cookies
    return opts




def _cleanup_old_files(max_age_hours: int = 2) -> None:
    cutoff = time.time() - max_age_hours * 3600

    for name in os.listdir(DOWNLOAD_DIR):
        path = os.path.join(DOWNLOAD_DIR, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def _cookie_file():
    """Get optional YouTube cookies from environment variables."""
    path = os.getenv("YT_COOKIES_FILE")
    if path and os.path.isfile(path):
        return path

    content = os.getenv("YT_COOKIES")
    if content:
        tmp = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        return tmp

    return None





def download_youtube_audio(url: str) -> str:
    _cleanup_old_files()
    print("yt-dlp version:", yt_dlp.version.__version__)

    # Reuse audio if this video was downloaded recently
    vid = _video_id(url)
    if vid:
        cached = os.path.join(DOWNLOAD_DIR, f"{vid}.wav")
        if os.path.isfile(cached) and os.path.getsize(cached) > 0:
            print("Using cached audio:", cached)
            return cached

    deno_path = ensure_deno()
    cookies = _cookie_file()

    # (player clients, use cookies?) -- tried in order
    attempts = [
        (["web_embedded", "tv"], True),
        (["web_embedded", "tv"], False),
        (["android_vr"], False),
        (["tv"], False),
    ]

    last_error = None
    for clients, use_cookies in attempts:
        if use_cookies and not cookies:
            continue
        print(f"Trying clients={clients} cookies={use_cookies}")
        opts = _build_opts(deno_path, clients, cookies if use_cookies else None)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            if not info:
                raise RuntimeError("yt-dlp returned no video information.")
            wav_path = os.path.join(DOWNLOAD_DIR, f"{info['id']}.wav")
            if os.path.isfile(wav_path) and os.path.getsize(wav_path) > 0:
                return wav_path
            raise FileNotFoundError(f"WAV not found: {wav_path}")
        except Exception as e:
            last_error = e
            print(f"Attempt failed: {type(e).__name__}: {e}")

    raise RuntimeError(
        "Could not download YouTube audio. YouTube may be blocking this "
        "server. Upload the audio/video file instead. "
        f"Details: {type(last_error).__name__}: {last_error}"
    ) from last_error




def convert_to_wav(input_path: str) -> str:
    """Convert an audio/video file to mono, 16 kHz WAV."""
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = os.path.splitext(input_path)[0] + "_converted.wav"

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")

    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 5) -> list:
    """Split WAV audio into chunks for transcription."""
    if chunk_minutes <= 0:
        raise ValueError("chunk_minutes must be greater than zero.")

    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start:start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    if not chunks:
        raise ValueError("No audio chunks were created.")

    return chunks


def process_input(source: str) -> list:
    source = source.strip()

    if not source:
        raise ValueError("Please provide a YouTube URL or audio/video file.")

    if source.startswith(("http://", "https://")):
        print("Detected URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = source

    wav_path = convert_to_wav(wav_path)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")

    return chunks
