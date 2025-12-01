# Multi-User RAG Application Setup Guide

This guide will help you set up the multi-user version of the Gemini RAG application with PostgreSQL database, user authentication, and chat session management.

## Features

✅ **User Authentication** - Register and login with username/password  
✅ **Multi-User Support** - Each user has their own isolated chat sessions  
✅ **Chat Session Management** - Create, list, delete, and switch between chats  
✅ **Data Persistence** - All messages and documents stored in PostgreSQL  
✅ **Document Management** - Upload and manage documents per chat session  
✅ **Secure** - Password hashing, user isolation, and session management  

## Prerequisites

1. **Python 3.13+**
2. **PostgreSQL 12+** installed and running
3. **Google Gemini API Key** - Get it from [Google AI Studio](https://aistudio.google.com/app/apikey)

## Step 1: Install PostgreSQL

### Windows

1. Download PostgreSQL from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run the installer and follow the setup wizard
3. Remember the password you set for the `postgres` user
4. Default port is `5432`

### macOS

```bash
brew install postgresql@15
brew services start postgresql@15
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

## Step 2: Create Database and Grant Permissions

Open PostgreSQL command line (psql):

```bash
# Windows: Use "SQL Shell (psql)" from Start Menu
# macOS/Linux:
psql -U postgres
```

Create the database and grant all necessary permissions (including schema permissions for PostgreSQL 15+):

```sql
-- Create database and user
CREATE DATABASE gemini_rag;
CREATE USER gemini_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE gemini_rag TO gemini_user;

-- Connect to the new database to grant schema permissions
\c gemini_rag

-- Grant schema permissions (required for PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO gemini_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gemini_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gemini_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO gemini_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO gemini_user;
\q
```

Or run as a single command:

```bash
psql -U postgres -c "CREATE DATABASE gemini_rag; CREATE USER gemini_user WITH PASSWORD 'your_secure_password'; GRANT ALL PRIVILEGES ON DATABASE gemini_rag TO gemini_user;" && psql -U postgres -d gemini_rag -c "GRANT ALL ON SCHEMA public TO gemini_user; GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gemini_user; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gemini_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO gemini_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO gemini_user;"
```

> **Note**: The schema permissions are required for PostgreSQL 15+. Without them, you'll get an "Access denied to schema public" error when running `setup_db.py`.

## Step 3: Configure Environment Variables

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Generate a JWT secret for authentication:

   ```bash
   chainlit create-secret
   ```

3. Edit `.env` and add your credentials (use the secret generated above):

   ```env
   GOOGLE_API_KEY=your_actual_gemini_api_key
   # Use DB_URL (not DATABASE_URL) to avoid Chainlit auto-detecting it
   DB_URL=postgresql://gemini_user:your_secure_password@localhost:5432/gemini_rag
   CHAINLIT_AUTH_SECRET=your_generated_secret_here
   ```

## Step 4: Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

## Step 5: Initialize Database

Run the setup script to create tables and admin user:

```bash
python setup_db.py
```

This will:

- Create all necessary database tables (users, chat_sessions, messages, documents)
- Prompt you to create an admin user account

Example:

```
Enter admin username: admin
Enter admin email: admin@example.com
Enter admin password: ********
Confirm password: ********
✅ Admin user created successfully!
```

## Step 6: Run the Application

```bash
chainlit run app.py -w
```

The application will start at `http://localhost:8000`

## Step 7: Login and Use

1. Open `http://localhost:8000` in your browser
2. Login with the admin credentials you created
3. Start chatting and uploading documents!

## Database Schema

### Tables

**users**

- `id` - Primary key
- `username` - Unique username
- `email` - Unique email
- `password_hash` - Hashed password
- `created_at` - Account creation timestamp
- `last_login` - Last login timestamp

**chat_sessions**

- `id` - Primary key
- `user_id` - Foreign key to users
- `title` - Session title
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `is_deleted` - Soft delete flag

**messages**

- `id` - Primary key
- `chat_session_id` - Foreign key to chat_sessions
- `role` - 'user' or 'assistant'
- `content` - Message text
- `created_at` - Timestamp

**documents**

- `id` - Primary key
- `chat_session_id` - Foreign key to chat_sessions
- `filename` - Original filename
- `file_path` - Storage path
- `gemini_file_uri` - Gemini API URI
- `gemini_file_name` - Gemini API name
- `mime_type` - File MIME type
- `file_size` - Size in bytes
- `uploaded_at` - Upload timestamp

## Troubleshooting

### Database Connection Error

- Check if PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL in `.env` is correct
- Ensure database and user exist

### Authentication Not Working

- Make sure `auth.py` is imported in `app.py`
- Check if user exists in database
- Verify password is correct

### Port Already in Use

```bash
# Change port in chainlit command
chainlit run app.py -w --port 8001
```

### "Access denied to schema public" Error (PostgreSQL 15+)

This error occurs when the database user doesn't have permissions on the `public` schema. PostgreSQL 15 changed the default permissions for security reasons.

**Solution**: Run the schema permission grant commands from Step 2, or use the helper script:

```bash
# Option 1: Use the helper script
python grant_permissions.py

# Option 2: Run psql command directly
psql -U postgres -d gemini_rag -c "GRANT ALL ON SCHEMA public TO gemini_user; GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gemini_user; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gemini_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO gemini_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO gemini_user;"
```

## Next Steps

Now you can implement the updated `app.py` with:

- Chat session management UI
- Document persistence
- Message history loading
- User profile management

See the implementation in the updated `app.py` file.
