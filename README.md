# tap-commerce-tools

Python 3.10 Singer tap for commercetools, scaffolded from the Hotglue tap
Cookiecutter and implemented with hotglue-singer-sdk.

## Streams

`products`, `categories`, `inventory`, and `channels` read the corresponding
project-scoped REST collections. Primary key: `id`. Incremental key:
`lastModifiedAt`. Products retain `masterData.current`, staged data, variants,
images, localized fields, embedded prices/discounts and custom attributes.
Categories retain parents and ancestors; inventory retains SKU and supply channel.
Standalone Prices are not included.

Pagination uses `(lastModifiedAt, id)` keysets, avoiding the 10,000 offset limit
and handling equal timestamps. Incremental boundaries are inclusive (a boundary
record may be replayed safely). SDK retries are bounded to five attempts;
429 Retry-After delays are honored in addition to exponential backoff.
Hard deletes are not exposed by these collection APIs; no tombstones are emitted.

## Configuration

| Setting | Required | Default / meaning |
|---|---|---|
| project_key | yes | commercetools project key |
| client_id | yes | Sensitive API client identifier |
| client_secret | yes | Sensitive API client secret |
| scope | no | View products, categories and inventory for the project; set explicit scopes matching your API client |
| api_url | no | https://api.us-east-2.aws.commercetools.com |
| auth_url | no | https://auth.us-east-2.aws.commercetools.com |
| start_date | no | 2000-01-01T00:00:00Z |
| page_size | no | 100; integer between 1 and 500 |
| full_table | no | false; true makes every stream a complete snapshot for denormalized catalog enrichment |
| resource_keys | no | Per-stream allowlist, e.g. `{"products":["demo-boot"]}`. Omitted stream means unrestricted; empty lists are rejected. |

Client-credentials OAuth uses HTTP Basic authentication at `/oauth/token`.
Tokens refresh automatically; no refresh token or Hotglue access-token service
is needed. Keep configuration in ignored `.secrets/` or use `--config ENV`.

```json
{
  "project_key": "your-project",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "scope": "view_products:your-project view_categories:your-project view_inventory:your-project"
}
```

## Run

```bash
uv venv --python 3.10 --seed .venv
uv pip install --python .venv/bin/python -e . pytest responses ruff
.venv/bin/tap-commerce-tools --config .secrets/config.json --discover > .secrets/catalog.json
.venv/bin/tap-commerce-tools --config .secrets/config.json --catalog .secrets/catalog.json > .secrets/data.singer
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Select desired streams/fields in the discovered catalog. For a denormalized
catalog-to-search ETL, set `full_table: true` on all four streams, so
inventory-only and category-only changes can re-enrich every affected product.
Alternatively maintain a complete downstream cache before enabling incremental
extraction across independently changing streams. An incremental product stream
alone cannot detect inventory changes.
