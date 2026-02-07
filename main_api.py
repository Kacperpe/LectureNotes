# main_api.py
# Web server backend for the Nagrania mobile app.

import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os
import shutil

# --- App Imports ---
from transcriber import load_model, transkrybuj_audio
import config  # Assuming config might be needed for default settings

# --- Basic App Setup ---
app = FastAPI()
model_whisper = None  # Global variable to hold the loaded model

# --- Model Loading on Startup ---
@app.on_event("startup")
def startup_event():
    """
    Load the Whisper model into memory once when the server starts.
    """
    global model_whisper
    # Using "base" model as specified in the original bot logic
    model_whisper = load_model("base")

# --- API Endpoints ---
@app.get("/")
def read_root():
    """
    Root endpoint to check if the server is running.
    """
    return {"message": "Nagrania Bot API is running."}

@app.post("/transcribe")
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    """
    This endpoint receives an audio file, saves it,
    transcribes it, and returns the transcription text.
    """
    # Define a temporary path to save the uploaded file
    temp_dir = "api_uploads"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    temp_file_path = os.path.join(temp_dir, file.filename)

    try:
        # Save the uploaded file to the temporary path
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # --- Actual Transcription ---
        # The model is pre-loaded and ready to use.
        # The 'language' parameter can be exposed as a query parameter if needed later.
        transcription_text = transkrybuj_audio(temp_file_path, model_whisper)
        
        if transcription_text is None:
            raise Exception("Transcription failed and returned None.")

        # Return the transcription in a JSON response
        return JSONResponse(content={"transcription": transcription_text})

    except Exception as e:
        # Handle potential errors
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        # The `transkrybuj_audio` function handles its own file cleanup,
        # so we no longer need to remove the file here.
        pass


# --- Running the Server ---
if __name__ == "__main__":
    """
    This allows you to run the server directly using:
    'python main_api.py'
    
    The server will be accessible on your local network.
    """
    uvicorn.run(app, host="0.0.0.0", port=8000)
