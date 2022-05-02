from fastapi import APIRouter, Depends, FastAPI
v1_router = APIRouter(
    prefix="/api/v1",
    tags=["All"],
    dependencies=[]
)


from routers.auth import auth_route
from routers.oss import oss_route
from routers.problem import problem_route
from routers.submission import submission_route


v1_router.include_router(auth_route)
v1_router.include_router(oss_route)
v1_router.include_router(problem_route)
v1_router.include_router(submission_route)
