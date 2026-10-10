from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Literal

class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str | None = None
class CustomerIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=5, max_length=32)
    email: EmailStr | None = None
    bale_user_id: str | None = Field(default=None, max_length=128)
    bale_chat_id: str | None = Field(default=None, max_length=128)
    notes: str | None = None
    @field_validator("email", mode="before")
    @classmethod
    def blank_email_to_none(cls, value):
        return None if value == "" else value
class CustomerOut(CustomerIn):
    id: int
    is_archived: bool
    model_config = ConfigDict(from_attributes=True)
class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    brand: str | None = None
    model: str | None = None
    service_interval: int = Field(default=12, ge=1, le=120)
    service_interval_unit: Literal['days','months','years'] = 'months'
    reminders_enabled: bool = True
    is_active: bool = True
class ProductOut(ProductIn):
    id: int
    model_config = ConfigDict(from_attributes=True)
class PurchaseIn(BaseModel):
    customer_id: int
    product_id: int
    purchase_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    invoice_number: str | None = None
    service_interval: int = Field(default=12, ge=1, le=120)
    service_interval_unit: Literal['days','months','years'] = 'months'
    notes: str | None = None
class TicketIn(BaseModel):
    customer_id: int
    title: str = Field(min_length=2, max_length=200)
    description: str = ''
    priority: Literal['low','normal','high','urgent'] = 'normal'
    status: Literal['open','in_progress','resolved','closed'] = 'open'
class ReminderIn(BaseModel):
    purchase_id: int
    due_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    message: str = Field(min_length=1, max_length=4096)
class CampaignIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    message: str = Field(min_length=1, max_length=4096)
class SendMessageIn(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    chat_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4096)

class CampaignSendIn(BaseModel):
    token: str = Field(min_length=10, max_length=512)
