# imports built-in modules
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

# imports third-party modules
from dotenv import load_dotenv
from google import genai
from google.genai import chats, types

# load environment variables
load_dotenv()

# Configure Gemini API - Create client
api_key: str | None = os.getenv("GOOGLE_API_KEY", None)
if api_key is None:
    print("Warning: GOOGLE_API_KEY not found in environment variables.")
    sys.exit(1)

# Create the client with API key
client = genai.Client(api_key=api_key)

# Configuration for the model
generation_config = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    top_k=64,
    max_output_tokens=8192,
    response_mime_type="text/plain",
)


def upload_file(file_path: str, display_name: Optional[str] = None) -> types.File:
    """Uploads a file to Gemini API."""
    if not display_name:
        display_name = Path(file_path).name

    print(f"Uploading file: {display_name}...")
    file_ref = client.files.upload(file=file_path)
    print(f"Completed upload: {file_ref.uri}")
    return file_ref


def wait_for_files_active(files: List[types.File]) -> None:
    """Waits for the given files to be active."""
    print("Waiting for file processing...")
    for file in files:
        if not file.name:
            raise Exception("File has no name")
        file_obj = client.files.get(name=str(file.name))
        while file_obj.state == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            file_obj = client.files.get(name=str(file.name))
        if file_obj.state != "ACTIVE":
            raise Exception(f"File {file_obj.name} failed to process")
    print("...all files ready")


def create_chat_session(files: Optional[List[types.File]] = None) -> chats.Chat:
    """Creates a chat session with the given files in history/context."""

    # Prepare system instruction
    system_instruction = """You are a helpful assistant. You have access to the provided files.
    Answer questions based on the information in these files.
    When citing sources, use the format (p. X) for page references, where X is the page number.
    Format your responses in a clear, readable style that works well with markdown rendering."""

    # Prepare history with files if provided
    history = []
    if files:
        # Add files to the initial history
        file_parts = []
        for file in files:
            if file.uri and file.mime_type:
                file_parts.append(
                    types.Part.from_uri(
                        file_uri=str(file.uri), mime_type=file.mime_type
                    )
                )

        # Add files as the first user message
        if file_parts:
            history.append(types.Content(role="user", parts=file_parts))

    # Create chat session with the new SDK
    chat = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=generation_config.temperature,
            top_p=generation_config.top_p,
            top_k=generation_config.top_k,
            max_output_tokens=generation_config.max_output_tokens,
            response_mime_type=generation_config.response_mime_type,
        ),
        history=history if history else None,
    )
    return chat
