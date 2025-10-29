from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import zipfile

from scanner_plugin import detect_language, get_scanner

# Logging setup
import logging
logging.basicConfig(
    filename="scanner-api.log",
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }

@app.post("/scan")
async def scan_code(file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        lang = detect_language(file_path)
        if not lang:
            raise HTTPException(status_code=400, detail="Could not detect language")
        try:
            run_scan = get_scanner(lang)
            result = run_scan(file_path)
            return JSONResponse(content={"language": lang, "result": result})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# New endpoint for zipped folder upload (Terraform multi-file scan)
@app.post("/scan-folder")
async def scan_folder(zip_file: UploadFile = File(...)):
    if not zip_file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract zip file
        zip_path = os.path.join(tmpdir, zip_file.filename)
        with open(zip_path, "wb") as f:
            f.write(await zip_file.read())
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)
        
        all_results = []
        for root, _, files in os.walk(tmpdir):
            for fname in files:
                file_path = os.path.join(root, fname)
                lang = detect_language(file_path)
                if not lang:
                    logger.warning(f"Could not detect language for {fname}")
                    continue
                try:
                    run_scan = get_scanner(lang)
                    result = run_scan(file_path)
                    all_results.append({
                        "file": fname,
                        "language": lang,
                        "result": result
                    })
                except Exception as e:
                    logger.error(f"Failed to scan {fname}: {str(e)}")
                    continue
        if not all_results:
            raise HTTPException(status_code=400, detail="No supported language files found in uploaded zip")
        return JSONResponse(content={"results": all_results})
