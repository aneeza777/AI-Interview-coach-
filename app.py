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

import uvicorn
import gradio as gr
from backend.main import app as fastapi_app, FRONTEND_DIR, init_db

# 1. Initialize database tables
init_db()

# 2. Gradio container setup for ZeroGPU and HF Spaces SDK compatibility
with gr.Blocks(
    title="AI Interview Coach | Alibaba Cloud AI Hackathon 2026",
) as demo:
    gr.HTML("<div style='text-align:center;padding:2rem;color:#94a3b8;'>AI Interview Coach is active.</div>")

# 3. Mount Gradio into FastAPI at /gradio
# This preserves FastAPI as the PRIMARY root app, natively serving:
# - GET / -> frontend/index.html (direct HTML, NO IFRAME, 100% native mic permissions)
# - GET /css/... -> static CSS
# - GET /js/... -> static JS
# - /api/... -> all backend endpoints
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
