"""Authentication router (placeholder)"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
def auth_status():
    return {"authenticated": False, "message": "Auth not implemented"}
