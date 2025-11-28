# rag_manager.py

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
    """Upload a file to the Gemini API.

    Parameters
    ----------
    file_path : str
        Path to the local file to be uploaded.
    display_name : Optional[str], default None
        Optional display name for the file in Gemini. If omitted, the
        filename from ``file_path`` is used.

    Returns
    -------
    types.File
        A reference to the uploaded file returned by the Gemini client.
    """
    if not display_name:
        display_name = Path(file_path).name

    print(f"Uploading file: {display_name}...")
    file_ref = client.files.upload(file=file_path)
    print(f"Completed upload: {file_ref.uri}")
    return file_ref


def wait_for_files_active(files: List[types.File]) -> None:
    """Block until all provided files are processed and active.

    The function polls the Gemini file status every two seconds until each
    file transitions from ``PROCESSING`` to ``ACTIVE``. If a file fails to
    become active, an exception is raised.

    Parameters
    ----------
    files : List[types.File]
        List of file references returned by :func:`upload_file`.

    Raises
    ------
    Exception
        If any file has no name or fails to reach the ``ACTIVE`` state.
    """
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
    """Create a Gemini chat session with optional file context.

    A system instruction is supplied to guide the assistant. If a list of
    files is provided, they are added to the initial chat history as a
    user message so that the model can reference them during the session.

    Parameters
    ----------
    files : Optional[List[types.File]], default None
        Files to include in the chat context. Each file must have a
        ``uri`` and ``mime_type``.

    Returns
    -------
    chats.Chat
        A chat session object that can be used to send messages to Gemini.
    """
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
