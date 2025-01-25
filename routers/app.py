import glob
import os
import subprocess
from tempfile import TemporaryDirectory
from typing import List

from fastapi import APIRouter, HTTPException, Response, UploadFile
from music21 import converter, midi, stream
from PIL import Image
from pydantic import BaseModel

import utils.connections as conn


router = APIRouter()


class SignUpRequest(BaseModel):
    username: str
    hashed_password: str


@router.post("/sign_up")
async def add_user(credentials: SignUpRequest):
    query = """
    INSERT INTO users (username, hashed_password)
    VALUES ($1, $2);
    """
    await conn.execute_query(query, credentials.username, credentials.hashed_password)


@router.post("/check_username")
async def get_all_usernames(username: str):
    query = """
    SELECT TRUE
    FROM users
    WHERE username = $1;
    """
    result = await conn.execute_query(query, username)
    return {"validity": not bool(result)}


class LoginRequest(BaseModel):
    username: str
    hashed_password: str


@router.post("/login")
async def login_user(credentials: LoginRequest):
    query = """
    SELECT id, username
    FROM users
    WHERE username = $1 AND hashed_password = $2;
    """
    result = await conn.execute_query(query, credentials.username, credentials.hashed_password)

    if not result:
        return {"success": False, "user_id": None, "username": None}

    return {"success": True, "user_id": result[0]["id"], "username": result[0]["username"]}


@router.post("/process_music")
async def process_music(files: List[UploadFile]):
    with TemporaryDirectory() as temp_dir:
        images = []
        for file_ in files:
            file_path = f"{temp_dir}/{file_.filename}"
            with open(file_path, "wb") as f:
                content = await file_.read()
                f.write(content)

            try:
                img = Image.open(file_path)
            except Exception:
                raise HTTPException(status_code=422, detail=f"One or more images are invalid")

            dpi = img.info.get("dpi", (72, 72))
            if dpi[0] < 290 or dpi[1] < 290:
                raise HTTPException(status_code=400, detail=f"Image resolution too low. Detected DPI: {int(max(dpi))}")

            images.append(file_path)

        # Step 1: Use OMR tool to convert images to MusicXML
        # Example: Audiveris CLI (ensure Audiveris is installed)
        subprocess.run(["audiveris", "-batch", "-transcribe", "-export", "-output", temp_dir] + sorted(images), check=True)
        print("Images successfully converted to MusicXML")

        # Combine into one file
        mxl_files = glob.glob(os.path.join(temp_dir, "**", "*.mxl"), recursive=True)
        print(mxl_files)

        if len(mxl_files) < len(files):
            raise HTTPException(status_code=422, detail=f"One or more images are invalid")

        combined_score = stream.Score()
        for mxl_file in mxl_files:
            print(f"Processing file: {mxl_file}")
            try:
                score = converter.parse(mxl_file)
                if not score.isWellFormedNotation():
                    print(f"Warning: {mxl_file} is not well-formed and will be skipped.")
                    continue
                combined_score.append(score)
            except Exception as e:
                print(f"Error parsing {mxl_file}: {e}")
                continue

        # Write the combined score to an output .mxl file
        combined_score.write("musicxml", fp=f"{temp_dir}/output.mxl")

        # Step 2: Convert MusicXML to MIDI using music21
        musicxml_path = f"{temp_dir}/output.mxl"
        score = converter.parse(musicxml_path)
        midi_path = f"{temp_dir}/output.mid"
        midi_file = midi.translate.music21ObjectToMidiFile(score)
        midi_file.open(midi_path, "wb")
        midi_file.write()
        midi_file.close()
        print("MusicXML files successfully converted to MIDI")

        # Step 3: Convert MIDI to WAV using FluidSynth
        wav_path = f"{temp_dir}/output.wav"
        subprocess.run(["fluidsynth", "-ni", midi_path, "-F", wav_path], check=True)
        print("MIDI file successfully converted to SoundFont")

        # Step 4: Return WAV as a streaming response
        with open(wav_path, "rb") as wav_file:
            audio_data = wav_file.read()
        print("Audiofile created successfully")

    return Response(audio_data, media_type="audio/wav")
