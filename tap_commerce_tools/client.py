"""commercetools client-credentials authentication and keyset pagination."""

from __future__ import annotations

import json
import time
from functools import cached_property
from urllib.parse import quote

from hotglue_singer_sdk.authenticators import OAuthAuthenticator
from hotglue_singer_sdk.streams import RESTStream


class CommerceToolsAuthenticator(OAuthAuthenticator):
    """Obtain short-lived tokens using the project's API client."""

    @property
    def oauth_request_body(self):
        return {
            "grant_type": "client_credentials",
            "scope": self.config.get("scope")
            or f"view_products:{self.config['project_key']} "
            f"view_categories:{self.config['project_key']} "
            f"view_inventory:{self.config['project_key']}",
        }

    def request_auth(self):
        return self.config["client_id"], self.config["client_secret"]


class CommerceToolsStream(RESTStream):
    """Page by timestamp and ID, without the API's 10,000 offset ceiling."""

    records_jsonpath = "$.results[*]"
    primary_keys = ["id"]  # noqa: RUF012 - SDK stream declaration
    replication_key = "lastModifiedAt"
    is_sorted = True

    @property
    def replication_method(self):
        # Explicit full snapshots must also override a previously saved catalog.
        return "FULL_TABLE" if self.config["full_table"] else super().replication_method

    @property
    def url_base(self):
        return self.config["api_url"].rstrip("/") + "/" + quote(self.config["project_key"], safe="")

    @cached_property
    def authenticator(self):
        return CommerceToolsAuthenticator(
            self,
            auth_endpoint=self.config["auth_url"].rstrip("/") + "/oauth/token",
        )

    def get_url_params(self, context, next_page_token):
        params = {
            "limit": self.config["page_size"],
            "withTotal": "false",
            "sort": ["lastModifiedAt asc", "id asc"],
        }
        predicates = []
        start = self.get_starting_timestamp(context)
        timestamp = start.isoformat() if start else self.config.get("start_date")
        if timestamp:
            predicates.append(f"lastModifiedAt >= {json.dumps(timestamp)}")
        keys = self.config.get("resource_keys", {}).get(self.name)
        if keys is not None:
            if not keys:
                raise ValueError(f"resource_keys.{self.name} must not be empty")
            predicates.append("key in (" + ",".join(map(json.dumps, keys)) + ")")
        if next_page_token:
            modified, resource_id = next_page_token
            stamp, identifier = json.dumps(modified), json.dumps(resource_id)
            predicates.append(
                f"(lastModifiedAt > {stamp} or (lastModifiedAt = {stamp} and id > {identifier}))"
            )
        if predicates:
            params["where"] = " and ".join(f"({p})" for p in predicates)
        return params

    def get_next_page_token(self, response, previous_token):
        rows = response.json()["results"]
        if len(rows) < self.config["page_size"]:
            return None
        return rows[-1]["lastModifiedAt"], rows[-1]["id"]

    def validate_response(self, response):
        # The SDK bounds retries to five attempts. Honor an explicit server delay
        # before its normal exponential backoff for throttled requests.
        if response.status_code == 429 and response.headers.get("Retry-After"):
            time.sleep(max(0, float(response.headers["Retry-After"])))
        super().validate_response(response)
