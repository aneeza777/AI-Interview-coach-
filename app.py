"""
AI Interview Coach — Cloud Entry Point
======================================
Serves the full custom web application (FastAPI + HTML/CSS/JS frontend)
with ZeroGPU acceleration and Gradio SDK compatibility.
"""

import os
import sys
import html
from pathlib import Path

# Ensure ZeroGPU detection passes during container initialization
try:
    import spaces
    HAS_SPACES = True
except ImportError:
    HAS_SPACES = False
    class _MockSpaces:
        def GPU(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    spaces = _MockSpaces()

@spaces.GPU
def _zero_gpu_startup():
    """Satisfy Hugging Face ZeroGPU orchestrator startup scan."""
    return True

_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "backend"))

from starlette.routing import Route
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import gradio as gr
from backend.main import app as fastapi_app, FRONTEND_DIR, init_db

# 1. Initialize database tables
init_db()

# 2. Gradio container setup (allows HF Spaces Gradio SDK to detect, orchestrate, and launch)
with gr.Blocks(
    title="AI Interview Coach | Alibaba Cloud AI Hackathon 2026",
) as demo:
    gr.HTML("<div style='text-align:center;padding:2rem;color:#94a3b8;'>AI Interview Coach is running...</div>")

# 3. Direct Root & Static Serving (Eliminates iframe completely for 100% native mobile mic access & responsive layout)
async def custom_root_endpoint(request):
    return FileResponse(str(FRONTEND_DIR / "index.html"))

# Prioritize our custom root routes at index 0 of demo.app router
demo.app.router.routes.insert(0, Route("/", custom_root_endpoint, methods=["GET"]))
demo.app.router.routes.insert(0, Route("/index.html", custom_root_endpoint, methods=["GET"]))

# Mount static directories directly on demo.app
demo.app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="frontend_css")
demo.app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="frontend_js")
demo.app.mount("/web", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend_web")

# 4. Attach all FastAPI backend endpoints (/api/auth, /api/interviews, /api/resumes, etc.)
demo.app.include_router(fastapi_app.router)

if __name__ == "__main__":
    demo.queue().launch(show_error=True)
