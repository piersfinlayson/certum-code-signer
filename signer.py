from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse
import subprocess
import tempfile
import os
import time
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

def cleanup_files(*files):
    """Delete temporary files"""
    for filepath in files:
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
                logger.debug(f"Cleaned up: {filepath}")
        except Exception as e:
            logger.error(f"Error cleaning up {filepath}: {e}")

@app.on_event("startup")
async def startup_event():
    """Start pcscd daemon and verify it's working"""
    logger.info("Starting pcscd...")
    
    # Start pcscd with polkit disabled
    try:
        subprocess.Popen(["pcscd", "--disable-polkit"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        logger.info("pcscd process started")
    except Exception as e:
        logger.error(f"Failed to start pcscd: {e}")
        sys.exit(1)
    
    # Wait for pcscd to be ready
    logger.info("Waiting for pcscd to initialize...")
    time.sleep(2)
    
    # Test that we can see the smartcard
    try:
        result = subprocess.run([
            "pkcs11-tool",
            "--module", "/opt/proCertumCardManager/sc30pkcs11-3.0.6.72-MS.so",
            "--list-slots"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0 or "Available slots" not in result.stdout:
            logger.error("pcscd started but cannot see smartcard reader")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")
            sys.exit(1)
            
        logger.info("pcscd started successfully and smartcard reader detected")
        logger.info(f"Slots found:\n{result.stdout}")
        
    except Exception as e:
        logger.error(f"ERROR testing pcscd: {e}")
        sys.exit(1)

@app.post("/sign")
async def sign_executable(
    file: UploadFile = File(...),
    pin: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    logger.info(f"Received signing request for file: {file.filename}")
    
    key_id = os.environ["KEY_ID"]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".exe") as tmp_in:
        content = await file.read()
        tmp_in.write(content)
        tmp_in_path = tmp_in.name
    
    logger.info(f"File saved to temporary location: {tmp_in_path}")
    tmp_out_path = tmp_in_path + ".signed"
    
    try:
        logger.info("Starting signing process...")
        result = subprocess.run([
            "osslsigncode", "sign",
            "-pkcs11module", "/opt/proCertumCardManager/sc30pkcs11-3.0.6.72-MS.so",
            "-certs", "/certs/signing_cert.pem",
            "-key", f"pkcs11:id={key_id};type=private?pin-value={pin}",
            "-h", "sha256",
            "-ts", "http://timestamp.digicert.com",
            "-in", tmp_in_path,
            "-out", tmp_out_path,
            "-verbose",
            "-n", "Signature"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Signing failed with return code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Signing failed: {result.stderr}")
        
        logger.info("Signing completed successfully")
        logger.debug(f"osslsigncode output: {result.stdout}")
        
        logger.info("Starting verification...")
        verify_result = subprocess.run([
            "osslsigncode", "verify",
            tmp_out_path
        ], capture_output=True, text=True)
        
        if verify_result.returncode != 0:
            logger.error(f"Verification failed with return code {verify_result.returncode}")
            logger.error(f"stderr: {verify_result.stderr}")
            raise HTTPException(status_code=500, detail=f"Verification failed: {verify_result.stderr}")
        
        logger.info("Verification completed successfully")
        logger.info(f"Returning signed file: {file.filename}")
        
        # Schedule cleanup after response is sent
        background_tasks.add_task(cleanup_files, tmp_in_path, tmp_out_path)
        
        return FileResponse(
            tmp_out_path,
            media_type="application/octet-stream",
            filename=file.filename
        )
    except HTTPException:
        # Clean up immediately on error
        cleanup_files(tmp_in_path, tmp_out_path)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during signing: {e}")
        cleanup_files(tmp_in_path, tmp_out_path)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")