"""Health check router"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "realviax-outreach"
    }
