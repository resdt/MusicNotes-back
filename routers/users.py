import os
import base64

from fastapi import APIRouter, UploadFile, HTTPException


router = APIRouter()

AUDIO_FOLDER = "uploaded_audio"


@router.post("/{user_id}/upload_audio")
async def upload_audio(user_id: int, filename: str, file_: UploadFile):
    user_folder = os.path.join(AUDIO_FOLDER, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    filename += ".wav"
    file_path = os.path.join(user_folder, filename)
    with open(file_path, "wb") as audio_file:
        content = await file_.read()
        audio_file.write(content)
    return {"message": f"File {filename} uploaded successfully."}


@router.get("/{user_id}/my_music")
async def my_music(user_id: int):
    music_list = []
    user_folder = os.path.join(AUDIO_FOLDER, str(user_id))

    if not os.path.exists(user_folder):
        return music_list

    for filename in os.listdir(user_folder):
        file_path = os.path.join(user_folder, filename)
        with open(file_path, "rb") as f:
            content = f.read()

        # Encode binary content to Base64
        encoded_content = base64.b64encode(content).decode("utf-8")
        music_list.append((filename.split(".")[0], encoded_content))

    return music_list


@router.put("/{user_id}/my_music/delete")
async def delete_music(user_id: int, filename: str):
    filename += ".wav"
    file_to_delete = os.path.join(AUDIO_FOLDER, str(user_id), filename)

    if not os.path.exists(file_to_delete):
        raise HTTPException(status_code=404, detail="File not found")

    os.remove(file_to_delete)
