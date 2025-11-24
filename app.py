import chainlit as cl
import rag_manager
import os
from pathlib import Path

# Global variable to store the chat session
# In Chainlit, we usually store session data in cl.user_session

@cl.on_chat_start
async def start():
    files = None
    
    # Ask user to upload a file
    files_uploaded = await cl.AskFileMessage(
        content="Please upload a text or PDF file to begin!", 
        accept=["text/plain", "application/pdf"],
        max_size_mb=20,
        timeout=180
    ).send()

    if files_uploaded:
        text_file = files_uploaded[0]
        
        msg = cl.Message(content=f"Processing `{text_file.name}`...")
        await msg.send()

        # Save file locally temporarily to upload to Gemini
        # Chainlit files are in memory or temp, let's ensure we have a path
        temp_path = Path(f"./tmp_{text_file.name}")
        with open(temp_path, "wb") as f:
            with open(text_file.path, "rb") as src:
                f.write(src.read())

        try:
            # Upload to Gemini
            gemini_file = rag_manager.upload_file(str(temp_path))
            rag_manager.wait_for_files_active([gemini_file])
            
            # Create Chat Session
            chat_session = rag_manager.create_chat_session([gemini_file])
            cl.user_session.set("chat_session", chat_session)
            
            msg.content = f"Processing `{text_file.name}` done. You can now ask questions!"
            await msg.update()
            
        except Exception as e:
            msg.content = f"Error processing file: {str(e)}"
            await msg.update()
        finally:
            # Cleanup temp file
            if temp_path.exists():
                os.remove(temp_path)

@cl.on_message
async def main(message: cl.Message):
    chat_session = cl.user_session.get("chat_session")
    
    if not chat_session:
        await cl.Message(content="No active session. Please restart and upload a file.").send()
        return

    # Send message to Gemini
    response = chat_session.send_message(message.content)
    
    # Stream back the response (Gemini supports streaming, but for simplicity we'll just send the text first)
    # To implement streaming properly with Chainlit + Gemini:
    # response = chat_session.send_message(message.content, stream=True)
    # msg = cl.Message(content="")
    # for chunk in response:
    #     await msg.stream_token(chunk.text)
    # await msg.send()
    
    await cl.Message(content=response.text).send()
