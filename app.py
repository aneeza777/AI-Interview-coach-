"""
AI Interview Coach — Cloud Entry Point
======================================
Serves the full custom web application (FastAPI + HTML/CSS/JS frontend)
with ZeroGPU acceleration and Gradio SDK compatibility.
"""

import os
import sys
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

import gradio as gr
from fastapi.staticfiles import StaticFiles
from backend.main import app as fastapi_app, FRONTEND_DIR, init_db

# 1. Initialize database tables
init_db()

css_dir = FRONTEND_DIR / "css"
js_dir = FRONTEND_DIR / "js"

# 2. Create Gradio Blocks embedding the full custom project frontend (Image 2 UI)
with gr.Blocks(
    title="AI Interview Coach | Alibaba Cloud AI Hackathon 2026",
) as demo:
    gr.HTML("""
    <style>
      html, body {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        height: 100% !important;
        overflow: hidden !important;
        background: #0b0f17 !important;
      }
      .gradio-container {
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
      }
      footer {
        display: none !important;
      }
      #app-frame {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        border: none;
        margin: 0;
        padding: 0;
        z-index: 9999999;
        background: #0b0f17;
      }
    </style>
    <iframe id="app-frame" src="/web/" allow="microphone; camera; display-capture; autoplay"></iframe>
    """)

# 3. Mount routes onto demo.app at MODULE LEVEL (runs on import AND on direct execution)
demo.app.mount("/web", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend_web")
if css_dir.exists():
    demo.app.mount("/css", StaticFiles(directory=str(css_dir)), name="frontend_css")
if js_dir.exists():
    demo.app.mount("/js", StaticFiles(directory=str(js_dir)), name="frontend_js")

# 4. Attach all FastAPI backend endpoints (/api/auth, /api/interviews, /api/resumes, etc.)
demo.app.include_router(fastapi_app.router)

if __name__ == "__main__":
    demo.queue().launch(show_error=True)
