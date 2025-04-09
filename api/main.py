1from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from tinyagent.logging import get_logger
from .routers import tools
import os

logger = get_logger(__name__)

app = FastAPI()

# Include the chat router with /api prefix
app.include_router(tools.router, prefix="/api")

# Serve chat.html as the main interface at the root path
@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Read the chat.html file from the static directory
    static_dir = os.path.join(os.getcwd(), "static")
    chat_path = os.path.join(static_dir, "chat.html")
    
    if os.path.exists(chat_path):
        with open(chat_path, "r") as f:
            content = f.read()
        return content
    else:
        return "<html><body><h1>Chat Interface Not Found</h1><p>The chat interface file (chat.html) could not be found.</p></body></html>"

# Serve static files
static_dir = os.path.join(os.getcwd(), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


