from fastapi import APIRouter, Depends, FastAPI
master_router = APIRouter(
    # prefix="/api/v2",
    tags=["All"],
    dependencies=[]
)


from routers.auth import auth_route
from routers.oss import oss_route
from routers.problem import problem_route



master_router.include_router(auth_route)
master_router.include_router(oss_route)
master_router.include_router(problem_route)
