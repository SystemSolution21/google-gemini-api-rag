# imports built-in modules
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

# imports third-party modules
import google.generativeai as genai
from dotenv import load_dotenv
from google.generativeai.generative_models import ChatSession
from google.generativeai.types import File as GeminiFile

# load environment variables
load_dotenv()

# Configure Gemini API
api_key: str | None = os.getenv("GOOGLE_API_KEY", None)
if api_key is None:
    print("Warning: GOOGLE_API_KEY not found in environment variables.")
    sys.exit(1)
else:
    genai.configure(api_key=api_key)

# Configuration for the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}


def upload_file(file_path: str, display_name: Optional[str] = None) -> GeminiFile:
    """Uploads a file to Gemini API."""
    if not display_name:
        display_name = Path(file_path).name

    print(f"Uploading file: {display_name}...")
    file_ref = genai.upload_file(path=file_path, display_name=display_name)
    print(f"Completed upload: {file_ref.uri}")
    return file_ref


def wait_for_files_active(files: List[GeminiFile]) -> None:
    """Waits for the given files to be active."""
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file_obj = genai.get_file(name)
        while file_obj.state.name == "PROCESSING":
            print(".", end="", flush=True)

            time.sleep(2)
            file_obj = genai.get_file(name)
        if file_obj.state.name != "ACTIVE":
            raise Exception(f"File {file_obj.name} failed to process")
    print("...all files ready")


def create_chat_session(files: Optional[List[GeminiFile]] = None) -> ChatSession:
    """Creates a chat session with the given files in history/context."""

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=generation_config,
        system_instruction="""You are a helpful assistant. You have access to the provided files. 
        Answer questions based on the information in these files. 
        When citing sources, use the format (p. X) for page references, where X is the page number.
        Format your responses in a clear, readable style that works well with markdown rendering.""",
    )

    history = []
    if files:
        # In the new Gemini API, we can pass files directly in the history or message
        # For a "chat with document" feel, we can treat them as part of the prompt context
        # or use the File Search tool if we were using the Assistants API equivalent.
        # For standard GenerativeModel, passing the file object in the history works well for 1.5 Flash.
        for file in files:
            history.append({"role": "user", "parts": [file]})
            # Add a dummy model response to acknowledge receipt, to keep chat history balanced if needed
            # Or just start the chat. 1.5 Flash handles mixed content well.

    chat = model.start_chat(history=history)
    return chat
