# app_multiuser.py
"""
Multi-user Chainlit chatbot with PostgreSQL persistence, user authentication,
and chat session management.
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
from src.auth import handlers as auth
from src.core import rag_manager
from src.db import ChatSession, Document, Message, get_pool
from src.utils import format_response_with_citations
from src.utils.logger import get_app_logger

# Application logger
logger = get_app_logger()


@cl.set_chat_profiles
async def chat_profile(current_user: cl.User | None, current_chat_profile: str | None):
    """Set up chat profiles for recent chats."""

    # Get user id from current user metadata (username display as identifier)
    user_id = None
    if current_user and current_user.metadata:
        user_id = current_user.metadata.get("user_id")

    if not user_id:
        return []

    # Create database connection pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        sessions = await ChatSession.list_by_user(conn, user_id)

        profiles = []

        # List user's most recent chats
        title_counts: dict[str, int] = {}
        for idx, session in enumerate(sessions[:5]):  # Show 5 most recent
            title = session["title"]
            if title in title_counts:
                title_counts[title] += 1
                profile_name = f"{title} ({title_counts[title]})"
            else:
                title_counts[title] = 1
                profile_name = title

            # Add profile for the recent chat
            profiles.append(
                cl.ChatProfile(
                    name=profile_name,
                    markdown_description=f"{session['updated_at'].strftime('%Y-%m-%d %H:%M')}",
                    icon="💬",
                    default=(idx == 0),  # Most recent chat is default
                )
            )

        # Add profile for new chat options
        profiles.append(
            cl.ChatProfile(
                name="new_chat",
                markdown_description="Create a new chat session",
                icon="📝",
                default=(len(sessions) == 0),  # Default only if no chats exist
            )
        )
        # Add profile for chat management option
        profiles.append(
            cl.ChatProfile(
                name="manage_chats",
                markdown_description="Manage all your chats (rename, delete)",
                icon="⚙️",
            )
        )

        return profiles


async def _handle_registration(user: cl.User):
    """Handle the user registration flow within a valid chat context."""
    if not user.metadata:
        await cl.Message(
            content="❌ Registration failed: User metadata not found."
        ).send()
        return

    try:
        # --- 1. Get Username ---
        await cl.Message(content="👋 Welcome! Let's create your account.").send()
        await cl.Message(content="**Step 1: Enter a username**").send()
        cl.user_session.set("registration_step", "username")

    except Exception as e:
        await cl.Message(
            content=f"❌ An error occurred during registration: {e}"
        ).send()


async def _handle_registration_step(step: str, value: str):
    """
    Process a single step of the conversational registration flow.

    This function acts as a state machine, processing the input for the current
    step and advancing to the next one.
    """
    if step == "username":
        username = value
        if not username:
            await cl.Message(
                content="❌ Username cannot be empty. Please try again."
            ).send()
            return

        cl.user_session.set("registration_username", username)
        cl.user_session.set("registration_step", "email")

        user = cl.user_session.get("user")
        email_from_login = "your_email@example.com"
        if user and user.metadata:
            email_from_login = user.metadata.get("email_from_login", email_from_login)

        await cl.Message(
            content=f"**Step 2: Enter your email address again**\n(`{email_from_login}`)"
        ).send()

    elif step == "email":
        user = cl.user_session.get("user")
        email_from_login = ""
        if user and user.metadata:
            email_from_login = user.metadata.get("email_from_login", "")
        email = value if value else email_from_login

        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            await cl.Message(
                content=f"❌ Invalid email address: `{email}`. Please try again."
            ).send()
            return

        cl.user_session.set("registration_email", email)
        cl.user_session.set("registration_step", "password")
        await cl.Message(
            content="**Step 3: Enter a password** (must be at least 8 characters)"
        ).send()

    elif step == "password":
        password = value
        if not password:
            await cl.Message(
                content="❌ Password cannot be empty. Please try again."
            ).send()
            return

        if len(password) < 8:
            await cl.Message(
                content="❌ Password must be at least 8 characters long. Please try again."
            ).send()
            return

        cl.user_session.set("registration_password", password)
        cl.user_session.set("registration_step", "password_confirm")
        await cl.Message(content="**Step 4: Confirm your password**").send()

    elif step == "password_confirm":
        password_confirm = value
        if not password_confirm:
            await cl.Message(
                content="❌ Password confirmation cannot be empty. Please try again."
            ).send()
            return

        password = cl.user_session.get("registration_password")
        if password != password_confirm:
            await cl.Message(content="❌ Passwords do not match.").send()
            # Reset to password step
            cl.user_session.set("registration_step", "password")
            await cl.Message(
                content="**Step 3: Enter a password** (must be at least 8 characters)"
            ).send()
            return

        # --- Final Step: Create User and End Flow ---
        username = cl.user_session.get("registration_username")
        email = cl.user_session.get("registration_email")
        if username and email and password:
            user_id = await auth.register_user(username, email, password)

        # Clean up session state
        cl.user_session.set("registration_step", None)
        cl.user_session.set("registration_username", None)
        cl.user_session.set("registration_email", None)
        cl.user_session.set("registration_password", None)

        if user_id:
            await cl.Message(
                content=f"✅ **Registration successful for user '{username}'!**\n\nPlease logout! And login again with your new credentials."
            ).send()
        else:
            await cl.Message(
                content="❌ **Registration failed.**\n\nThe username or email may already be in use. Please try again by refreshing the page and starting over."
            ).send()


@cl.on_chat_start
async def start():
    """Handle the initial chat start event with authentication and session management."""

    # Get authenticated user
    user = cl.user_session.get("user")
    if not user:
        await cl.Message(content="❌ Authentication required. Please log in.").send()
        return

    # Check for pending registration
    if user.metadata.get("registration_pending"):
        await _handle_registration(user)
        return

    # Check which profile was selected
    chat_profile = cl.user_session.get("chat_profile")

    if chat_profile == "new_chat":
        # Explicitly create new chat
        await create_new_chat_flow()

    elif chat_profile == "manage_chats":
        # Show management interface
        await show_chat_management()

    elif chat_profile:
        # Try to load chat by matching profile name to session title
        await load_chat_by_profile_name(chat_profile)

    else:
        # Default: Load most recent chat or create new one if none exists
        await load_or_create_chat()


async def load_or_create_chat():
    """Load the most recent chat session, or create a new one if none exists."""
    user_id = auth.get_current_user_id()
    if not user_id:
        await cl.Message(content="❌ Not authenticated").send()
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        sessions = await ChatSession.list_by_user(conn, user_id)

        if sessions:
            # Load the most recent chat
            most_recent = sessions[0]
            await load_chat_by_id(most_recent["id"])
        else:
            # No existing chats, create a new one
            await create_new_chat_flow()


async def create_new_chat_flow():
    """Create a new chat session and set it as active."""
    user_id = auth.get_current_user_id()
    user_name = auth.get_current_username()
    if not user_id:
        await cl.Message(content="❌ Not authenticated").send()
        return

    # Create new chat session in database
    pool = await get_pool()
    async with pool.acquire() as conn:
        session_id = await ChatSession.create(conn, user_id, "New Chat")
        if not session_id:
            await cl.Message(content="❌ Failed to create chat session").send()
            return

    # Set active session
    cl.user_session.set("chat_session_id", session_id)
    cl.user_session.set("chat_title", "New Chat")

    # Create empty Gemini chat session immediately
    gemini_chat = rag_manager.create_chat_session()
    cl.user_session.set("gemini_chat", gemini_chat)

    await cl.Message(
        content=f"🆕 **New chat created for {user_name}!**\n\nYou can start chatting now or upload a file using the attachment button (📎)."
    ).send()


async def show_chat_management():
    """Show chat management interface with rename/delete options."""
    user_id = auth.get_current_user_id()
    if not user_id:
        await cl.Message(content="❌ Not authenticated").send()
        return

    # Remove previous management messages to avoid stacking
    old_management_msgs = cl.user_session.get("management_messages") or []
    for msg in old_management_msgs:
        await msg.remove()
    cl.user_session.set("management_messages", [])

    pool = await get_pool()
    async with pool.acquire() as conn:
        sessions = await ChatSession.list_by_user(conn, user_id)

        if not sessions:
            await cl.Message(
                content="You don't have any chat sessions yet. Create one to get started!"
            ).send()
            return

        # Track management messages for later removal
        management_msgs = []

        # Send header message
        header_msg = cl.Message(
            content="⚙️ **Chat Management**\n\nSelect an action for each chat:"
        )
        await header_msg.send()
        management_msgs.append(header_msg)

        # Send each chat as a separate message with its own action buttons
        for i, session in enumerate(sessions[:10], 1):
            chat_info = f"**{i}. {session['title']}**\n📅 {session['updated_at'].strftime('%Y-%m-%d %H:%M')}"

            # Create action buttons for this specific chat
            chat_actions = [
                cl.Action(
                    name="load_chat",
                    payload={"session_id": session["id"]},
                    label="📂 Load",
                ),
                cl.Action(
                    name="rename_chat",
                    payload={
                        "session_id": session["id"],
                        "current_title": session["title"],
                    },
                    label="✏️ Rename",
                ),
                cl.Action(
                    name="delete_chat",
                    payload={"session_id": session["id"], "title": session["title"]},
                    label="🗑️ Delete",
                ),
            ]

            chat_msg = cl.Message(content=chat_info, actions=chat_actions)
            await chat_msg.send()
            management_msgs.append(chat_msg)

        # Store references for later removal
        cl.user_session.set("management_messages", management_msgs)


async def load_chat_by_profile_name(profile_name: str):
    """Load a chat session by matching profile name to session title."""
    user_id = auth.get_current_user_id()
    if not user_id:
        await cl.Message(content="❌ Not authenticated").send()
        return

    # Check if this chat is already loaded
    current_session_id = cl.user_session.get("chat_session_id")
    current_title = cl.user_session.get("chat_title")

    pool = await get_pool()
    async with pool.acquire() as conn:
        sessions = await ChatSession.list_by_user(conn, user_id)

        # Build same mapping as in chat_profile to find matching session
        title_counts: dict[str, int] = {}
        for session in sessions[:5]:
            title = session["title"]
            if title in title_counts:
                title_counts[title] += 1
                expected_name = f"{title} ({title_counts[title]})"
            else:
                title_counts[title] = 1
                expected_name = title

            if expected_name == profile_name:
                # Check if this is already the active session
                if current_session_id == session["id"]:
                    await cl.Message(
                        content=f"✅ Chat **{current_title}** is already active. You can continue chatting."
                    ).send()
                    return
                await load_chat_by_id(session["id"])
                return

    await cl.Message(content="❌ Chat session not found").send()


async def load_chat_by_id(session_id: int):
    """Load a specific chat by ID and display chat history."""
    user_id = auth.get_current_user_id()
    if not user_id:
        await cl.Message(content="❌ Not authenticated").send()
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
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

        # Recreate Gemini chat session with documents (or without if none)
        gemini_files = []
        if documents:
            for doc in documents:
                if doc["gemini_file_uri"] and doc["gemini_file_name"]:
                    gemini_file = types.File(
                        name=doc["gemini_file_name"],
                        uri=doc["gemini_file_uri"],
                        mime_type=doc["mime_type"],
                    )
                    gemini_files.append(gemini_file)

        # Always create a Gemini chat session (with or without files)
        chat_session = rag_manager.create_chat_session(
            gemini_files if gemini_files else None
        )
        cl.user_session.set("gemini_chat", chat_session)

        # Show loaded chat confirmation with document info
        doc_info = ""
        if documents:
            doc_names = [doc["filename"] for doc in documents]
            doc_info = f"\n📄 Documents: {', '.join(doc_names)}"

        await cl.Message(
            content=f"✅ Loaded chat: **{session['title']}**{doc_info}\n\n💬 You can continue your conversation."
        ).send()

        # Display previous messages as chat history (skip internal prompts)
        if messages:
            display_messages = []
            for msg in messages:
                content = msg["content"]
                # Skip auto-generated system prompts
                if "Provide a comprehensive summary using this format:" in content:
                    continue
                display_messages.append(msg)

            if display_messages:
                await cl.Message(content="---\n**Previous conversation:**").send()
                for msg in display_messages:
                    author = "You" if msg["role"] == "user" else "Assistant"
                    content = msg["content"]
                    # Truncate long messages for display
                    if len(content) > 500:
                        content = content[:500] + "..."
                    # Format timestamp for tooltip-style display
                    timestamp = msg["created_at"].strftime("%Y-%m-%d %H:%M")
                    await cl.Message(
                        content=f"**{author}** `{timestamp}`\n{content}",
                        author=msg["role"],
                    ).send()
                await cl.Message(content="---\n**Continue chatting below:**").send()


@cl.action_callback("load_chat")
async def on_load_chat(action: cl.Action):
    """Load a chat session from management interface."""
    session_id: Any | None = action.payload.get("session_id")
    if session_id:
        # Remove management messages when exiting management mode
        old_management_msgs = cl.user_session.get("management_messages") or []
        for msg in old_management_msgs:
            await msg.remove()
        cl.user_session.set("management_messages", [])

        await load_chat_by_id(int(session_id))

        # Update chat_profile to match loaded chat title
        chat_title = cl.user_session.get("chat_title")
        if chat_title:
            cl.user_session.set("chat_profile", chat_title)


@cl.action_callback("rename_chat")
async def on_rename_chat(action: cl.Action):
    """Rename a chat session - stores session info for the next message."""
    session_id: Any | None = action.payload.get("session_id")
    current_title: str = action.payload.get("current_title", "")

    if not session_id:
        await cl.Message(content="❌ Invalid session").send()
        return

    # Store pending rename info and prompt user
    cl.user_session.set("pending_rename_session_id", session_id)
    cl.user_session.set("pending_rename_old_title", current_title)

    await cl.Message(
        content=f"✏️ Enter new name for chat '**{current_title}**':\n\n_(Type the new name and press Enter)_"
    ).send()


@cl.action_callback("delete_chat")
async def on_delete_chat(action: cl.Action):
    """Delete a chat session and its files."""
    session_id: Any | None = action.payload.get("session_id")
    user_id: int | None = auth.get_current_user_id()

    if not session_id or not user_id:
        await cl.Message(content="❌ Invalid session").send()
        return

    # Delete files first
    session_dir = Path("public") / str(user_id) / str(session_id)
    if session_dir.exists():
        shutil.rmtree(session_dir)

    # Then hard delete from database (cascades to messages and documents)
    pool = await get_pool()
    async with pool.acquire() as conn:
        success = await ChatSession.hard_delete(conn, int(session_id), user_id)
        if success:
            await cl.Message(content="✅ Chat deleted successfully").send()
            # Refresh the chat management UI
            await show_chat_management()
        else:
            await cl.Message(content="❌ Failed to delete chat").send()


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
    else:
        # User skipped file upload, create empty Gemini chat session
        gemini_chat = rag_manager.create_chat_session()
        cl.user_session.set("gemini_chat", gemini_chat)

        # Send confirmation message that chat is ready
        await cl.Message(
            content="✅ **Chat ready!** You can now ask questions without any documents."
        ).send()


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

        # Save document to database and update chat title to file name
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
            # Update chat title to file name
            await ChatSession.update_title(conn, chat_session_id, user_id, file.name)
            cl.user_session.set("chat_title", file.name)

        # Create Gemini chat session with the uploaded file
        chat_session = rag_manager.create_chat_session([gemini_file])
        cl.user_session.set("gemini_chat", chat_session)

        msg.content = f"✅ Processed `{file.name}` successfully!"
        await msg.update()

        # Auto-generate summary (internal prompt, not saved to database)
        initial_prompt = f"""Analyze the uploaded document '{file.name}'.
                                Provide a comprehensive summary using this format:

                                1. Start with a brief overview paragraph
                                2. Create section headers for main topics (use ## for headers)
                                3. Under each header, provide 2-3 bullet points with key insights
                                4. Include specific page references using (p. X) format
                                5. End with a conclusion section

                                Format the response with clear structure and include citations pointing to relevant sections."""
        response = chat_session.send_message(message=initial_prompt)

        # Save only the assistant's summary response (not the internal prompt)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await Message.create(
                conn, chat_session_id, "assistant", response.text or ""
            )

        file_path = get_citation_file_path(file.name)
        final_response = format_response_with_citations(response, file.name, file_path)
        await cl.Message(content=final_response).send()

    except Exception as e:
        msg.content = f"❌ Error processing file: {str(e)}"
        await msg.update()


def get_citation_file_path(source_document_name: Optional[str]) -> Optional[str]:
    """Get the full file path for citations in multi-user context.

    Parameters
    ----------
    source_document_name : Optional[str]
        The filename of the source document.

    Returns
    -------
    Optional[str]
        Full path in format "user_id/session_id/filename" or None.
    """
    if not source_document_name:
        return None

    user_id = auth.get_current_user_id()
    chat_session_id = cl.user_session.get("chat_session_id")

    if user_id and chat_session_id:
        return f"{user_id}/{chat_session_id}/{source_document_name}"
    return source_document_name


async def process_pending_rename(message: cl.Message, pending_session_id: Any):
    """Process a pending rename operation."""
    user_id: int | None = auth.get_current_user_id()
    new_title = message.content.strip()

    # Clear pending state
    cl.user_session.set("pending_rename_session_id", None)
    cl.user_session.set("pending_rename_old_title", None)

    if not user_id:
        await cl.Message(content="❌ Not authenticated").send()
        return

    if not new_title:
        await cl.Message(content="❌ Name cannot be empty").send()
        await show_chat_management()
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        success = await ChatSession.update_title(
            conn, int(pending_session_id), user_id, new_title
        )
        if success:
            await cl.Message(
                content=f"✅ Chat renamed to: **{new_title}**\n\n🔄 *Refresh this chat page using the browser's reload button.*"
            ).send()
        else:
            await cl.Message(content="❌ Failed to rename chat").send()

    # Refresh the chat management UI
    await show_chat_management()


@cl.on_message
async def main(message: cl.Message):
    """Process user messages and file attachments with database persistence."""

    # Check for registration flow
    registration_step = cl.user_session.get("registration_step")
    if registration_step:
        await _handle_registration_step(registration_step, message.content.strip())
        return

    # Check pending chat rename operation
    pending_session_id = cl.user_session.get("pending_rename_session_id")
    if pending_session_id:
        await process_pending_rename(message, pending_session_id)
        return

    # --- Main Chat Processing ---
    chat_session_id = cl.user_session.get("chat_session_id")

    if not chat_session_id:
        await cl.Message(
            content="❌ No active chat session. Please create or load a chat first."
        ).send()
        return

    # Handle file attachments first
    if message.elements:
        for element in message.elements:
            if (
                element.mime
                and ("pdf" in element.mime or "text" in element.mime)
                and element.path
            ):
                await process_uploaded_file(element)

    # Handle text message if present
    if message.content:
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
            file_path = get_citation_file_path(doc_filename)
            final_response = format_response_with_citations(
                response, doc_filename, file_path
            )
            await cl.Message(content=final_response).send()

        except Exception as e:
            error_msg = f"❌ An error occurred: {str(e)}"
            await cl.Message(content=error_msg).send()


@cl.on_stop
def on_stop():
    """Handle session stop."""
    logger.info("Chat session stopped")


@cl.on_chat_end
async def on_chat_end():
    """Handle chat end."""
    logger.info("Chat session ended")
