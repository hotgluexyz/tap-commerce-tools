"""Catalog resources, retaining nested variants, prices and custom attributes."""

from tap_commerce_tools.client import CommerceToolsStream


def resource_schema(properties):
    """Common commercetools resource envelope."""
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "key": {"type": ["string", "null"]},
            "version": {"type": "integer"},
            "createdAt": {"type": "string", "format": "date-time"},
            "lastModifiedAt": {"type": "string", "format": "date-time"},
            **properties,
        },
    }


# Free-form objects are intentional: localized strings, attributes and money vary
# by project. Preserve their complete structure for downstream transformations.
OBJECT = {"type": ["object", "null"], "additionalProperties": True}
REFERENCES = {"type": ["array", "null"], "items": OBJECT}


class ProductsStream(CommerceToolsStream):
    """Published/current and staged catalog data including all variants/prices."""

    name = "products"
    path = "/products"
    schema = resource_schema(
        {
            "masterData": OBJECT,
            "productType": OBJECT,
            "taxCategory": OBJECT,
            "priceMode": {"type": ["string", "null"]},
        }
    )


class CategoriesStream(CommerceToolsStream):
    """Category names, parents and ancestors."""

    name = "categories"
    path = "/categories"
    schema = resource_schema(
        {
            "name": OBJECT,
            "slug": OBJECT,
            "description": OBJECT,
            "ancestors": REFERENCES,
            "parent": OBJECT,
            "custom": OBJECT,
            "externalId": {"type": ["string", "null"]},
            "orderHint": {"type": ["string", "null"]},
        }
    )


class InventoryStream(CommerceToolsStream):
    """SKU-level inventory, optionally scoped to a supply channel."""

    name = "inventory"
    path = "/inventory"
    schema = resource_schema(
        {
            "sku": {"type": "string"},
            "supplyChannel": OBJECT,
            "custom": OBJECT,
            "quantityOnStock": {"type": "integer"},
            "availableQuantity": {"type": "integer"},
            "restockableInDays": {"type": ["integer", "null"]},
            "expectedDelivery": {"type": ["string", "null"], "format": "date-time"},
        }
    )


class ChannelsStream(CommerceToolsStream):
    """Supply/distribution channels for inventory and price enrichment."""

    name = "channels"
    path = "/channels"
    schema = resource_schema(
        {
            "name": OBJECT,
            "description": OBJECT,
            "address": OBJECT,
            "roles": {"type": "array", "items": {"type": "string"}},
            "custom": OBJECT,
        }
    )
