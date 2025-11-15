from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Each Pydantic class corresponds to a collection (lowercased)

class Product(BaseModel):
    id: Optional[str] = Field(default=None, description="String id")
    title: str
    price: float
    category: str
    rating: float = 4.5
    popularity: int = 0
    image: str
    features: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Review(BaseModel):
    id: Optional[str] = None
    product_id: str
    name: str
    rating: int
    comment: str
    created_at: Optional[datetime] = None

class CartItem(BaseModel):
    product_id: str
    quantity: int = 1

class PaymentMethod(BaseModel):
    type: str  # card, upi, netbanking, wallet, cod
    provider: Optional[str] = None
    last4: Optional[str] = None
    upi_id: Optional[str] = None

class Customer(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None

class Order(BaseModel):
    id: Optional[str] = None
    items: List[CartItem]
    subtotal: float
    discount: float = 0
    total: float
    payment: PaymentMethod
    customer: Customer
    status: str = "confirmed"
    created_at: Optional[datetime] = None
