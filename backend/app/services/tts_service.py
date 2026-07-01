import edge_tts
import uuid
import os

AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)


async def generate_speech(text: str):
    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    communicate = edge_tts.Communicate(
        text=text,
        voice="en-IN-NeerjaNeural"
    )

    await communicate.save(filepath)

    return f"/static/audio/{filename}"