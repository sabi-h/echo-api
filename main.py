from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from piccolo.engine import engine_finder
from app import auth_router
from app import posts_router
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.tables import User, Post

    await User.create_table(if_not_exists=True)
    await Post.create_table(if_not_exists=True)
    yield
    # Shutdown
    engine = engine_finder()
    await engine.close_connection_pool()


app = FastAPI(
    title="Hackathon API",
    description="Simple API for posts with voice and text",
    version="1.0.0",
    lifespan=lifespan,  # Use lifespan instead of on_event
    swagger_ui_parameters={"persistAuthorization": True},  # This keeps your authorization between refreshes
)

# CORS middleware for React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React Native app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
os.makedirs("uploads", exist_ok=True)


# Include routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(posts_router.router, prefix="/api/posts", tags=["Posts"])


@app.get("/")
async def root():
    return {"message": "Hackathon API is running!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
