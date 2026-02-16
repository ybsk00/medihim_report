from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import bcrypt
import jwt
import datetime
from models.schemas import AdminUserCreate
from services.supabase_client import get_supabase
from config import JWT_SECRET

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(data: LoginRequest):
    db = get_supabase()
    result = db.table("admin_users").select("id, username, password_hash").eq("username", data.username).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")

    user = result.data[0]
    if not bcrypt.checkpw(data.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")

    payload = {
        "sub": user["id"],
        "username": user["username"],
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return {"token": token, "username": user["username"]}


@router.get("/users")
async def list_admin_users():
    db = get_supabase()
    result = db.table("admin_users").select("id, username, created_at").order("created_at", desc=True).execute()
    return {"data": result.data}


@router.post("/users")
async def create_admin_user(data: AdminUserCreate):
    if len(data.username) < 3:
        raise HTTPException(status_code=400, detail="아이디는 3자 이상이어야 합니다")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="비밀번호는 6자 이상이어야 합니다")

    db = get_supabase()

    # 중복 확인
    existing = db.table("admin_users").select("id").eq("username", data.username).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="이미 존재하는 아이디입니다")

    password_hash = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    result = db.table("admin_users").insert({
        "username": data.username,
        "password_hash": password_hash,
    }).execute()

    user = result.data[0]
    return {"id": user["id"], "username": user["username"], "created_at": user["created_at"]}


@router.delete("/users/{user_id}")
async def delete_admin_user(user_id: str):
    db = get_supabase()

    existing = db.table("admin_users").select("id").eq("id", user_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="관리자를 찾을 수 없습니다")

    db.table("admin_users").delete().eq("id", user_id).execute()
    return {"deleted": True, "id": user_id}
