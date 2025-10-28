

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import zipfile

from scanner_plugin import detect_language, get_scanner

# MongoDB Atlas support
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Logging setup
import logging
logging.basicConfig(
    filename="scanner-api.log",
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Read MongoDB config from environment variables
MONGO_URI = os.environ.get("MONGO_URI")
MONGODB_DB = os.environ.get("MONGODB_DB", "scanner_results")
MONGODB_COLLECTION = os.environ.get("MONGODB_COLLECTION", "scan_results")

# Set up MongoDB client (global)
mongo_client = None
mongo_collection = None
if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_db = mongo_client[MONGODB_DB]
        mongo_collection = mongo_db[MONGODB_COLLECTION]
    except ConnectionFailure:
        logger.warning("Could not connect to MongoDB Atlas. Check your URI and network.")
else:
    logger.warning("MONGO_URI environment variable not set. MongoDB will not be used.")

app = FastAPI()

@app.get("/health")
async def health_check():
    # Check MongoDB connection
    try:
        if mongo_client:
            mongo_client.admin.command('ping')
            mongo_status = "connected"
        else:
            mongo_status = "not configured"
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        mongo_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "mongodb": mongo_status
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
            # Prepare document for MongoDB
            doc = {
                "filename": file.filename,
                "language": lang,
                "result": result
            }
            try:
                if mongo_collection is not None:
                    mongo_collection.insert_one(doc)
                    logger.info(f"Inserted scan result for {file.filename} into MongoDB.")
                else:
                    logger.warning("MongoDB collection not configured. Skipping insert.")
            except Exception as db_exc:
                logger.error(f"Failed to insert scan result for {file.filename}: {db_exc}")
            return JSONResponse(content={"language": lang, "result": result})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# New endpoint for zipped folder upload (Terraform multi-file scan)
@app.post("/scan-folder")
async def scan_folder(zip_file: UploadFile = File(...)):
    if not zip_file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")
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
            # Prepare document for MongoDB
            doc = {
                "filename": zip_file.filename,
                "language": "terraform",
                **results
            }
            try:
                if mongo_collection is not None:
                    mongo_collection.insert_one(doc)
                    logger.info(f"Inserted scan result for {zip_file.filename} into MongoDB.")
                else:
                    logger.warning("MongoDB collection not configured. Skipping insert.")
            except Exception as db_exc:
                logger.error(f"Failed to insert scan result for {zip_file.filename}: {db_exc}")
            return JSONResponse(content={"language": "terraform", **results})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
