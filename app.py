import atexit
import os
import re
import shutil
from pathlib import Path
from typing import Optional

import chainlit as cl
from google.generativeai.generative_models import ChatSession
from google.generativeai.types import GenerateContentResponse

import rag_manager

# Global variable to store the chat session
# In Chainlit, we usually store session data in cl.user_session


def cleanup_public_folder():
    """Delete the public folder and all its contents when the app exits."""
    public_path = Path("public")
    if public_path.exists():
        try:
            shutil.rmtree(public_path)
            print("✓ Cleaned up public folder")
        except Exception as e:
            print(f"Warning: Could not clean up public folder: {e}")


# Register cleanup function to run when the app exits
atexit.register(cleanup_public_folder)


def format_response_with_citations(
    response: GenerateContentResponse, source_document_name: Optional[str] = None
) -> str:
    """Helper to format the response text with citations."""
    answer_text = response.text

    # Link page citations if source document is provided
    if source_document_name:
        # Pattern for ", p. X)" - inline citations with quotes
        answer_text = re.sub(
            r'",\s*p\.\s*(\d+)\)',
            rf'", [p. \1](/public/{source_document_name}#page=\1))',
            answer_text,
        )
        # Pattern for (p. X) - standalone citations
        answer_text = re.sub(
            r"\(p\.\s*(\d+)\)",
            rf"([p. \1](/public/{source_document_name}#page=\1))",
            answer_text,
        )
        # Pattern for ", p. X-Y)" - inline range citations
        answer_text = re.sub(
            r'",\s*p\.\s*(\d+)-(\d+)\)',
            rf'", [p. \1-\2](/public/{source_document_name}#page=\1))',
            answer_text,
        )
        # Pattern for (p. X-Y) - standalone range citations
        answer_text = re.sub(
            r"\(p\.\s*(\d+)-(\d+)\)",
            rf"([p. \1-\2](/public/{source_document_name}#page=\1))",
            answer_text,
        )

    citations = []
    if response.candidates and response.candidates[0].citation_metadata:
        citation_sources = response.candidates[0].citation_metadata.citation_sources
        if citation_sources:
            citations.append("\n\n**Citations:**")
            for i, source in enumerate(citation_sources):
                citation_text = f"{i + 1}. "
                if source.uri:
                    citation_text += f"[{source.uri}]({source.uri})"
                else:
                    citation_text += "Source Document"

                if source.start_index is not None and source.end_index is not None:
                    citation_text += (
                        f" (Indexes: {source.start_index}-{source.end_index})"
                    )

                citations.append(citation_text)

    return answer_text + "\n".join(citations)


@cl.on_chat_start
async def start():
    # Ensure public directory exists for serving PDF files (temporary storage)
    os.makedirs("public", exist_ok=True)

    # Ask user to upload a file
    files_uploaded = await cl.AskFileMessage(
        content="Please upload a text or PDF file to begin!",
        accept=["text/plain", "application/pdf"],
        max_size_mb=20,
        timeout=180,
    ).send()

    if files_uploaded:
        text_file = files_uploaded[0]

        msg = cl.Message(content=f"Processing `{text_file.name}`...")
        await msg.send()

        # Save file to public directory to enable PDF page links (e.g., /public/file.pdf#page=5)
        # This is necessary because Chainlit's temporary file paths are not web-accessible
        # Files will be cleaned up when the app exits
        public_path = Path("public") / text_file.name
        with open(public_path, "wb") as f:
            with open(text_file.path, "rb") as src:
                f.write(src.read())

        # Store the filename in session for later use
        cl.user_session.set("current_file_name", text_file.name)

        # Use the public path for Gemini upload
        upload_path = public_path

        try:
            # Upload to Gemini
            gemini_file = rag_manager.upload_file(str(upload_path))
            rag_manager.wait_for_files_active([gemini_file])

            # Create Chat Session
            chat_session = rag_manager.create_chat_session([gemini_file])
            cl.user_session.set("chat_session", chat_session)

            msg.content = f"Processing `{text_file.name}` done. Generating summary..."
            await msg.update()

            # Auto-Summary
            initial_prompt = f"Analyze the uploaded document '{text_file.name}'. List the filename, and provide a brief summary with 3-5 citations pointing to key sections. Include page numbers if inferred."
            response = chat_session.send_message(initial_prompt)
            final_response = format_response_with_citations(response, text_file.name)

            msg.content = final_response
            await msg.update()

        except Exception as e:
            msg.content = f"Error processing file: {str(e)}"
            await msg.update()


@cl.on_message
async def main(message: cl.Message):
    chat_session: Optional[ChatSession] = cl.user_session.get("chat_session")
    current_file_name: Optional[str] = cl.user_session.get("current_file_name")

    if not chat_session:
        await cl.Message(
            content="No active session. Please restart and upload a file."
        ).send()
        return

    # Prepare content to send to Gemini
    gemini_content = []

    # Handle text content
    if message.content:
        gemini_content.append(message.content)

    # Handle attachments
    if message.elements:
        for element in message.elements:
            # Check if it's a file we can process
            if element.mime and ("pdf" in element.mime or "text" in element.mime):
                msg = cl.Message(content=f"Processing `{element.name}`...")
                await msg.send()

                # Save file to public directory to enable PDF page links
                public_path = Path("public") / element.name
                with open(public_path, "wb") as f:
                    with open(element.path, "rb") as src:
                        f.write(src.read())

                # Update current file name
                current_file_name = element.name
                cl.user_session.set("current_file_name", current_file_name)

                upload_path = public_path

                try:
                    # Upload to Gemini
                    gemini_file = rag_manager.upload_file(str(upload_path))
                    rag_manager.wait_for_files_active([gemini_file])
                    gemini_content.append(gemini_file)

                    msg.content = f"Processing `{element.name}` done."
                    await msg.update()

                except Exception as e:
                    await cl.Message(
                        content=f"Error processing {element.name}: {str(e)}"
                    ).send()

    # If we have content (text or files), send it
    if gemini_content:
        # If the user only sent a file without text, add a prompt to summarize it
        if not message.content and message.elements:
            gemini_content.append(
                "Analyze the uploaded document(s). List the filename, and provide a brief summary with 3-5 citations pointing to key sections. Include page numbers if inferred."
            )

        try:
            response = chat_session.send_message(gemini_content)
            final_response = format_response_with_citations(response, current_file_name)

            # If we had a 'msg' from file processing (and no text query), we could update it.
            # But if the user sent text + file, the 'msg' was "Processing file...".
            # It's cleaner to just send the answer as a new message for the query response,
            # OR if it was ONLY a file upload (auto-summary), update the processing message.

            if not message.content and message.elements and "msg" in locals():
                msg.content = final_response
                await msg.update()
            else:
                await cl.Message(content=final_response).send()

        except Exception as e:
            await cl.Message(content=f"An error occurred: {str(e)}").send()
    else:
        await cl.Message(content="Please send text or a valid file.").send()
