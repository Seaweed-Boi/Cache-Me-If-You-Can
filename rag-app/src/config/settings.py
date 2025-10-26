from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses pydantic_settings to validate and manage configuration.
    """

    # Optional local model (a Hugging Face/local path). If provided, the app
    # will use this model for generation instead of OpenAI.
    local_model_name: Optional[str] = None

    # Embedding Model Configuration (sentence-transformers)
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # Qdrant configuration (used instead of Chroma)
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "rag_documents"

    # Data Configuration
    data_path: str = "./data"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_data_path(self) -> Path:
        """Returns the data path as a Path object."""
        return Path(self.data_path)


# Create a singleton instance of settings
settings = Settings()