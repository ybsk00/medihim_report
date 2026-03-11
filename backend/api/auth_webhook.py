"""Webhook 인증 미들웨어 — API Key + HMAC-SHA256 서명 검증"""

import hmac
import hashlib
from fastapi import Request, HTTPException, Depends


# 환경변수에서 로드 (config.py에서 가져옴)
def _get_api_key():
    from config import IPPEO_API_KEY
    return IPPEO_API_KEY


def _get_webhook_secret():
    from config import IPPEO_WEBHOOK_SECRET
    return IPPEO_WEBHOOK_SECRET


async def verify_api_key(request: Request):
    """API Key 검증"""
    api_key = request.headers.get("X-API-Key")
    expected = _get_api_key()
    if not expected:
        # API Key 미설정 시 개발 모드로 통과
        return True
    if not api_key or api_key != expected:
        raise HTTPException(status_code=401, detail={
            "success": False,
            "error": "INVALID_API_KEY",
            "message": "유효하지 않은 API Key입니다."
        })
    return True


async def verify_webhook_signature(request: Request):
    """HMAC-SHA256 서명 검증"""
    secret = _get_webhook_secret()
    if not secret:
        # Secret 미설정 시 개발 모드로 통과
        return True

    signature = request.headers.get("X-Signature", "")
    if not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail={
            "success": False,
            "error": "INVALID_SIGNATURE",
            "message": "서명 형식이 올바르지 않습니다. sha256=... 형식이어야 합니다."
        })

    body = await request.body()
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    received = signature.replace("sha256=", "")
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail={
            "success": False,
            "error": "SIGNATURE_MISMATCH",
            "message": "서명이 일치하지 않습니다."
        })

    return True


async def verify_webhook(request: Request):
    """API Key + 서명 동시 검증 (Webhook 엔드포인트용)"""
    await verify_api_key(request)
    await verify_webhook_signature(request)
    return True
