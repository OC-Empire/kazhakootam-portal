import sys, os, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    from main import app
except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()
    err = traceback.format_exc()
    @app.get("/{path:path}")
    async def debug(path=""):
        return JSONResponse({"error": str(e), "trace": err, "root": ROOT, "syspath": sys.path, "files": os.listdir(ROOT)}, status_code=500)
    @app.post("/{path:path}")
    async def debugp(path=""):
        return JSONResponse({"error": str(e), "trace": err}, status_code=500)
PY
echo done