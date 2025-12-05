# Quick Start Guide - Multi-User RAG Application

## 🚀 Get Started in 5 Minutes

### 1. Install PostgreSQL

**Windows (Quick):**

```powershell
# Download and install from: https://www.postgresql.org/download/windows/
# Or use Chocolatey:
choco install postgresql
```

**macOS:**

```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux:**

```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database and Grant Permissions

```bash
# Connect to PostgreSQL
psql -U postgres

# In psql, create database and user:
CREATE DATABASE gemini_rag;
CREATE USER gemini_user WITH PASSWORD 'changeme123';
GRANT ALL PRIVILEGES ON DATABASE gemini_rag TO gemini_user;

# Connect to the new database to grant schema permissions (required for PostgreSQL 15+)
\c gemini_rag

# Grant schema permissions:
GRANT ALL ON SCHEMA public TO gemini_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gemini_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gemini_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO gemini_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO gemini_user;
\q
```

Or run as a single command:

```bash
psql -U postgres -c "CREATE DATABASE gemini_rag; CREATE USER gemini_user WITH PASSWORD 'changeme123'; GRANT ALL PRIVILEGES ON DATABASE gemini_rag TO gemini_user;" && psql -U postgres -d gemini_rag -c "GRANT ALL ON SCHEMA public TO gemini_user; GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gemini_user; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gemini_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO gemini_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO gemini_user;"
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Generate JWT secret for authentication
chainlit create-secret

# Edit .env with your credentials
# Windows: notepad .env
# macOS/Linux: nano .env
```

Add (use the secret generated above):

```env
GOOGLE_API_KEY=your_gemini_api_key_here
# Use DB_URL (not DATABASE_URL) to avoid Chainlit auto-detecting it
DB_URL=postgresql://gemini_user:changeme123@localhost:5432/gemini_rag
CHAINLIT_AUTH_SECRET=your_generated_secret_here
```

### 4. Install Dependencies

```bash
uv sync
```

### 5. Initialize Database

```bash
python setup_db.py
```

Follow prompts to create admin user:

```
Enter admin username: admin
Enter admin email: admin@example.com
Enter admin password: admin123
Confirm password: admin123
```

### 6. Run Application

```bash
chainlit run app_multiuser.py -w
```

### 7. Open Browser

Navigate to: `http://localhost:8000`

Login with your admin credentials!

## 📋 Features Available

✅ **User Authentication** - Secure login/registration  
✅ **Multiple Chat Sessions** - Create unlimited chats  
✅ **Document Upload** - PDF and text files  
✅ **Message History** - All conversations saved  
✅ **Chat Management** - Create, list, delete chats  
✅ **Citations** - Clickable page references  

## 🎯 Usage Flow

1. **Login** with your credentials
2. **Create New Chat** - Click "📝 New Chat"
3. **Upload Document** - Upload PDF or text file
4. **Ask Questions** - Chat with your documents
5. **Switch Chats** - Click "📋 My Chats" to see all sessions
6. **Load Previous Chat** - Click on any chat to continue

## 🔧 Troubleshooting

### Can't connect to database?

```bash
# Check if PostgreSQL is running
pg_isready

# Restart PostgreSQL
# Windows: Services → PostgreSQL → Restart
# macOS: brew services restart postgresql@15
# Linux: sudo systemctl restart postgresql
```

### Port 8000 already in use?

```bash
chainlit run app_multiuser.py -w --port 8001
```

### Authentication not working?

- Verify user exists: `psql -U gemini_user -d gemini_rag -c "SELECT * FROM users;"`
- Check password is correct
- Ensure `auth.py` is imported in `app_multiuser.py`

### "Access denied to schema public" error?

This error occurs on PostgreSQL 15+ when schema permissions are not granted. Run the grant commands from step 2, or use the helper script:

```bash
# Option 1: Use the helper script
python grant_permissions.py

# Option 2: Run psql command directly
psql -U postgres -d gemini_rag -c "GRANT ALL ON SCHEMA public TO gemini_user; GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gemini_user; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gemini_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO gemini_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO gemini_user;"
```

## 📚 Next Steps

- **Add more users**: Run `python setup_db.py` again
- **Customize UI**: Edit `config.toml`
- **Add features**: Modify `app_multiuser.py`
- **Deploy**: See deployment guide (coming soon)

## 🆘 Need Help?

Check the detailed setup guide: `SETUP_MULTIUSER.md`
