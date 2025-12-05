# Gemini RAG Agent

A Python-based RAG application using **Chainlit** and **Gemini API**.

## Prerequisites

1. **API Key**: You need a Google Gemini API Key.
    - Get it here: [Google AI Studio](https://aistudio.google.com/app/apikey)
    - Open the `.env.example` file in your project folder: `c:\path-to-project\google-gemini-api-rag\.env`
    - Paste your key: `GOOGLE_API_KEY=your_actual_key_here`
    - DB_URL=postgresql://gemini_user:your_secure_password@localhost:5432/gemini_rag
    - CHAINLIT_AUTH_SECRET=your_generated_secret_here
    - Rename the file to `.env`

## How to Run

1. Open your terminal in VS Code.
2. Run the following command:

    ```bash
    chainlit run app.py -w
    ```

3. A new browser tab should open automatically (usually at `http://localhost:8000`).

## How to Use

1. **Upload**: The chat interface will ask you to upload a file (PDF or Text).
2. **Auto-Summary**: The app will automatically process the file and display a **summary with citations** immediately.
3. **Chat**: You can then continue to ask specific questions like:
    - "What are the key takeaways?"
    - "Find the section about X."

## Troubleshooting

- **API Key Error**: If you see an error about the API key, double-check your `.env` file and ensure you saved it.
- **Dependencies**: If `chainlit` is not found, try running `uv sync` or `uv pip install -r pyproject.toml` (if generated) or just `uv add chainlit google-generativeai python-dotenv` again.
