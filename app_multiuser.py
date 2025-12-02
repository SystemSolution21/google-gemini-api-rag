# app_multiuser.py
"""
Multi-user Chainlit chatbot with PostgreSQL persistence, user authentication,
and chat session management. This is an enhanced version of app.py with:
- User registration and login
- Multiple chat sessions per user
- Message and document persistence
- Chat history loading
"""

# imports built-in modules
import re
import shutil
from pathlib import Path
from typing import Any, Optional

# imports third-party modules
import chainlit as cl
from google.genai import types

# imports local modules
import auth
import rag_manager
from database import get_pool
from models import ChatSession, Document, Message


# Initialize database on startup
@cl.on_chat_start
async def start():
    """Handle the initial chat start event with authentication and session management."""

    # Get authenticated user
    user = cl.user_session.get("user")
    if not user or not user.metadata:
        await cl.Message(content="❌ Authentication required. Please log in.").send()
        return

    username = user.metadata.get("username")

    # Welcome message
    await cl.Message(
        content=f"👋 Welcome back, **{username}**!\n\nWhat would you like to do?"
    ).send()

    # Show chat session options
    actions = [
        cl.Action(name="new_chat", payload={}, label="📝 New Chat"),
        cl.Action(name="list_chats", payload={}, label="📋 My Chats"),
    ]

    await cl.Message(content="Choose an option:", actions=actions).send()


@cl.action_callback("new_chat")
async def on_new_chat(action: cl.Action):
    """Handle new chat creation."""
    user_id = auth.get_current_user_id()
    if not user_id:
        await cl.Message(content="❌ Not authenticated").send()
        return

    # Ask for chat title
    res = await cl.AskUserMessage(
        content="Enter a title for your new chat:", timeout=60
    ).send()

    if res:
        title = res.get("output", "").strip()
        if not title:
            title = "Untitled Chat"

        # Create chat session in database
        pool = await get_pool()
        async with pool.acquire() as conn:
            session_id = await ChatSession.create(conn, user_id, title)

            if session_id:
                cl.user_session.set("chat_session_id", session_id)
                cl.user_session.set("chat_title", title)

                await cl.Message(
                    content=f"✅ Created new chat: **{title}**\n\nYou can now upload documents or start asking questions!"
                ).send()

                # Prompt for file upload
                await prompt_file_upload()
            else:
                await cl.Message(content="❌ Failed to create chat session").send()


@cl.action_callback("load_chat")
async def on_load_chat(action: cl.Action):
    """Load an existing chat session."""
    session_id = action.payload.get("session_id")
    user_id = auth.get_current_user_id()

    if not session_id or not user_id:
        await cl.Message(content="❌ Invalid session").send()
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verify session belongs to user
        session = await ChatSession.get_by_id(conn, session_id, user_id)
        if not session:
            await cl.Message(content="❌ Session not found").send()
            return

        # Set active session
        cl.user_session.set("chat_session_id", session_id)
        cl.user_session.set("chat_title", session["title"])

        # Load messages and documents
        messages = await Message.list_by_session(conn, session_id)
        documents = await Document.list_by_session(conn, session_id)

        # Recreate Gemini chat session with documents
        if documents:
            # Recreate Gemini files from stored URIs
            gemini_files = []
            for doc in documents:
                if doc["gemini_file_uri"] and doc["gemini_file_name"]:
                    # Create file object from stored metadata
                    gemini_file = types.File(
                        name=doc["gemini_file_name"],
                        uri=doc["gemini_file_uri"],
                        mime_type=doc["mime_type"],
                    )
                    gemini_files.append(gemini_file)

            if gemini_files:
                chat_session = rag_manager.create_chat_session(gemini_files)
                cl.user_session.set("gemini_chat", chat_session)

        await cl.Message(content=f"✅ Loaded chat: **{session['title']}**").send()

        # Optionally display recent messages
        if messages:
            recent_messages = messages[-3:]  # Show last 3 messages
            history_text = "**Recent conversation:**\n\n"
            for msg in recent_messages:
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                content_preview = (
                    msg["content"][:100] + "..."
                    if len(msg["content"]) > 100
                    else msg["content"]
                )
                history_text += (
                    f"{role_icon} **{msg['role'].title()}:** {content_preview}\n\n"
                )

            await cl.Message(content=history_text).send()


