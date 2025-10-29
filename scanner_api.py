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

        # Collect all .py and .tf files
        tf_files = []
        py_files = []
        for root, dirs, files in os.walk(tmpdir):
            for fname in files:
                fpath = os.path.join(root, fname)
                if fname.endswith('.tf'):
                    tf_files.append(fpath)
                elif fname.endswith('.py'):
                    py_files.append(fpath)

        if not tf_files and not py_files:
            raise HTTPException(status_code=400, detail="No .tf or .py files found in uploaded zip")

        scan_results = {"findings": [], "files": {}}
        errors = []
        # Scan Terraform files (aggregate)
        if tf_files:
            try:
                from terraform_v2.scanner_project import run_terraform_scan
                tf_result = run_terraform_scan(tf_files)
                scan_results["findings"].extend(tf_result.get("findings", []))
                scan_results["files"].update({f: "terraform" for f in tf_files})
            except Exception as e:
                errors.append(f"Terraform scan error: {str(e)}")

        # Scan Python files (individually)
        if py_files:
            from scanner_plugin import detect_language, get_scanner
            try:
                py_scanner = get_scanner("python")
                for py_file in py_files:
                    try:
                        py_findings = py_scanner(py_file)
                        scan_results["findings"].extend(py_findings)
                        scan_results["files"][py_file] = "python"
                    except Exception as e:
                        errors.append(f"Python scan error in {py_file}: {str(e)}")
            except Exception as e:
                errors.append(f"Python scanner error: {str(e)}")

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
                "timestamp": timestamp,
                "errors": errors
            }
        }
        with open(os.path.join(results_dir, "scan_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(scan_metadata, f, indent=2)

        if errors:
            return JSONResponse(content={"result": scan_results, "errors": errors})
        return JSONResponse(content=scan_results)
