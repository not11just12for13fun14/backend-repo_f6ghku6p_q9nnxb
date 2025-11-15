from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import db, create_document, get_documents
from schemas import Product, Review, Order

app = FastAPI(title="Pet Boutique API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FilterParams(BaseModel):
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    popularity: Optional[str] = None  # asc/desc
    rating: Optional[float] = None


@app.get("/test")
async def test():
    # Verify DB connection
    try:
        await db.command("ping")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/seed")
async def seed_products():
    # Seed initial 12 products if not exist
    existing = await get_documents("product", {}, limit=1)
    if existing:
        return {"message": "Already seeded"}
    products = [
        {"title": "Premium Dog Harness", "price": 999, "category": "Dogs", "image": "https://images.unsplash.com/photo-1548199973-03cce0bbc87b"},
        {"title": "Anti-Slip Dog Boots", "price": 799, "category": "Dogs", "image": "https://images.unsplash.com/photo-1517849845537-4d257902454a"},
        {"title": "Adjustable Pet Leash", "price": 499, "category": "Dogs", "image": "https://images.unsplash.com/photo-1543466835-00a7907e9de1"},
        {"title": "Plush Squeaky Dog Toy", "price": 349, "category": "Dogs", "image": "https://images.unsplash.com/photo-1558944351-c0a8f8f1a3c4"},
        {"title": "Stainless Steel Feeding Bowl", "price": 399, "category": "Accessories", "image": "https://images.unsplash.com/photo-1583336663277-620dc1996580"},
        {"title": "Anti-Tick Dog Shampoo", "price": 299, "category": "Dogs", "image": "https://images.unsplash.com/photo-1610725666532-ef9f2ff1bf4c"},
        {"title": "Parrot Perch Stand", "price": 699, "category": "Birds", "image": "https://images.unsplash.com/photo-1558287324-183109ad1f83"},
        {"title": "Bird Water Dispenser", "price": 249, "category": "Birds", "image": "https://images.unsplash.com/photo-1498534928137-473e2843ebd7"},
        {"title": "Bird Cage Hanging Toys", "price": 399, "category": "Birds", "image": "https://images.unsplash.com/photo-1518791841217-8f162f1e1131"},
        {"title": "Grooming Brush", "price": 449, "category": "Accessories", "image": "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91"},
        {"title": "Pet Nail Trimmer", "price": 299, "category": "Accessories", "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b"},
        {"title": "Soft Pet Blanket", "price": 599, "category": "Accessories", "image": "https://images.unsplash.com/photo-1517841905240-472988babdf9"},
    ]
    for p in products:
        pdoc = Product(**p, rating=4.5, popularity=100, features=["Durable", "Pet-safe", "Easy to clean"])
        await create_document("product", pdoc.dict())
    return {"message": "Seeded 12 products"}


@app.post("/products")
async def list_products(filters: FilterParams):
    query = {}
    if filters.category:
        query["category"] = filters.category
    if filters.min_price is not None or filters.max_price is not None:
        price = {}
        if filters.min_price is not None:
            price["$gte"] = filters.min_price
        if filters.max_price is not None:
            price["$lte"] = filters.max_price
        query["price"] = price
    if filters.rating is not None:
        query["rating"] = {"$gte": filters.rating}

    docs = await get_documents("product", query, limit=100)
    return docs


@app.get("/products/{product_id}")
async def product_details(product_id: str):
    results = await get_documents("product", {"_id": product_id}, limit=1)
    if not results:
        raise HTTPException(status_code=404, detail="Product not found")
    product = results[0]
    reviews = await get_documents("review", {"product_id": product_id}, limit=20)
    recs = await get_documents("product", {"category": product.get("category")}, limit=6)
    return {"product": product, "reviews": reviews, "recommended": recs}


class AddReview(BaseModel):
    product_id: str
    name: str
    rating: int
    comment: str


@app.post("/reviews")
async def add_review(payload: AddReview):
    review = Review(**payload.dict(), created_at=datetime.utcnow())
    await create_document("review", review.dict())
    return {"message": "Review added"}


class CheckoutPayload(BaseModel):
    items: List[dict]
    discount_code: Optional[str] = None
    payment: dict
    customer: dict


@app.post("/checkout")
async def checkout(payload: CheckoutPayload):
    # Calculate totals
    subtotal = 0.0
    for item in payload.items:
        pid = item.get("product_id")
        qty = int(item.get("quantity", 1))
        product_res = await get_documents("product", {"_id": pid}, limit=1)
        if not product_res:
            raise HTTPException(status_code=400, detail=f"Invalid product {pid}")
        price = float(product_res[0].get("price", 0))
        subtotal += price * qty

    discount = 0.0
    if payload.discount_code:
        if payload.discount_code.upper() in ["WELCOME10", "PETLOVE10"]:
            discount = subtotal * 0.10

    total = max(subtotal - discount, 0)

    order = Order(
        items=[{"product_id": i["product_id"], "quantity": int(i.get("quantity", 1))} for i in payload.items],
        subtotal=subtotal,
        discount=discount,
        total=total,
        payment=payload.payment,  # stored as-is
        customer=payload.customer,
        status="confirmed",
        created_at=datetime.utcnow(),
    )
    saved = await create_document("order", order.dict())
    return {"message": "Order confirmed", "order_id": saved.get("_id"), "total": total}
