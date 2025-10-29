

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

        # Debug: log all files found
        found_files = []
        for root, _, files in os.walk(tmpdir):
            for fname in files:
                file_path = os.path.join(root, fname)
                found_files.append(file_path)
        logger.info(f"[DEBUG] Files found in zip: {found_files}")

        # Scan results by language
        results_by_language = {}
        files_by_language = {}

        # Walk through all files and detect languages
        for file_path in found_files:
            try:
                lang = detect_language(file_path)
                logger.info(f"[DEBUG] File: {file_path}, Detected language: {lang}")
                if lang:
                    if lang not in files_by_language:
                        files_by_language[lang] = []
                    files_by_language[lang].append(file_path)
            except Exception as e:
                logger.warning(f"Could not detect language for {file_path}: {str(e)}")
                continue

        if not files_by_language:
            logger.error(f"[DEBUG] No supported language files found in uploaded zip. Files: {found_files}")
            raise HTTPException(status_code=400, detail="No supported language files found in uploaded zip")

        # Scan files for each detected language
        all_results = []
        for lang, files in files_by_language.items():
            try:
                run_scan = get_scanner(lang)
                if lang == "terraform":
                    from terraform_v2.scanner_project import run_terraform_scan
                    lang_results = run_terraform_scan(files)
                else:
                    lang_results = []
                    for file_path in files:
                        file_results = run_scan(file_path)
                        lang_results.extend(file_results)
                results_by_language[lang] = {
                    "files_scanned": len(files),
                    "findings": lang_results
                }
                all_results.extend(lang_results)
            except Exception as e:
                logger.error(f"Error scanning {lang} files: {str(e)}")
                continue

        scan_results = {
            "project_name": os.path.splitext(zip_file.filename)[0],
            "languages_detected": list(results_by_language.keys()),
            "total_files_scanned": sum(data["files_scanned"] for data in results_by_language.values()),
            "results_by_language": results_by_language,
            "total_findings": len(all_results)
        }

        return JSONResponse(content=scan_results)
