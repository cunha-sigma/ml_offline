# Joined Kinesis and delivery-control data

## Kinesis event files

The three `firehose-sample-*.ndjson` files contain eight representative events
from each supplied source file. The three `firehose-full-*.ndjson` files contain
all 304, 319, and 310 events, respectively. Each output line is one JSON event.

### What the Kinesis records contain

Each record combines a `request` (the bid opportunity and candidate ads) with
an `impression` (the delivered creative, advertiser/line-item IDs, bid and win
prices, and timing). Many records also have an `activity` array with later
video events such as start, quartiles, and completion. The auction identifier
links the request and impression; the impression and activity records also
share `requestid_str` when activity is present.

The bid request includes app or site inventory, ad slot/video details, deals,
and device/user context. `adcandidates` lists candidate ads and their bidding
and pacing information. Prices such as `bid_price_micros_usd` and
`win_price_micros_usd` use micro-USD units in the fields so named.

For delivered-entity IDs, use `impression.adgroupid.accountid`, `campaignid`,
and `lineitemid`, plus `impression.creative_id` and `advertiser_id`.
`request.adcandidates` contains possible candidates, so its IDs should not be
treated as delivered impressions.

[Beeswax's decoded joined streaming protobuf example](https://github.com/BeeswaxIO/beeswax-api/blob/master/beeswax/logs/streaming/samples/joined_pbf.txt)
shows how a request and impression appear in one joined message. That example
is human-readable protobuf text; these local files are NDJSON. Joined messages
can contain additional message types, so fields and sections vary by record.

## Structured delivery-control file

`sigma_sample_file.ndjson` contains 130 records exported from PostgreSQL:
12 organizations, 12 ad accounts, 14 campaigns, 14 ad sets, and 78 ads.
Each line is one entity object. The records form this hierarchy:

```text
organization → ad_account → campaign → adset → ad
```

Every record has `name`, `entity_name`, `entity_id`, `entity_type`,
`ua_organization_id`, and `status`. `entity_name` and `entity_type` identify the
kind of entity; `entity_id` is its UA UUID and matches its entity-specific
`ua_*_id` field. `name` is a display name, not a join key. The `ua_*_id` fields
link each record to its parent:

| Entity       | Parent link          | Main delivery fields                                                                                                                |
| ------------ | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Organization | None                 | Status, timezone, currency, daily spend limit, unlimited-spend flag, and credit limit.                                              |
| Ad account   | `ua_organization_id` | Beeswax advertiser ID, status, timezone, and default currency.                                                                      |
| Campaign     | `ua_ad_account_id`   | Beeswax campaign ID, objective, flight dates, budgets, currency, and frequency cap.                                                 |
| Ad set       | `ua_campaign_id`     | Beeswax line-item ID, flight dates, budgets, bid, raw bidding and targeting configuration, inventory references, and frequency cap. |
| Ad           | `ua_adset_id`        | Beeswax ad and primary creative IDs, UA primary creative ID, and status.                                                            |

`status` is resolved for each entity separately as `ACTIVE` or `PAUSED`; a
child's status does not incorporate its parent's status. Campaign and ad-set
`bidding_strategy` and `pacing` are null placeholders in this export. The ad
set's `bidding` and `targeting` fields contain the raw stored configuration;
other ad-set fields expose selected targeting inputs and linked inventory IDs.
This is a selected delivery-control structure, not every field in the database.

The Beeswax advertiser, campaign, and line-item IDs were matched to delivered
Kinesis impressions. The stream has no UA ad ID, so the export includes all ads
under matched ad sets, including ads that may not appear in these impressions.
The file reflects PostgreSQL state when the query ran, which can differ from
the state when an impression occurred. Converting the Sigma JSON export to
NDJSON changed only its format; it did not change field values.

## Kinesis anonymization

The anonymization process replaced user and device identifiers, precise user
geography, consent data, user-linked request and auction identifiers, matched
user segment IDs, site page URLs, tracking URLs, and personal content titles
or keywords.
It also replaces the `sellrUsrNo` query value in app-store URLs when present.
User-linked arrays are limited to three entries to reduce fingerprinting.

Business data remains as supplied, including advertiser, campaign, line-item,
creative and deal IDs, prices, targeting configuration, and publisher/app data.
These files therefore still contain production business data; review the
intended recipient and sharing channel before sending them.

The source files were concatenated pretty-printed JSON objects. The processed
files are newline-delimited JSON. The original source files were not modified.
