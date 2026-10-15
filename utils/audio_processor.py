import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import yt_dlp
from pydub import AudioSegment

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def ensure_deno() -> str:
    """Find Deno, then Node.js, or install Deno if neither is available."""
    install_dir = Path.home() / ".deno"
    deno_path = install_dir / "bin" / "deno"

    if deno_path.is_file():
        return str(deno_path)

    found = shutil.which("deno")
    if found:
        return found

    # Node.js is available on Streamlit Cloud through packages.txt and is
    # also supported by yt-dlp's JavaScript challenge solver.
    found = shutil.which("node")
    if found:
        return found

    env = os.environ.copy()
    env["DENO_INSTALL"] = str(install_dir)
    try:
        subprocess.run(
            ["sh", "-c", "curl -fsSL https://deno.land/install.sh | sh"],
            check=True, timeout=180, env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            "No JavaScript runtime was found. Install Deno or Node.js."
        ) from exc

    if not deno_path.is_file():
        raise RuntimeError(f"Deno was not installed at {deno_path}.")
    return str(deno_path)


def _video_id(url: str):
    m = re.search(r"(?:youtu\.be/|v=|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


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


def _build_opts(deno_path: str, client: str, cookies):
    runtime_name = "node" if Path(deno_path).stem.lower() == "node" else "deno"
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
        "js_runtimes": {runtime_name: {"path": deno_path}},
        "remote_components": {"ejs:npm"},
        "extractor_args": {"youtube": {"player_client": [client]}},
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.youtube.com/",
        },
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "wav"}
        ],
        "postprocessor_args": {
            "ffmpegextractaudio": ["-ac", "1", "-ar", "16000"]
        },
    }
    if cookies:
        opts["cookiefile"] = cookies

    proxy = os.getenv("YT_PROXY")
    if proxy:
        opts["proxy"] = proxy

    return opts


def _player_clients() -> list[str]:
    """Return clients in deployment-configurable order."""
    configured = os.getenv("YT_PLAYER_CLIENTS", "")
    if configured.strip():
        clients = [client.strip() for client in configured.split(",")]
        clients = [client for client in clients if client]
        if clients:
            return clients

    # These clients currently avoid the embedded/TV clients' frequent
    # PO-token and bot-check failures on hosted servers.
    return ["web", "web_safari", "mweb", "ios"]


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

    # Try public clients first. A browser cookie export can become invalid
    # when YouTube rotates it, so it is only used as an optional fallback.
    attempts = [
        (client, False)
        for client in _player_clients()
    ]
    if cookies:
        attempts.extend((client, True) for client in _player_clients())

    errors = []
    cookies_invalid = False
    for round_no in range(2):
        for client, use_cookies in attempts:
            if use_cookies and (not cookies or cookies_invalid):
                continue
            print(
                f"Trying client={client} cookies={use_cookies} "
                f"(round {round_no + 1})"
            )
            opts = _build_opts(
                deno_path, client, cookies if use_cookies else None
            )
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
                if use_cookies and "cookies are no longer valid" in str(e).lower():
                    cookies_invalid = True
                msg = (
                    f"{client}/cookies={use_cookies}: "
                    f"{type(e).__name__}: {str(e)[:150]}"
                )
                errors.append(msg)
                print("Attempt failed:", msg)
        time.sleep(3)

    raise RuntimeError(
        "Could not download YouTube audio. YouTube may be blocking this "
        "server. Remove expired YT_COOKIES or configure YT_PROXY with a "
        "trusted residential proxy. Upload the audio/video file instead.\n"
        + "\n".join(errors[-4:])
    )


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