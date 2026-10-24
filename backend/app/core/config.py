from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    AI_PROVIDER: str
    # Optional proxy for Gemini's outbound calls. Render's Frankfurt egress IP is
    # rejected by Gemini ("User location is not supported", 400 FAILED_PRECONDITION);
    # routing through a non-Frankfurt egress fixes it. Accepts a single URL — ideally
    # a Webshare *rotating* endpoint so churning free IPs are handled upstream — or a
    # comma-separated list the provider rotates across on retry. Empty = direct.
    GEMINI_PROXY_URL: str = ""
    # How many egress attempts (each a fresh rotation) before giving up and letting
    # the LLM fallback take over. Only applied when GEMINI_PROXY_URL is set.
    GEMINI_PROXY_RETRIES: int = 3
    # Optional so a missing value never breaks Settings() import (the migration
    # step imports this module). The photo endpoint degrades to 404 when unset.
    GOOGLE_PLACES_API_KEY: str = ""
    # Absolute base for the photo-proxy URLs handed to clients. A fixed value
    # rather than request.base_url so deep serialisation layers (itineraries) can
    # build the same link without a request, and so it is immune to proxy-header
    # host confusion. Defaults to the production API host; override per env.
    PUBLIC_API_URL: str = "https://api.offpeak.live"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    # config flag for query counter
    ENABLE_QUERY_COUNTER: bool = False
    # Optional for the same reason as above; the Google login routes return 503 when unset.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
