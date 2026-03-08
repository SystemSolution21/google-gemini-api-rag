# src/core/rag_manager.py
"""
Gemini RAG Manager.

Handles file uploads, processing, and chat session creation
with the Google Gemini API.
"""

# imports built-in modules
import os
import shutil
import time
import uuid
from typing import List, Optional

# imports third-party modules
from google import genai
from google.genai import chats, types

# imports local modules
from src.config import config
from src.utils.logger import get_app_logger

# Application logger
logger = get_app_logger()

# Create the Gemini client with API key
client = genai.Client(api_key=config.GOOGLE_API_KEY)

# Configuration for the model
generation_config = types.GenerateContentConfig(
    temperature=config.GEMINI_TEMPERATURE,
    top_p=config.GEMINI_TOP_P,
    top_k=config.GEMINI_TOP_K,
    max_output_tokens=config.GEMINI_MAX_OUTPUT_TOKENS,
    response_mime_type="text/plain",
)


async def upload_file(file_path: str, display_name: str | None = None) -> types.File:
    """Upload a file to Gemini and return the File object."""
    try:
        # Use display_name if provided, otherwise extract from path
        name = display_name or os.path.basename(file_path)
        logger.info(f"Uploading file: {name}")

        # Create ASCII-safe temporary filename for upload
        file_ext = os.path.splitext(file_path)[1]
        temp_filename = f"upload_{uuid.uuid4().hex}{file_ext}"
        temp_path = os.path.join(os.path.dirname(file_path), temp_filename)

        # Copy file to temp location with ASCII-safe name
        shutil.copy2(file_path, temp_path)

        try:
            # Upload file using the ASCII-safe path
            uploaded_file = client.files.upload(file=temp_path)
            logger.info(f"File uploaded successfully: {uploaded_file.uri}")
            return uploaded_file
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        raise


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

    logger.info("Waiting for file processing...")
    for file in files:
        if not file.name:
            raise Exception("File has no name")
        file_obj = client.files.get(name=str(file.name))
        while file_obj.state == "PROCESSING":
            logger.debug("File still processing...")
            time.sleep(2)
            file_obj = client.files.get(name=str(file.name))
        if file_obj.state != "ACTIVE":
            raise Exception(f"File {file_obj.name} failed to process")
    logger.info("All files ready")


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

    # System instruction
    system_instruction = """You are a helpful assistant. You have access to the provided files.

**Language rule**: Detect the primary language of the document and respond entirely in that language. Do not translate content.

**Task 1 – Summary**
Summarize the file concisely and clearly, covering the main topics and key findings.
When referencing a specific fact or section, cite the page inline using the format (p. X), where X is the page number.

**Task 2 – Key Takeaways Q&A**
End with a Q&A section of the most important takeaways from the document, in the same language as the document.

Format the entire response in clean Markdown (headings, bullet points, bold) for readability."""

    # History with files provided
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
        model=config.GEMINI_MODEL,
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
