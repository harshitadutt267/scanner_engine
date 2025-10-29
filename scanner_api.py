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
    import datetime, json
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, zip_file.filename)
        with open(zip_path, "wb") as f:
            f.write(await zip_file.read())
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)
        # Collect all .tf files
        tf_files = []
        for root, dirs, files in os.walk(tmpdir):
            for fname in files:
                if fname.endswith('.tf'):
                    tf_files.append(os.path.join(root, fname))
        if not tf_files:
            raise HTTPException(status_code=400, detail="No .tf files found in uploaded zip")
        # Use the new API function for multi-file scanning
        try:
            from terraform_v2.scanner_project import run_terraform_scan
            results = run_terraform_scan(tf_files)
            scan_results = {"language": "terraform", **results}
            # Store results to disk (host-mountable directory)
            project_name = os.path.splitext(zip_file.filename)[0]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            results_dir = os.path.join("/scanner_results", project_name, timestamp)
            os.makedirs(results_dir, exist_ok=True)
            # Write scan results
            with open(os.path.join(results_dir, "scan_results.json"), "w", encoding="utf-8") as f:
                json.dump(scan_results, f, indent=2)
            # Write scan metadata
            scan_metadata = {
                "scan_info": {
                    "project_name": project_name,
                    "timestamp": timestamp
                }
            }
            with open(os.path.join(results_dir, "scan_metadata.json"), "w", encoding="utf-8") as f:
                json.dump(scan_metadata, f, indent=2)
            return JSONResponse(content=scan_results)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
