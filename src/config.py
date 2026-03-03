from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://parkwise:parkwise@localhost:5432/parkwise"
    async_database_url: str = ""
    anthropic_api_key: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore"}

    def get_async_database_url(self) -> str:
        if self.async_database_url:
            return self.async_database_url
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


settings = Settings()
