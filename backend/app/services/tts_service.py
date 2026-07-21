from __future__ import annotations

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"
AUDIO_DIR = BACKEND_DIR / "static" / "audio"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)

loaded = load_dotenv(
    dotenv_path=ENV_FILE,
    override=True,
)

print("ElevenLabs env file:", ENV_FILE)
print("Env file exists:", ENV_FILE.exists())
print("Dotenv loaded:", loaded)
print(
    "ElevenLabs key available:",
    bool(os.getenv("ELEVENLABS_API_KEY")),
)

API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

if API_KEY:
    API_KEY = API_KEY.strip()

if VOICE_ID:
    VOICE_ID = VOICE_ID.strip()

client = ElevenLabs(api_key=API_KEY) if API_KEY else None


async def generate_speech(text: str) -> str:
    if not API_KEY or client is None:
        raise RuntimeError(
            f"ELEVENLABS_API_KEY was not loaded from {ENV_FILE}"
        )

    if not VOICE_ID:
        raise RuntimeError(
            f"ELEVENLABS_VOICE_ID was not loaded from {ENV_FILE}"
        )

    if not text or not text.strip():
        raise ValueError("Text is required for speech generation.")

    filename = f"{uuid.uuid4()}.mp3"
    filepath = AUDIO_DIR / filename

    try:
        audio = client.text_to_speech.convert(
            voice_id=VOICE_ID,
            text=text.strip(),
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128",
        )

        with filepath.open("wb") as audio_file:
            for chunk in audio:
                if chunk:
                    audio_file.write(chunk)

        if not filepath.exists() or filepath.stat().st_size == 0:
            raise RuntimeError(
                "ElevenLabs returned no audio data."
            )

        return f"/static/audio/{filename}"

    except Exception as exc:
        if filepath.exists():
            filepath.unlink()

        raise RuntimeError(
            f"ElevenLabs speech generation failed: {exc}"
        ) from exc