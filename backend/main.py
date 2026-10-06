from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
import backend.models as models
from backend.routes import resume, interview, analytics

# Initialize database schema and migrations
init_db()

app = FastAPI(
    title="AI Interview Intelligence System API",
    description="Multimodal Interview Preparation and Performance Analytics Engine",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(resume.router)
app.include_router(interview.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "AI Interview Intelligence System",
        "version": "1.0.0"
    }