@cl.action_callback("list_chats")
async def on_list_chats(action: cl.Action):
    """Handle listing user's chat sessions."""
    user_id = auth.get_current_user_id()
    if not user_id:
        await cl.Message(content="❌ Not authenticated").send()
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        sessions = await ChatSession.list_by_user(conn, user_id)

        if not sessions:
            await cl.Message(
                content="You don't have any chat sessions yet. Create one to get started!"
            ).send()
            return

        # Create action buttons for each session
        session_actions = []
        session_list = "**Your Chat Sessions:**\n\n"

        for i, session in enumerate(sessions[:10], 1):  # Limit to 10 most recent
            session_list += f"{i}. **{session['title']}** - {session['updated_at'].strftime('%Y-%m-%d %H:%M')}\n"
            session_actions.append(
                cl.Action(
                    name="load_chat",  # Remove the dynamic part
                    payload={"session_id": session["id"]},
                    label=f"Load: {session['title'][:30]}",
                )
            )

        await cl.Message(content=session_list, actions=session_actions).send()


@cl.action_callback("delete_chat")
async def on_delete_chat(action: cl.Action):
    """Delete a chat session and its files."""
    session_id: Any | None = action.payload.get("session_id")
    user_id: int | None = auth.get_current_user_id()

    # Delete files first
    session_dir = Path("public") / str(user_id) / str(session_id)
    if session_dir.exists():
        shutil.rmtree(session_dir)

    # Then delete from database
    pool = await get_pool()
    async with pool.acquire() as conn:
        if session_id and user_id:
            await ChatSession.delete(conn, session_id, user_id)


async def prompt_file_upload():
    """Prompt user to upload a file for the current chat session."""
    files_uploaded = await cl.AskFileMessage(
        content="📎 Upload a text or PDF file to begin (or skip to chat without documents):",
        accept=["text/plain", "application/pdf"],
        max_size_mb=20,
        timeout=180,
    ).send()

    if files_uploaded:
        await process_uploaded_file(files_uploaded[0])


