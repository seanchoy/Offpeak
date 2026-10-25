from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.query_counter import register_query_counter
from app.routers import ai, auth, health, itinerary, pois, users

# instantiate app
app = FastAPI()

if settings.ENABLE_QUERY_COUNTER:
    register_query_counter(app)

# connect React frontend origin(s) to FastAPI backend origin via CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Holds OAuth state/nonce between /google/login and /google/callback only.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET_KEY,
    max_age=600,
    same_site="lax",
    https_only=True,
)

# include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(pois.router)
app.include_router(users.router)
app.include_router(itinerary.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {"message": "API running"}
