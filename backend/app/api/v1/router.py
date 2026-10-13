from fastapi import APIRouter, Depends

from app.api.deps import verify_csrf
from app.api.v1 import account, admin, applications, auth, candidates, companies, cvs, health, jobs

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_csrf)])
for module in (health, auth, account, candidates, cvs, jobs, companies, applications, admin):
    api_router.include_router(module.router)
