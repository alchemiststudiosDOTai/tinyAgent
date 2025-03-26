from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from .config import get_api_config
from .routers import tools
from .dependencies import get_agent_factory
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core.logging import get_logger
import os

logger = get_logger(__name__)

config = get_api_config()

app = FastAPI(
    title=config["app_name"],
    docs_url="/docs" if config["enable_docs"] else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers without prefix to maintain compatibility
app.include_router(tools.router)

# Also include with /api prefix for better organization
app.include_router(tools.router, prefix="/api")

# Serve chat.html as the main interface at the root path
@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Read the chat.html file from the static directory
    static_dir = os.path.join(os.getcwd(), "static")  # Use current working directory
    chat_path = os.path.join(static_dir, "chat.html")
    
    # Debug information
    logger.info(f"Looking for chat.html at: {chat_path}")
    logger.info(f"File exists: {os.path.exists(chat_path)}")
    
    if os.path.exists(chat_path):
        with open(chat_path, "r") as f:
            content = f.read()
        logger.info(f"Serving chat interface from root path using {chat_path}")
        return content
    else:
        # Try absolute path as fallback
        abs_path = "/home/fabian/tinyAgent/static/chat.html"
        if os.path.exists(abs_path):
            with open(abs_path, "r") as f:
                content = f.read()
            logger.info(f"Serving chat interface from root path using absolute path: {abs_path}")
            return content
        else:
            logger.warning(f"Chat interface not found at {chat_path} or {abs_path}")
            return "<html><body><h1>Chat Interface Not Found</h1><p>The chat interface file (chat.html) could not be found.</p></body></html>"

# Note: We're now serving the chat interface at the root path, so this route is no longer needed

# Add a debug endpoint
@app.get("/debug", response_class=JSONResponse)
async def debug_info():
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    return {
        "static_dir": static_dir,
        "static_dir_exists": os.path.exists(static_dir),
        "index_path": index_path,
        "index_exists": os.path.exists(index_path),
        "cwd": os.getcwd(),
    }

# Determine the static directory path
static_dir = os.path.join(os.getcwd(), "static")  # Use current working directory

# Debug information
logger.info(f"Static directory path: {static_dir}")
logger.info(f"Static directory exists: {os.path.exists(static_dir)}")

if os.path.exists(static_dir):
    # Serve static files
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Mounted static files from {static_dir}")
else:
    # Try absolute path as fallback
    abs_static_dir = "/home/fabian/tinyAgent/static"
    if os.path.exists(abs_static_dir):
        app.mount("/static", StaticFiles(directory=abs_static_dir), name="static")
        logger.info(f"Mounted static files from absolute path: {abs_static_dir}")
    else:
        logger.warning(f"Static directory not found at {static_dir} or {abs_static_dir}")

@app.on_event("startup")
async def init_factory():
    # Warm up agent factory
    factory = get_agent_factory()
    factory.list_tools()  # Force initialization (sync call)
    logger.info("Agent factory initialized with %d tools", len(factory.list_tools()))
