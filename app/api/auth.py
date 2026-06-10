from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    return {"access_token": "dev-token", "token_type": "bearer", "user": "demo-user"}
