from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Product(BaseModel):
    # strict=True: reject "19.99" for an int instead of converting it.
    model_config = ConfigDict(strict=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price_cents: int = Field(alias="priceCents", ge=0)
    in_stock: bool = Field(alias="inStock")


class Ok(TypedDict):
    ok: Literal[True]
    product: dict[str, object]


class Err(TypedDict):
    ok: Literal[False]
    field: str


def parse_product(raw: object) -> Ok | Err:
    try:
        product = Product.model_validate(raw)  # runtime validation
    except ValidationError as exc:
        loc = exc.errors()[0]["loc"]
        return {"ok": False, "field": ".".join(str(part) for part in loc)}
    return {"ok": True, "product": product.model_dump(by_alias=True)}
