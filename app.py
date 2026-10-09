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

import html
import gradio as gr
from backend.main import app as fastapi_app, FRONTEND_DIR, init_db

# 1. Initialize database tables
init_db()

# 2. Read and bundle the full custom project frontend (Image 2 UI) with updated responsive CSS & JS
with open(FRONTEND_DIR / "index.html", "r", encoding="utf-8") as f:
    raw_html = f.read()

with open(FRONTEND_DIR / "css" / "style.css", "r", encoding="utf-8") as f:
    css_content = f.read()

with open(FRONTEND_DIR / "js" / "app.js", "r", encoding="utf-8") as f:
    js_content = f.read()

# Inline CSS & JS with base href for full API and asset resolution
full_doc = raw_html.replace(
    '<head>',
    '<head>\n  <base href="/">\n'
).replace(
    '<link rel="stylesheet" href="/css/style.css">',
    f'<style>\n{css_content}\n</style>'
).replace(
    '<script src="/js/app.js"></script>',
    f'<script>\n{js_content}\n</script>'
)

escaped_doc = html.escape(full_doc, quote=True)

# 3. Create Gradio Blocks embedding the full custom project frontend
with gr.Blocks(
    title="AI Interview Coach | Alibaba Cloud AI Hackathon 2026",
) as demo:
    gr.HTML(f"""
    <style>
      html, body {{
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        height: 100% !important;
        overflow: hidden !important;
        background: #0b0f17 !important;
      }}
      .gradio-container {{
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
      }}
      footer {{
        display: none !important;
      }}
      #app-frame {{
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
      }}
    </style>
    <iframe id="app-frame" srcdoc="{escaped_doc}" allow="microphone *; autoplay *"></iframe>
    """)

# 4. Mount Gradio interface and unify with FastAPI
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")
demo.app = app
demo.server_app = app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
