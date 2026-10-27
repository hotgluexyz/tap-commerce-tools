"""CommerceTools tap class."""

from __future__ import annotations

from hotglue_singer_sdk import Stream, Tap
from hotglue_singer_sdk import typing as th  # JSON schema typing helpers
from typing_extensions import override

from tap_commerce_tools.streams import (
    CategoriesStream,
    ChannelsStream,
    InventoryStream,
    ProductsStream,
)

STREAM_TYPES = [
    CategoriesStream,
    ChannelsStream,
    InventoryStream,
    ProductsStream,
]


class TapCommerceTools(Tap):
    """Singer tap for CommerceTools."""

    name = "tap-commerce-tools"

    config_jsonschema = th.PropertiesList(
        th.Property("project_key", th.StringType, required=True),
        th.Property("client_id", th.StringType, required=True),
        th.Property("client_secret", th.StringType, required=True),
        th.Property("scope", th.StringType),
        th.Property(
            "auth_url", th.StringType, default="https://auth.us-east-2.aws.commercetools.com"
        ),
        th.Property("page_size", th.IntegerType, default=100),
        th.Property(
            "resource_keys",
            th.ObjectType(),
            description="Optional per-stream allowlist of resource keys",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync",
            default="2000-01-01T00:00:00Z",
        ),
        th.Property(
            "api_url",
            th.StringType,
            description="Base URL for the CommerceTools API",
            default="https://api.us-east-2.aws.commercetools.com",
        ),
    ).to_dict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not 1 <= self.config["page_size"] <= 500:
            raise ValueError("page_size must be between 1 and 500")

    @override
    def discover_streams(self) -> list[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapCommerceTools.cli()
