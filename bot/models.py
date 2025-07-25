"""
Pydantic модели для валидации данных
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator, ConfigDict


class SessionCreate(BaseModel):
    """Модель для создания новой сессии генерации"""
    user_id: int = Field(..., gt=0, description="ID пользователя Telegram")
    images: List[str] = Field(default_factory=list, max_length=5, description="Список file_id изображений")
    prompt: str = Field(..., min_length=3, max_length=4000, description="Текстовый промпт для генерации")
    
    @validator('prompt')
    def clean_prompt(cls, v: str) -> str:
        return v.strip()


class Session(BaseModel):
    """Модель сессии генерации"""
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(..., description="UUID сессии")
    user_id: int = Field(..., gt=0)
    images: List[str] = Field(default_factory=list)
    prompt: str = Field(..., min_length=1)
    status: str = Field(..., pattern="^(pending|paid|completed|failed)$")
    payment_charge_id: Optional[str] = Field(None, description="ID платежа в Telegram")
    created_at: datetime


class PaymentCreate(BaseModel):
    """Модель для создания записи о платеже"""
    session_id: str = Field(..., description="UUID сессии")
    user_id: int = Field(..., gt=0)
    payment_charge_id: str = Field(..., min_length=1)
    amount: int = Field(..., gt=0, description="Сумма в копейках")


class Payment(BaseModel):
    """Модель платежа"""
    id: int
    session_id: str
    user_id: int
    payment_charge_id: str
    amount: int
    status: str = Field(..., pattern="^(pending|success|refunded)$")
    created_at: datetime
    refunded_at: Optional[datetime] = None


class PackagePurchase(BaseModel):
    """Модель покупки пакета генераций"""
    user_id: int = Field(..., gt=0)
    package_size: int = Field(..., gt=0, le=1000, description="Количество генераций в пакете")
    payment_charge_id: str = Field(..., min_length=1)


class GenerationRequest(BaseModel):
    """Модель запроса на генерацию изображения"""
    prompt: str = Field(..., min_length=3, max_length=4000)
    images: List[bytes] = Field(default_factory=list, max_length=5, description="Изображения в байтах")
    
    @validator('prompt')
    def clean_prompt(cls, v: str) -> str:
        return v.strip()
    
    @validator('images')
    def validate_image_sizes(cls, v: List[bytes]) -> List[bytes]:
        max_size = 20 * 1024 * 1024  # 20MB на изображение
        for img in v:
            if len(img) > max_size:
                raise ValueError(f"Изображение превышает максимальный размер {max_size // 1024 // 1024}MB")
        return v


class UserBalance(BaseModel):
    """Модель баланса пользователя"""
    user_id: int = Field(..., gt=0)
    balance: int = Field(..., ge=0, description="Количество доступных генераций")
    last_updated: datetime