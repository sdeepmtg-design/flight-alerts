from pydantic import BaseModel, Field, field_validator, model_validator


class DeviceUpdate(BaseModel):
    origin_iata: str | None = Field(None, min_length=3, max_length=3)
    push_token: str | None = None

    @field_validator("origin_iata")
    @classmethod
    def upper_iata(cls, v: str | None) -> str | None:
        return v.upper() if v else None


class RouteCreate(BaseModel):
    destination_iata: str = Field(..., min_length=3, max_length=3)
    destination_country: str | None = Field(None, max_length=64)
    destination_city: str | None = Field(None, max_length=64)
    max_price: int = Field(..., gt=0, le=10_000_000)
    label: str | None = Field(None, max_length=64)
    trip_class: int = Field(0, ge=0, le=2)
    departure_month: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    departure_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_flex_days: int = Field(0, ge=0, le=7)
    one_way: bool = True

    @field_validator("destination_iata")
    @classmethod
    def upper_dest(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def date_rules(self) -> "RouteCreate":
        if self.departure_date and self.departure_month:
            if not self.departure_date.startswith(self.departure_month):
                raise ValueError("Дата вылета должна быть в выбранном месяце")
        if self.date_flex_days >= 3 and not self.departure_date:
            raise ValueError("Для ±3 дней укажите конкретную дату вылета")
        return self


class RouteOut(BaseModel):
    id: int
    destination_iata: str
    destination_country: str | None = None
    destination_city: str | None = None
    max_price: int
    label: str | None
    trip_class: int = 0
    departure_month: str | None = None
    departure_date: str | None = None
    date_flex_days: int = 0
    one_way: bool = True
    last_price: int | None = None
    last_departure: str | None = None
    last_return: str | None = None
    last_checked: str | None = None


class DeviceOut(BaseModel):
    device_id: str
    origin_iata: str | None
    routes_count: int


class CheckResult(BaseModel):
    checked: int
    alerts_sent: int
