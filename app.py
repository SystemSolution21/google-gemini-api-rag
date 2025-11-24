import os
from pathlib import Path

import chainlit as cl

import rag_manager

# Global variable to store the chat session
# In Chainlit, we usually store session data in cl.user_session


def format_response_with_citations(response):
    """Helper to format the response text with citations."""
    answer_text = response.text

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

                # No local file path appended as files are temporary and not stored in session.

                citations.append(citation_text)

    return answer_text + "\n".join(citations)


@cl.on_chat_start
async def start():
    # Ensure uploads directory exists
    os.makedirs("uploads", exist_ok=True)
    cl.user_session.set("uploaded_files", {})

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

        # Save file to a temporary location
        import tempfile

        with open(text_file.path, "rb") as src:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(text_file.name).suffix
            ) as tmp:
                tmp.write(src.read())
                upload_path = Path(tmp.name)
        # No session storage of uploaded files; they are temporary.

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
            final_response = format_response_with_citations(response)

            msg.content = final_response
            await msg.update()

        except Exception as e:
            msg.content = f"Error processing file: {str(e)}"
            await msg.update()
        # No finally block to delete files - we keep them now


@cl.on_message
async def main(message: cl.Message):
    chat_session = cl.user_session.get("chat_session")

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

                # Save file to a temporary location
                import tempfile

                with open(element.path, "rb") as src:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=Path(element.name).suffix
                    ) as tmp:
                        tmp.write(src.read())
                        upload_path = Path(tmp.name)
                # No session storage of uploaded files; they are temporary.

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
                # No finally block - keep files

    # If we have content (text or files), send it
    if gemini_content:
        # If the user only sent a file without text, add a prompt to summarize it
        if not message.content and message.elements:
            gemini_content.append(
                "Analyze the uploaded document(s). List the filename, and provide a brief summary with 3-5 citations pointing to key sections. Include page numbers if inferred."
            )

            # If we reused the 'msg' from upload, we should update it.
            # If there was no upload (just text), we create a new message.
            # But here we know we have elements if we are in this block.
            # Let's assume 'msg' exists if we uploaded files.
            # However, gemini_content might have text too.

        try:
            response = chat_session.send_message(gemini_content)
            final_response = format_response_with_citations(response)

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
