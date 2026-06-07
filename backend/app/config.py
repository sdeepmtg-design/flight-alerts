from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    travelpayouts_token: str = ""
    travelpayouts_marker: str = ""
    database_url: str = ""
    database_path: str = "./flight_alerts.db"
    check_interval_hours: int = 4
    cron_secret: str = "dev"

    aviasales_base: str = "https://www.aviasales.ru"


settings = Settings()