async def process_uploaded_file(file):
    """Process an uploaded file and add it to the current chat session."""
    chat_session_id = cl.user_session.get("chat_session_id")
    user_id = auth.get_current_user_id()

    if not chat_session_id or not user_id:
        await cl.Message(content="❌ No active chat session").send()
        return

    if not file.path:
        await cl.Message(content="❌ Uploaded file has no path").send()
        return

    msg = cl.Message(content=f"Processing `{file.name}`...")
    await msg.send()

    # Create user-specific directory
    user_dir = Path("public") / str(user_id) / str(chat_session_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = user_dir / file.name
    with open(file_path, "wb") as f:
        with open(file.path, "rb") as src:
            f.write(src.read())

    try:
        # Upload to Gemini
        gemini_file = rag_manager.upload_file(str(file_path))
        rag_manager.wait_for_files_active([gemini_file])

        # Save document to database
        pool = await get_pool()
        async with pool.acquire() as conn:
            await Document.create(
                conn,
                chat_session_id=chat_session_id,
                filename=file.name,
                file_path=str(file_path),
                gemini_file_uri=gemini_file.uri,
                gemini_file_name=gemini_file.name,
                mime_type=gemini_file.mime_type,
                file_size=file_path.stat().st_size,
            )

        # Create or update chat session with file
        chat_session = cl.user_session.get("gemini_chat")
        if not chat_session:
            chat_session = rag_manager.create_chat_session([gemini_file])
            cl.user_session.set("gemini_chat", chat_session)

        msg.content = f"✅ Processed `{file.name}` successfully!"
        await msg.update()

        # Auto-generate summary
        initial_prompt = f"""Analyze the uploaded document '{file.name}'. 
                                Provide a comprehensive summary using this format:

                                1. Start with a brief overview paragraph
                                2. Create section headers for main topics (use ## for headers)
                                3. Under each header, provide 2-3 bullet points with key insights
                                4. Include specific page references using (p. X) format
                                5. End with a conclusion section

                                Format the response with clear structure and include citations pointing to relevant sections."""
        response = chat_session.send_message(message=initial_prompt)

        # Save messages to database
        pool = await get_pool()
        async with pool.acquire() as conn:
            await Message.create(conn, chat_session_id, "user", initial_prompt)
            await Message.create(
                conn, chat_session_id, "assistant", response.text or ""
            )

        final_response = format_response_with_citations(response, file.name)
        await cl.Message(content=final_response).send()

    except Exception as e:
        msg.content = f"❌ Error processing file: {str(e)}"
        await msg.update()


def format_response_with_citations(
    response: types.GenerateContentResponse, source_document_name: Optional[str] = None
) -> str:
    """Format Gemini's response text with citation links."""
    answer_text = response.text or ""

    if source_document_name and answer_text:
        # Get current user and session info for correct path
        user_id = auth.get_current_user_id()
        chat_session_id = cl.user_session.get("chat_session_id")

        if user_id and chat_session_id:
            file_path = f"{user_id}/{chat_session_id}/{source_document_name}"

            # Pattern for citations with correct multi-user path
            answer_text = re.sub(
                r'",\s*p\.\s*(\d+)\)',
                rf'", [p. \1](/public/{file_path}#page=\1))',
                answer_text,
            )
            answer_text = re.sub(
                r"\(p\.\s*(\d+)\)",
                rf"([p. \1](/public/{file_path}#page=\1))",
                answer_text,
            )

    citations = []
    if response.candidates and response.candidates[0].citation_metadata:
        citation_metadata = response.candidates[0].citation_metadata
        if citation_metadata.citations:
            citations.append("\n\n**Citations:**")
            for i, source in enumerate(citation_metadata.citations):
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


@cl.on_message
async def main(message: cl.Message):
    """Process user messages with database persistence."""
    chat_session_id = cl.user_session.get("chat_session_id")

    if not chat_session_id:
        await cl.Message(
            content="❌ No active chat session. Please create or load a chat first."
        ).send()
        return

    gemini_chat = cl.user_session.get("gemini_chat")
    if not gemini_chat:
        # Create a new Gemini chat session without files
        gemini_chat = rag_manager.create_chat_session()
        cl.user_session.set("gemini_chat", gemini_chat)

    # Save user message to database
    pool = await get_pool()
    async with pool.acquire() as conn:
        await Message.create(conn, chat_session_id, "user", message.content)

    try:
        # Send to Gemini
        response = gemini_chat.send_message(message=message.content)
        response_text = response.text or ""

        # Save assistant response to database
        async with pool.acquire() as conn:
            await Message.create(conn, chat_session_id, "assistant", response_text)

        # Get document filename for citations
        async with pool.acquire() as conn:
            documents = await Document.list_by_session(conn, chat_session_id)
            doc_filename = documents[0]["filename"] if documents else None

        # Format and send response
        final_response = format_response_with_citations(response, doc_filename)
        await cl.Message(content=final_response).send()

    except Exception as e:
        error_msg = f"❌ An error occurred: {str(e)}"
        await cl.Message(content=error_msg).send()

        # Save error to database
        async with pool.acquire() as conn:
            await Message.create(conn, chat_session_id, "assistant", error_msg)


@cl.on_stop
def on_stop():
    """Handle session stop."""
    print("🔄 Chat session stopped")


@cl.on_chat_end
async def on_chat_end():
    """Handle chat end."""
    print("👋 Chat session ended")
