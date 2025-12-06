# Application Lifecycle and User Operation Flow for `app_multiuser.py`

This document outlines the function call flow within `app_multiuser.py` when it's run by the Chainlit framework. The application's execution is event-driven, orchestrated by Chainlit decorators like `@cl.on_chat_start`, `@cl.on_message`, and `@cl.action_callback`.

The diagrams below illustrate the sequence of function calls for major user operations.

---

### 1. Initial Load & Chat Profile Selection

When a user first opens the chat, Chainlit prepares the initial screen by asking the application for a list of "chat profiles."

```mermaid
sequenceDiagram
    participant C as Chainlit UI
    participant F as app_multiuser.py
    participant DB as Database

    C->>F: Triggers @cl.set_chat_profiles
    F->>F: chat_profile(current_user)
    Note over F: Gets user_id from current_user
    F->>DB: ChatSession.list_by_user(user_id)
    DB-->>F: Returns list of recent sessions
    Note over F: Builds list of profiles:<br/>- Recent chats<br/>- "new_chat"<br/>- "manage_chats"
    F-->>C: Returns list of cl.ChatProfile objects
    C->>C: Renders the chat profile selection screen
```

**Flow Description:**

1. **`chat_profile()`**: This function is called by Chainlit to populate the initial "chat profile" selection screen.
2. It fetches the user's recent chat sessions from the database.
3. It then constructs and returns a list of `cl.ChatProfile` objects, which includes recent chats and static options like "New Chat" and "Manage Chats".

---

### 2. Starting a Chat Session

After the user selects a profile from the initial screen, the `@cl.on_chat_start` event is triggered, which calls the `start()` function to route the user to the correct flow.

```mermaid
sequenceDiagram
    participant C as Chainlit UI
    participant F as app_multiuser.py

    C->>F: User selects a profile, triggers @cl.on_chat_start
    F->>F: start()
    Note over F: Checks if user is authenticated
    
    alt New User Registration
        F->>F: _handle_registration(user)
        Note over F: Sends welcome messages and prompts for username.<br/>Waits for user input.
    else Existing User
        F->>F: Gets selected chat_profile
        
        alt Profile is "new_chat"
            F->>F: create_new_chat_flow()
            Note over F: Creates DB session, sets session variables,<br/>creates Gemini chat, sends confirmation.
        
        else Profile is "manage_chats"
            F->>F: show_chat_management()
            Note over F: Fetches all chats and displays them with<br/>Load, Rename, Delete action buttons.
        
        else Profile is a recent chat
            F->>F: load_chat_by_profile_name(profile_name)
            F->>F: load_chat_by_id(session_id)
            Note over F: Fetches messages/docs, recreates Gemini session,<br/>and displays chat history.
        
        else No profile selected (first time user)
            F->>F: load_or_create_chat()
            Note over F: Tries to load most recent chat, otherwise<br/>calls create_new_chat_flow().
        end
    end
```

**Flow Description:**

1. **`start()`**: The main entry point for a chat. It routes the user based on the selected profile.
2. **`_handle_registration()`**: If the user is new (`registration_pending` is true), this function initiates a conversational registration process.
3. **`create_new_chat_flow()`**: Called when the user explicitly selects "New Chat".
4. **`show_chat_management()`**: Displays an interface for managing existing chats.
5. **`load_chat_by_profile_name()` / `load_chat_by_id()`**: These work together to load a past conversation, including its history and any associated documents.

---

### 3. User Sends a Message or File

Once a chat is active, any user input (a text message or a file upload) triggers the `@cl.on_message` event, which calls the `main()` function.

```mermaid
sequenceDiagram
    participant C as Chainlit UI
    participant F as app_multiuser.py
    participant DB as Database
    participant Gemini as Gemini API

    C->>F: User sends a message/file, triggers @cl.on_message
    F->>F: main(message)
    
    alt Registration in progress
        F->>F: _handle_registration_step(step, message.content)
        Note over F: Processes one step of registration (username, email, etc.)<br/>and prompts for the next.
    
    else Rename in progress
        F->>F: process_pending_rename(message, session_id)
        Note over F: Updates chat title in DB and refreshes<br/>the management UI.
    
    else Normal Chat Message/File
        Note over F: Gets active chat_session_id
        
        alt Message has a file
            F->>F: process_uploaded_file(element)
            Note over F: Saves file, uploads to Gemini, updates DB,<br/>and auto-generates a summary.
        end

        alt Message has text
            Note over F: Gets/creates Gemini chat session
            F->>DB: Message.create(user_message)
            F->>Gemini: gemini_chat.send_message(...)
            Gemini-->>F: Returns assistant response
            F->>DB: Message.create(assistant_response)
            F->>F: get_citation_file_path(...)
            F->>F: format_response_with_citations(...)
            F-->>C: Sends formatted response to UI
        end
    end
```

**Flow Description:**

1. **`main(message)`**: The central handler for all incoming user messages. It first checks for special states like registration or renaming.
2. **`_handle_registration_step()`**: A state machine that guides the user through each step of creating an account.
3. **`process_pending_rename()`**: Handles the input for a rename request initiated from the management screen.
4. **`process_uploaded_file()`**: Manages file uploads, including saving the file, processing it with the RAG system, and generating an initial summary.
5. If it's a standard text message, `main()` saves the user's query, sends it to the Gemini model, saves the assistant's response, and formats it for display.

---

### 4. User Interacts with Chat Management Actions

When the user is in the "Manage Chats" view, they can click an action button (Load, Rename, Delete), which triggers a corresponding `@cl.action_callback` function.

```mermaid
sequenceDiagram
    participant C as Chainlit UI
    participant F as app_multiuser.py
    participant DB as Database

    C->>F: User clicks "Load Chat", triggers @cl.action_callback("load_chat")
    F->>F: on_load_chat(action)
    F->>F: load_chat_by_id(session_id)
    Note over F: Loads chat history and documents.
    
    C->>F: User clicks "Rename Chat", triggers @cl.action_callback("rename_chat")
    F->>F: on_rename_chat(action)
    Note over F: Sets session state for pending rename<br/>and prompts user for new name.
    
    C->>F: User clicks "Delete Chat", triggers @cl.action_callback("delete_chat")
    F->>F: on_delete_chat(action)
    Note over F: Deletes files from storage.
    F->>DB: ChatSession.hard_delete(session_id)
    DB-->>F: Confirms deletion
    F->>F: show_chat_management()
    Note over F: Refreshes the management UI.
```

**Flow Description:**

1. **`on_load_chat()`**: Triggered by the "Load" button. It calls `load_chat_by_id()` to switch to the selected chat.
2. **`on_rename_chat()`**: Triggered by the "Rename" button. It sets a "pending rename" state, waiting for the user's next message to be the new title.
3. **`on_delete_chat()`**: Triggered by the "Delete" button. It handles the complete removal of a chat session and its associated data, then refreshes the management list by calling `show_chat_management()`.
