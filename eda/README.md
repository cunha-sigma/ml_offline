# EDA dev suite

Local Jupyter environment for exploring the client data samples
(`docs/batch_03/data-samples/`). The repo is mounted into the container,
so notebooks read the data in place and save under `eda/notebooks/`.

## Run

```sh
cd eda
docker compose up --build -d
```

Jupyter Lab: http://localhost:8888 — auth is disabled (local-only dev
suite; the port is bound on localhost by your compose/podman defaults —
do not expose it beyond the machine).

Stop with `docker compose down`.

## Loading the data

`eda/src/eda_tools` is on `PYTHONPATH` inside the container:

```python
from eda_tools import (
    load_firehose,          # one row per joined event (933)
    load_candidates,        # one row per ad candidate, with join keys + request context
    load_activity,          # one row per video activity event (START/Q1/MID/Q3)
    load_delivery_control,  # one row per entity record (130)
    read_ndjson,            # generic: any ndjson file -> DataFrame
)
```

All loaders default to the batch_03 paths and accept explicit paths.
Candidates and activity join back to events on `auction_key` (a scalar
derived from the `auctionid` struct, present in all three frames);
delivery-control entities split by `entity_type` and link child→parent
via the `ua_*_id` fields.

`notebooks/00_batch03_overview.ipynb` is the starter template.
