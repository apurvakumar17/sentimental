from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartReview"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'smartreview.db'}"
    DEFAULT_SCRAPE_DELAY: float = 1.0
    DEFAULT_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    DEFAULT_MAX_PAGES: int = 5
    USER_AGENT: str = "SmartReviewBot/1.0 (+https://github.com/apurvakumar17/sentimental)"

    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()
