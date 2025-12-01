# Multi-User RAG Application Architecture

## 🏗️ System Overview

This is a multi-user Retrieval-Augmented Generation (RAG) application built with:

- **Frontend**: Chainlit (React-based chat UI)
- **Backend**: Python with asyncio
- **Database**: PostgreSQL with asyncpg
- **AI**: Google Gemini API
- **Authentication**: Chainlit password auth with custom callbacks

## 📊 Architecture Diagram

```architecture
┌─────────────────────────────────────────────────────────────┐
│                         Browser                             │
│                    (Chainlit React UI)                      │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket + HTTP
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Chainlit Server                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Auth       │  │   Session    │  │   File       │       │
│  │   Handler    │  │   Manager    │  │   Upload     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ PostgreSQL  │  │   Gemini    │  │   File      │
│  Database   │  │     API     │  │  Storage    │
│             │  │             │  │  (public/)  │
│ - users     │  │ - Upload    │  │             │
│ - sessions  │  │ - Chat      │  │ /user_id/   │
│ - messages  │  │ - RAG       │  │ /session_id/│
│ - documents │  │             │  │ /file.pdf   │
└─────────────┘  └─────────────┘  └─────────────┘
```

## 📁 File Structure

```project
google-gemini-api-rag/
├── app.py                  # single-user app
├── app_multiuser.py        # Multi-user version
├── auth.py                 # Authentication module
├── database.py             # Database connection & schema
├── models.py               # Database models (User, ChatSession, Message, Document)
├── rag_manager.py          # Gemini API integration
├── setup_db.py             # Database initialization script
├── config.toml             # Chainlit configuration
├── .env                    # Environment variables
├── pyproject.toml          # Dependencies
├── QUICKSTART.md           # Quick start guide
├── SETUP_MULTIUSER.md      # Detailed setup guide
└── ARCHITECTURE.md         # This file
```

## 🔐 Authentication Flow

```auth-flow
1. User opens browser → Chainlit shows login page
2. User enters username/password
3. Chainlit calls auth_callback() in auth.py
4. auth.py queries PostgreSQL users table
5. Password verified with hash comparison
6. If valid: Create cl.User object with metadata
7. User session established with user_id
```

## 💬 Chat Session Flow

```chat-flow
1. User logs in → Welcome screen
2. User clicks "New Chat" or "My Chats"
3. New Chat:
   - Prompt for title
   - Create record in chat_sessions table
   - Store session_id in cl.user_session
   - Prompt for file upload (optional)
4. Load Existing Chat:
   - Fetch chat_sessions for user_id
   - Display list with action buttons
   - User selects chat → Load session_id
   - Fetch messages from database
   - Restore Gemini chat context
```

## 📝 Message Flow

```message-flow
1. User sends message
2. Save to messages table (role='user')
3. Send to Gemini API with chat context
4. Receive response from Gemini
5. Save to messages table (role='assistant')
6. Display formatted response with citations
7. Update chat_sessions.updated_at timestamp
```

## 📄 Document Upload Flow

```document-flow
1. User uploads PDF/text file
2. Save to public/{user_id}/{session_id}/{filename}
3. Upload to Gemini API
4. Wait for Gemini processing (ACTIVE state)
5. Save metadata to documents table:
   - filename, file_path
   - gemini_file_uri, gemini_file_name
   - mime_type, file_size
6. Create/update Gemini chat session with file context
7. Auto-generate document summary
8. Save summary messages to database
```

## 🗄️ Database Schema

### users

```sql
id              SERIAL PRIMARY KEY
username        VARCHAR(255) UNIQUE NOT NULL
email           VARCHAR(255) UNIQUE NOT NULL
password_hash   VARCHAR(255) NOT NULL
created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
last_login      TIMESTAMP
```

### chat_sessions

```sql
id          SERIAL PRIMARY KEY
user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE
title       VARCHAR(500) NOT NULL
created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
is_deleted  BOOLEAN DEFAULT FALSE
```

### messages

```sql
id               SERIAL PRIMARY KEY
chat_session_id  INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE
role             VARCHAR(50) NOT NULL  -- 'user' or 'assistant'
content          TEXT NOT NULL
created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### documents

```sql
id               SERIAL PRIMARY KEY
chat_session_id  INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE
filename         VARCHAR(500) NOT NULL
file_path        VARCHAR(1000) NOT NULL
gemini_file_uri  VARCHAR(1000)
gemini_file_name VARCHAR(500)
mime_type        VARCHAR(100)
file_size        INTEGER
uploaded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

## 🔒 Security Features

1. **Password Hashing**: SHA-256 with random salt
2. **User Isolation**: All queries filter by user_id
3. **Soft Deletes**: Chat sessions marked as deleted, not removed
4. **Session Management**: Chainlit handles WebSocket sessions
5. **File Isolation**: Files stored in user-specific directories

## 🚀 Scalability Considerations

### Current Implementation

- Single PostgreSQL instance
- Local file storage
- In-memory Gemini chat sessions

### Future Enhancements

- **Database**: PostgreSQL replication, connection pooling
- **File Storage**: S3/Cloud Storage for documents
- **Caching**: Redis for session data
- **Load Balancing**: Multiple Chainlit instances
- **Message Queue**: Celery for async document processing

## 🔄 Data Flow Example

### User asks: "What is the main topic of the document?"

```data-flow
1. Browser → WebSocket → Chainlit Server
2. app_multiuser.py → main() function
3. Get chat_session_id from cl.user_session
4. Save message to PostgreSQL:
   INSERT INTO messages (chat_session_id, role, content)
   VALUES (123, 'user', 'What is the main topic...')
5. Get gemini_chat from cl.user_session
6. Send to Gemini API:
   chat.send_message("What is the main topic...")
7. Receive response from Gemini
8. Save response to PostgreSQL:
   INSERT INTO messages (chat_session_id, role, content)
   VALUES (123, 'assistant', 'The main topic is...')
9. Format response with citations
10. Send to browser via WebSocket
11. Display in chat UI
```

## 📈 Performance Optimization

1. **Database Indexes**: On user_id, chat_session_id
2. **Connection Pooling**: asyncpg pool (default 10 connections)
3. **Async Operations**: All I/O operations are async
4. **Lazy Loading**: Messages loaded only when chat is opened
5. **File Streaming**: Large files streamed, not loaded in memory

## 🧪 Testing Strategy

1. **Unit Tests**: Test models, auth functions
2. **Integration Tests**: Test database operations
3. **E2E Tests**: Test full user flows
4. **Load Tests**: Test concurrent users

## 📦 Deployment Options

1. **Local**: Current setup (development)
2. **Docker**: Containerize app + PostgreSQL
3. **Cloud**: Deploy to Heroku, AWS, GCP, Azure
4. **Kubernetes**: For high availability

See deployment guides (coming soon) for details.
