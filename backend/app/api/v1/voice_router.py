from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
import tempfile
import os

from app.integrations.speech_to_text import transcribe_audio
from app.database.dependencies import get_db
from app.voice.call_flow import handle_call


router = APIRouter()


@router.post("/voice/chat")
async def voice_chat(
    file: UploadFile = File(...),
    session_id: str = "voice_session",
    db: Session = Depends(get_db),
):
    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        transcript = transcribe_audio(temp_path)

        response = handle_call(
            message=transcript,
            session_id=session_id,
            db=db,
        )
        from app.services.tts_service import generate_speech

        audio_url = await generate_speech(
        response["message"]
)

        response["audio_url"] = audio_url

        return {
            "transcript": transcript,
            "response": response,
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)