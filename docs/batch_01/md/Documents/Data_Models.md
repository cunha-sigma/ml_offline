# Data Models

# the client Data Dictionary and Relationship Guide

## Purpose

The client is sharing relevant campaign, ad set, targeting, creative, delivery, and performance data with the partner teams. This includes contextual and operational information such as flight dates, status, budgets, targeting rules, delivery overrides, pacing, spend, and historical bid/win/conversion signals. This document is intended to explain what the data means and how the major entities relate to each other. It is not a raw database schema dump.

## Audience

- Engineering teams consuming the client configuration data from Postgres.

- Data science / ML teams using pacing, spend, and performance data.

- Data engineering teams joining the client configuration data to win logs, bid requests, spend, and conversion datasets.

## Scope

This guide covers the core advertiser configuration and reporting entities visible in the client backend models:

- Organization and ad account ownership.

- Campaign, ad set, ad, creative, media, targeting, and placements.

- Enhanced pixel, app tracker, and conversion measurement relationships.

- Raw delivery / win-log-style data and hourly reporting aggregates.

- Relationship and join guidance for the relevant data.

This guide should be reviewed against the production warehouse / event-log contracts before creating hard dependencies on delivery-log field names or grain.

## Core Grain Summary

| Dataset | Grain | Primary join keys | Source of truth | Notes |
|----|----|----|----|----|
| organization | One row per the client organization | organization.id | the client Postgres | Business owner / tenant-level context. |
| adaccount | One row per advertiser account | adaccount.id, organization_id | the client Postgres | Campaigns live under ad accounts. |
| campaign | One row per campaign | campaign.id, adaccount_id, external_id | the client Postgres | Top-level flight, budget, objective, and status settings. |
| adset | One row per ad set / downstream line item | adset.id, campaign_id, external_id | the client Postgres | Primary delivery configuration object. Contains bid, budget, dates, pacing-related fields, inventory, and tracker links. |
| target | One row per ad set | target.id, adset_id | the client Postgres | Targeting criteria are mostly JSON fields. |
| target_placement | One row per target-placement association | target_id, placement_id | the client Postgres | Normalized join between targeting and placements. |
| placement | One row per available placement | placement.id, external_id, network_id | the client Postgres | Placement names and external placement identifiers. |
| ad | One row per ad under an ad set | ad.id, adset_id, external_id | the client Postgres | Links ad delivery object to creative assets. |
| creative | One row per creative asset record | creative.id, external_id, media_id | the client Postgres | Creative eligibility, approval state, and media linkage. |
| media | One row per uploaded media object | media.id | the client Postgres / object storage | Contains object storage key and bucket, not necessarily a public URL. |
| adset_delivery_override | At most one row per ad set | adset_id | the client Postgres admin data | Admin-managed delivery and pacing overrides that should take precedence over normal defaults. |
| app_tracker | One row per app measurement tracker | app_tracker.id, adaccount_id | the client Postgres | Used by app promotion ad sets and app event measurement. |
| app_tracker_pixel | One row per platform-specific app tracker pixel URL | app_tracker_id, platform | the client Postgres | Stores impression tracking URLs by platform. |
| performance_report_pipeline_merged | One row per ad_id x hour | ad_id, hour, hour_utc | the client reporting pipeline | Aggregated delivery/performance metrics. |
| raw_performance_data | Event/log export grain, usually lower than report aggregate | downstream IDs such as campaign_id, line_item_id, creative_id | Log / reporting pipeline | Contains auction, bid, inventory, device, geo, spend, and performance fields. |
| win_logs | Win-log query structure, not a Postgres table model | downstream IDs such as campaign_id, line_item_id, creative_id | Parquet / Athena / DuckDB query source | Used for safe query generation against external log data. |
| conversion_data | One row per pixel_external_id x hour | pixel_external_id, hour, hour_utc | the client reporting pipeline | Hourly conversion aggregate. |
| attributed_conversion_data | One row per pixel_external_id x creative_external_id x hour | pixel_external_id, creative_external_id, hour, hour_utc | the client reporting pipeline | Hourly attributed conversion aggregate. |
| raw_attributed_conversion_data | Raw attributed conversion event grain | downstream IDs such as campaign_id, line_item_id, creative_id; conversion_id | the client reporting pipeline | Lower-level attributed conversion records. |
| app_events_conversion_data | One row per app_tracker_id x event_name x hour | app_tracker_id, event_name, hour, hour_utc | the client reporting pipeline | Hourly app event conversion aggregate. |
| mobile_app_event\_\*\_day_attribution | One row per attributed app conversion | conversion_id, app_tracker_id, ad_id | the client Postgres / attribution pipeline | Separate 7-day, 14-day, and 30-day attribution windows. |
| kochava_conversion_data | One row per enhanced_pixel_id x event_name x hour | enhanced_pixel_id, event_name, hour, hour_utc | the client reporting pipeline | Hourly web-attribution conversion aggregate. |
| kochava\_\*\_day_attribution | One row per web-attributed conversion | conversion_id, enhanced_pixel_id, ad_id | the client Postgres / attribution pipeline | Separate 7-day, 14-day, and 30-day attribution windows. |
| gold_kochava\_\*\_day_attribution | One row per web-attributed conversion in query/reporting layer | conversion_id, enhanced_pixel_id, ad_id, adaccount_id | Warehouse/query source | Query-only mappings for 7-day, 14-day, and 30-day attribution windows. |
| kochava | Raw web-attribution conversion source | transaction_id, pixel_id, partition fields | Warehouse/query source | Query-only mapping for raw web-attribution conversion events. |
| raw_performance_data_kochava | the web-attribution provider-specific raw performance join data | auction_id, creative_id, timestamps | the client reporting pipeline | Contains a focused set of fields for the web-attribution provider attribution joins. |

## Common Field Conventions

Most the client Postgres models all inherit common metadata.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal identifier | UUID | the client Postgres | Primary key for most Postgres entities. Prefer this for internal Postgres joins. |
| created_at | Row creation timestamp | Timestamp without timezone | the client Postgres | Server default. |
| updated_at | Last update timestamp | Timestamp without timezone | the client Postgres | Server update timestamp. |
| created_by | User that created the row | UUID | the client Postgres | References user.id when set. |
| updated_by | User that last updated the row | UUID | the client Postgres | References user.id when set. |
| created_by_app | Application that created the ad object | UUID | the client Postgres | Present on ad objects. |
| updated_by_app | Application that updated the ad object | UUID | the client Postgres | Present on ad objects. |
| status | the client internal lifecycle status | String or integer depending on table | the client Postgres | Do not assume every table uses the same enum type (**all core objects use string**). Campaign/adset/ad status values are strings. |
| external_id | Downstream system identifier | String | the client Postgres / external ad server | Primary bridge from the client records to BW objects. |
| external_status | Downstream system status | String | the client Postgres / external ad server | Separate from the client internal status. |
| archived_at | Archive timestamp | Timestamp without timezone | the client Postgres | Present on campaign, adset, and ad. |
| archived_from_status | Status before archive | String | the client Postgres | Useful for audits, not active eligibility. |

## Business Definitions

| Object | Definition | Relevance |
|----|----|----|
| Organization | the client tenant / business entity that owns ad accounts. | Provides account hierarchy, timezone, inventory enablement, and financial context. |
| Ad account | Advertiser-level account under an organization. | Provides default currency, timezone, network/account restrictions, and ownership for campaigns and creatives. |
| Campaign | Top-level advertising initiative. | Provides objective, broad flight window, budget, frequency cap, campaign type, and network scoping. |
| Ad set | Delivery unit under a campaign, generally closest to a downstream line item. | Primary object for delivery configuration: bid, budget, dates, status, targeting, pacing, inventory, and tracker/pixel association. |
| Target | Targeting configuration for an ad set. | Defines eligible inventory, geo, demographics, devices, segments, genre, dayparting, language, and placement constraints. |
| Placement | Supply or inventory placement made available through a network. | Determines where an ad set may serve and may include a placement-level bid floor. |
| Ad | Renderable ad object under an ad set. | Links the ad set to creative assets and has its own status and rotation weight. |
| Creative | Creative asset metadata and approval state. | Indicates creative status, approval state, and deliverability context. |
| Media | Backing media object for a creative or segment data. | Useful for creative metadata and asset references. |
| Enhanced pixel | Measurement source for web conversion campaigns. | Links outcome events to ad sets for optimization. |
| App tracker | Measurement source for app promotion campaigns. | Links app metadata, MMP context, platform tracking URLs, and app-event outcomes to ad sets. |
| the web-attribution provider data | the web-attribution provider conversion and attribution data. | Connects enhanced pixels, conversion events, attributed impressions, ads, and attribution windows. |
| Custom segment | Audience segment available to an ad account or campaign. | Can affect targeting and model features when referenced by ad set targeting JSON. |
| Performance report tables | Hourly aggregate of delivery and outcomes. | Useful for pacing, spend, CTR/CVR, and model training labels. |
| Attributed conversion data | Conversion events attributed back to ads, creatives, campaigns, line items, pixels, or app trackers. | Useful for connecting outcomes to delivery and measurement configuration. |
| Raw logs / win logs | Lower-level auction and win-event data. | Useful for bid shading, clearing price, supply quality, contextual features, and ML training. |

## Entity Data Dictionary

### Organization: organization

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal organization UUID | UUID | the client Postgres | Parent of ad accounts. |
| name | Organization display name | String | the client Postgres | Descriptive; do not use as durable key. |
| organization_type | Organization category | String enum | the client Postgres | Defaults to regular. |
| network_id | Required/associated network | UUID | the client Postgres | Nullable. References network.id. |
| timezone | Organization timezone | String | the client Postgres | Required. Ad account timezone is more directly relevant for campaign/adset date normalization. |
| inventory_enabled | Whether inventory-specific behavior is enabled | Boolean | the client Postgres | Relevant for ad set inventory targeting rules. |
| credit_limit | Organization credit limit | Float | the client Postgres | Organization-level financial context. |
| status | Organization lifecycle status | String enum | the client Postgres | Pending/active/etc. |

### Ad Account: adaccount

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal ad account UUID | UUID | the client Postgres | Parent of campaigns and creatives. |
| organization_id | Owning organization | UUID | the client Postgres | References organization.id. |
| account_id | Linked internal account | UUID | the client Postgres | Nullable. |
| name | Ad account name | String | the client Postgres | Descriptive; do not use as durable key. |
| external_id | External account identifier | String | the client Postgres / external platform | Useful for downstream mapping. |
| domain | Advertiser/account domain | String | the client Postgres |  |
| category | Account category | String | the client Postgres | Political rules depend on this in current flows. |
| default_continent | Default geography group | String | the client Postgres |  |
| default_currency | Default currency | String | the client Postgres | Campaign creation uses this as campaign currency. |
| timezone | Ad account timezone | String | the client Postgres | Important: campaign/adset user-entered dates are normalized through this timezone. |
| attributes | Additional account attributes | JSON | the client Postgres |  |
| threshold_amount | Spend threshold | Integer | the client Postgres | Financial/account-control context. |
| legacy_pixel_enabled | Whether legacy pixels are enabled | Boolean | the client Postgres | Pixel integration behavior can vary. |
| status | client account status | String enum | the client Postgres | Defaults to paused. |
| external_status | External account status | String | the client Postgres / external platform | Nullable. |

### Campaign: campaign

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal campaign UUID | UUID | the client Postgres | Parent of ad sets. |
| adaccount_id | Owning ad account | UUID | the client Postgres | References adaccount.id. |
| external_id | Downstream campaign identifier | String | the client Postgres / external platform | Bridge to external systems and some logs. |
| name | Campaign name | String | the client Postgres | Descriptive; do not use as durable key. |
| currency | Campaign currency | String | the client Postgres | Usually from adaccount.default_currency. |
| start_date | Campaign start in account/user timezone representation | Timestamp | the client Postgres | Required. Use UTC fields for cross-system processing. |
| end_date | Campaign end in account/user timezone representation | Timestamp | the client Postgres | Nullable. |
| start_date_utc | Campaign start in UTC | Timestamp with timezone | the client Postgres | Preferred for cross-system date comparisons and pacing windows. |
| end_date_utc | Campaign end in UTC | Timestamp with timezone | the client Postgres | Nullable. |
| min_bid | Minimum bid | Integer | the client Postgres | Nullable. Not used. |
| max_bid | Maximum bid | Integer | the client Postgres | Nullable. Not used. |
| continents | Continent targeting / defaults | String | the client Postgres | Nullable. |
| budget_type | Campaign budget interpretation | String enum | the client Postgres | Current supported value includes spend including vendor fees. |
| objective_type | Campaign objective | String enum | the client Postgres | Known values include web_conversions, awareness, app_promotion. |
| lifetime_budget | Campaign lifetime budget | Float | the client Postgres | Max budget to spend of the campaigns lifetime |
| daily_budget | Campaign daily budget | Float | the client Postgres | Nullable. Cannot exceed lifetime budget in creation flow. |
| frequency_cap_duration | Frequency cap window duration (seconds) | Integer | the client Postgres | Must be paired with impressions when set. |
| frequency_cap_impressions | Impression count in cap window | Integer | the client Postgres | Must be paired with duration when set. |
| frequency_cap | Structured frequency cap config | JSON | the client Postgres | Nullable. Use as authoritative when populated. |
| network_id | Scoped network | UUID | the client Postgres | Nullable. References network.id. Required for scoped campaigns, disallowed for performance campaign path. |
| campaign_type | Campaign behavior type | String enum | the client Postgres | Known values include standard, legacy, performance, scoped. |
| status | the client campaign lifecycle status | String enum | the client Postgres | Known values include active, draft, error, pending, paused, deleted, completed, archived. |
| external_status | Downstream campaign status | String enum | the client Postgres / external platform | Known values include active, inactive. |
| advocacy | Political advocacy classification | String enum | the client Postgres | Required for political ad accounts; disallowed for non-political accounts. |
| jurisdiction_scope | Political jurisdiction scope | String enum | the client Postgres | Required for political ad accounts; disallowed for non-political accounts. |

### Ad Set: adset

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal ad set UUID | UUID | the client Postgres | Parent of ads and targeting. |
| campaign_id | Parent campaign | UUID | the client Postgres | References campaign.id. |
| external_id | Downstream ad set / line item identifier | String | the client Postgres / external platform | Important bridge to log data. |
| name | Ad set name | String | the client Postgres | Descriptive; do not use as durable key. |
| adset_type | Ad set creative/media type | String enum | the client Postgres | Current enum includes video. |
| budget_type | Ad set budget interpretation | String enum | the client Postgres | Current supported value includes spend including vendor fees. |
| lifetime_budget | Ad set lifetime budget | Float | the client Postgres | Max budget to spend over the ad sets lifetime |
| daily_budget | Ad set daily budget | Float | the client Postgres | Nullable. Cannot exceed lifetime budget in creation flow. |
| status | the client ad set lifecycle status | String enum | the client Postgres | Known values include active, draft, error, pending, paused, deleted, completed, archived. |
| external_status | Downstream line item status | String enum | the client Postgres / external platform | Known values include active, inactive. |
| guaranteed | Guaranteed delivery flag/value | Integer | the client Postgres | Nullable. Not used. |
| start_date | Ad set start in account/user timezone representation | Timestamp | the client Postgres | Required. |
| end_date | Ad set end in account/user timezone representation | Timestamp | the client Postgres | Nullable. |
| start_date_utc | Ad set start in UTC | Timestamp with timezone | the client Postgres | Preferred for cross-system date comparisons and pacing. |
| end_date_utc | Ad set end in UTC | Timestamp with timezone | the client Postgres | Nullable. |
| user_timezone | User/account timezone attached to ad set | String | the client Postgres | Nullable. |
| enable_skad_tracking | SKAd tracking flag/value | Integer | the client Postgres | Nullable. Relevant to app promotion / iOS measurement. |
| currency | Ad set currency | String | the client Postgres | Nullable. |
| bid | Ad set bid | Float | the client Postgres | CPM bid amount |
| fee | Ad set fee | Float | the client Postgres | Defaults to 0. |
| bidding | Structured bidding config | JSON | the client Postgres |  |
| bid_shading | Whether bid shading is enabled | Boolean | the client Postgres | Required. |
| bid_shading_control | Bid shading control mode | String | the client Postgres | Nullable. |
| frequency_cap_duration | Frequency cap window duration | Integer | the client Postgres | Must be paired with impressions when set. |
| frequency_cap_impressions | Impression count in cap window | Integer | the client Postgres | Must be paired with duration when set. |
| frequency_cap | Structured frequency cap config | JSON | the client Postgres | Nullable. |
| segment_extension | Segment extension config | JSON | the client Postgres | Nullable. Related constants include person/household modes. |
| regulated_content | Whether content is regulated | String | the client Postgres | Hybrid property defaults missing value to unregulated. |
| app_tracker_id | App tracker dependency | UUID | the client Postgres | Required by app promotion campaign flow. |
| inventory | Inventory-specific setting | String | the client Postgres | Nullable. Requires inventory-enabled account and specific network behavior. |

### Targeting: target

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal targeting row UUID | UUID | the client Postgres | Usually one target per ad set. |
| adset_id | Ad set being targeted | UUID | the client Postgres | References adset.id. |
| external_id | Downstream targeting identifier | String | the client Postgres / external platform | Nullable. |
| target | Full targeting payload | JSON | the client Postgres | Required. Broad container for targeting details. |
| location | Geo/location targeting | JSON | the client Postgres | Nullable. |
| age | Age targeting | JSON | the client Postgres | Nullable. |
| gender | Gender targeting | JSON | the client Postgres | Nullable. |
| advanced_demographic | Advanced demographic targeting | JSON | the client Postgres | Nullable. Political rules may restrict use. |
| device_type | Device targeting | JSON | the client Postgres | Nullable. Not allowed on some networks such as UK flow. |
| segment | Audience segment targeting | JSON | the client Postgres | Nullable. May reference custom segments or external segments. |
| genre | Genre targeting | JSON | the client Postgres | Nullable. Limited to specific networks / automatic network behavior. |
| day_part | Dayparting targeting | JSON | the client Postgres | Nullable. Current validation disallows overlapping or duplicate windows. |
| content_language | Content language targeting | JSON | the client Postgres | Nullable. Current validation allows at most one included language. |

### Placement: placement and target_placement

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| placement.id | the client internal placement UUID | UUID | the client Postgres | Referenced by target_placement.placement_id. |
| placement.name | Placement display name | String | the client Postgres | Descriptive. |
| placement.external_id | Downstream placement ID(s) | String | the client Postgres / external platform | Can contain comma-separated IDs; model exposes split_external_ids. |
| placement.network_id | Owning network | UUID | the client Postgres | References network.id. Must match campaign/adset network rules. |
| placement.status | Placement lifecycle status | String enum | the client Postgres | Defaults active. |
| placement.bid_floor | Placement bid floor | Float | the client Postgres | Nullable. Useful supply-side pricing context if populated. |
| target_placement.target_id | Targeting row | UUID | the client Postgres | References target.id. |
| target_placement.placement_id | Placement row | UUID | the client Postgres | References placement.id. |

### Ad: ad

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal ad UUID | UUID | the client Postgres | Joins to hourly performance_report_pipeline_merged.ad_id. |
| adset_id | Parent ad set | UUID | the client Postgres | References adset.id. |
| external_id | Downstream ad identifier | String | the client Postgres / external platform | Bridge to external systems. |
| name | Ad name | String | the client Postgres | Descriptive. |
| url | Destination or creative URL | String | the client Postgres | Nullable. |
| thumbnail_url | Thumbnail URL | String | the client Postgres | Nullable. |
| click_url | Click-through URL | String | the client Postgres | Nullable. |
| ad_type | Downstream ad type integer | Integer | the client Postgres | the ad server mapping: banner 0, video 1, native 2. |
| ad_template_type | Creative template ID | Integer | the client Postgres | Known values include VAST inline 3 and VAST inline dynamic 25. |
| status | the client ad lifecycle status | String enum | the client Postgres | Known values include active, pending, paused, rejected, archived. |
| external_status | Downstream ad status | String enum | the client Postgres / external platform | Known values include not_created, pending, active, inactive. |
| primary_creative_id | Primary creative | UUID | the client Postgres | References creative.id. Nullable. |
| secondary_creative_id | Secondary creative | UUID | the client Postgres | References creative.id. Nullable. |
| creative_duration | Creative duration (seconds) | Integer | the client Postgres | Nullable |
| rotation_weight | Ad rotation weight | Float | the client Postgres | Nullable. Must be between 0 and 1 when set. |
| clock_number | Clock number / traffic identifier | String | the client Postgres | Nullable. |

### Creative: creative

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal creative UUID | UUID | the client Postgres | Referenced by ads. |
| external_id | Downstream creative identifier | String | the client Postgres / external platform | Bridge to logs / ad server where applicable. |
| name | Creative name | String | the client Postgres | Nullable and descriptive. |
| url | Creative asset URL | String | the client Postgres | Nullable. |
| thumbnail_url | Creative thumbnail URL | String | the client Postgres | Nullable. |
| adaccount_id | Owning ad account | UUID | the client Postgres | References adaccount.id. |
| creative_asset_type_id | Creative type lookup | UUID | the client Postgres | References creative_asset_type.id. |
| creative_status_id | Internal creative status lookup | UUID | the client Postgres | References creative_internal_status.id. |
| external_creative_status_id | External creative status lookup | UUID | the client Postgres | References creative_external_status.id. |
| media_id | Backing media object | UUID | the client Postgres | References media.id. |
| duration | Creative duration | Interval | the client Postgres | Nullable. |
| political_details | Political creative metadata | JSON | the client Postgres | Nullable. |
| approval_status | Political/compliance approval status | String enum | the client Postgres | Deliverable values are approved or not_required. |
| jurisdiction_scope | Political jurisdiction scope | String enum | the client Postgres | Nullable. |

Creative deliverability should consider both internal creative status and approval status. Current helper logic treats a creative as deliverable when creative_status = active and approval_status is either approved or not_required.

### Media: media

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal media UUID | UUID | the client Postgres | Referenced by creative. |
| mime_type | Asset MIME type | String | the client Postgres | Required. |
| key | Object storage key | String | the client Postgres / object storage | Required. |
| bucket | Object storage bucket | String | the client Postgres / object storage | Required. |
| status | Media lifecycle status | String enum | the client Postgres | Defaults pending. |
| adaccount_id | Owning ad account | UUID | the client Postgres | Nullable. |
| application_id | Associated application identifier | String | the client Postgres | Nullable. This is a string and should not be assumed to equal application.id. |

### Delivery Overrides: adset_delivery_override

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal override UUID | UUID | the client Postgres | Admin-managed row. |
| adset_id | Ad set receiving overrides | UUID | the client Postgres | References adset.id; unique, so at most one override row per ad set. |
| publisher_exclusion_ids | Publisher IDs to exclude | JSON | the client Postgres admin data | Should be applied as targeting exclusions downstream. |
| included_deal_ids | Deal IDs explicitly included | JSON | the client Postgres admin data | Useful for PMP/deal-constrained delivery. |
| delivery_modifier_id | Downstream delivery modifier ID | Integer | the client Postgres admin data | If present, should take precedence over defaults. |
| bid_modifier | Bid modifier config | JSON | the client Postgres admin data | Downstream bid modifier identifier and min + max bids |
| pacing_type | Pacing override | String | the client Postgres admin data | Nullable |
| dynamic_creative_rotation | Whether dynamic creative rotation is enabled | Boolean | the client Postgres admin data | Defaults false. |
| creative_rotation_weights | Creative/ad rotation weight overrides | JSON | the client Postgres admin data | Nullable. |

Override precedence rule: when an override field is present, downstream sync logic should treat it as higher priority than the client-derived defaults.

### Enhanced Pixel and Conversion Measurement

#### Enhanced Pixel: enhanced_pixel

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal enhanced pixel UUID | UUID | the client Postgres | Referenced by ad set links and custom segments. |
| adaccount_id | Owning ad account | UUID | the client Postgres | References adaccount.id. |
| name | Pixel name | String | the client Postgres | Required. |
| status | Pixel status | String enum | the client Postgres | Required. |
| installation_type | Pixel installation type | String | the client Postgres | Required. |
| activity_key | Activity/event key | String | the client Postgres | Nullable. |
| event_source_id | Event source | UUID | the client Postgres | References event_sources.id. |

#### Ad Set Link: enhanced_pixel_adset_link

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| adset_id | Ad set using the enhanced pixel | UUID | the client Postgres | References adset.id. |
| enhanced_pixel_id | Enhanced pixel used for measurement | UUID | the client Postgres | References enhanced_pixel.id. |
| status | Link status | String enum | the client Postgres | Defaults active. |

#### Conversion Aggregates: conversion_data and pixel_events

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| pixel_id | the client internal pixel UUID | UUID | the client reporting pipeline | Present on conversion_data; nullable. |
| pixel_external_id | External pixel identifier | String | the client reporting pipeline | Join key for hourly conversion aggregates. |
| conversions | Conversion count | Integer | the client reporting pipeline | Nullable. |
| count | Pixel event count | Integer | the client reporting pipeline | Present on pixel_events. |
| hour | Local/reporting hour | Timestamp | the client reporting pipeline | Used with pixel ID for uniqueness. |
| hour_utc | UTC hour | Timestamp with timezone | the client reporting pipeline | Preferred for time-series modeling. |

#### Legacy Attributed Conversion Aggregates: attributed_conversion_data

One row represents one pixel_external_id x creative_external_id x hour. The table has a unique constraint on hour, pixel_external_id, and creative_external_id.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| pixel_id | the client internal pixel UUID | UUID | the client reporting pipeline | Nullable. |
| pixel_external_id | External pixel identifier | String | the client reporting pipeline | Used to connect attribution back to pixel-based measurement. |
| creative_id | the client internal creative UUID | UUID | the client reporting pipeline | Nullable. |
| creative_external_id | External creative identifier | String | the client reporting pipeline | Used with pixel and hour for uniqueness. |
| conversions | Attributed conversion count | Integer | the client reporting pipeline | Nullable. |
| hour | Local/reporting hour | Timestamp | the client reporting pipeline | Used in the unique aggregate key. |
| hour_utc | UTC reporting hour | Timestamp with timezone | the client reporting pipeline | Preferred for time-series joins. |

#### Legacy Raw Attributed Conversion Data: raw_attributed_conversion_data

Legacy raw attributed conversion data is lower-level than hourly aggregates and includes conversion identifiers, attribution method, downstream delivery identifiers, geo context, app bundle, and conversion value fields.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| conversion_id | Conversion event identifier | String | the client attribution pipeline | Useful for deduping and traceability. |
| conversion_ord / conversion_order | Conversion order fields | String | the client attribution pipeline |  |
| conversion_value | Parsed conversion value | Float | the client attribution pipeline | Nullable. |
| conversion_value_raw | Raw conversion value | String | the client attribution pipeline | Nullable. Useful for debugging parsing issues. |
| conversion_type | Conversion type | String | the client attribution pipeline | Nullable. |
| event_id | Event identifier | Integer | the client attribution pipeline | Nullable. |
| attribution_method | Method used to attribute the conversion | String | the client attribution pipeline | Nullable. |
| campaign_id | Downstream campaign identifier | Integer | the client attribution pipeline | Not a client UUID; map through campaign.external_id when appropriate. |
| line_item_id | Downstream line item/ad set identifier | Integer | the client attribution pipeline | Not a client UUID; map through adset.external_id when appropriate. |
| creative_id | Downstream creative identifier | Integer | the client attribution pipeline | Not a client UUID; map through external creative identifiers where available. |
| account_id | Downstream account identifier | Integer | the client attribution pipeline | Not a client UUID. |
| advertiser_id | Downstream advertiser identifier | Integer | the client attribution pipeline | Not a client UUID. |
| auction_id | Auction identifier | String | the client attribution pipeline | Useful for connecting conversion attribution to delivery events where available. |
| bid_time | Bid timestamp | Timestamp | the client attribution pipeline | Nullable. |
| bid_time_utc | UTC bid timestamp | Timestamp | the client attribution pipeline | Preferred for cross-system joins. |
| rx_timestamp | Receive timestamp | Timestamp | the client attribution pipeline | Nullable. |
| rx_timestamp_utc | UTC receive timestamp | Timestamp | the client attribution pipeline | Preferred for cross-system joins. |
| create_time_utc | UTC conversion creation timestamp | Timestamp | the client attribution pipeline | Nullable. |
| app_bundle | App bundle associated with the conversion | String | the client attribution pipeline | Supply/app context; not necessarily the client application UUID. |
| postback_url | Postback URL | String | the client attribution pipeline | Nullable. Treat as sensitive integration data. |
| geo_city, geo_country, geo_region, geo_zip, geo_metro | Geo fields associated with the conversion | String | the client attribution pipeline | Nullable. |
| test_group_id, experiment_user_index, test_plan_id, experiment_id_type | Experiment metadata | Integer/String | the client attribution pipeline | Nullable. |

### App Tracker and App Event Measurement

#### App Tracker: app_tracker

App trackers are used for app promotion measurement. An ad set can reference an app tracker through adset.app_tracker_id.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal app tracker UUID | UUID | the client Postgres | Referenced by adset.app_tracker_id, app event aggregates, and mobile app attribution tables. |
| adaccount_id | Owning ad account | UUID | the client Postgres | References adaccount.id. |
| name | Tracker name | String | the client Postgres | Required. |
| mmp | Mobile measurement partner | String | the client Postgres | Required. |
| ios_app_store_id | iOS App Store identifier | String | the client Postgres | Nullable. |
| android_package_name | Android package name | String | the client Postgres | Nullable. |
| app_name | App display name | String | the client Postgres | Required; descriptive, not a durable join key. |
| status | App tracker status | String | the client Postgres | Required. |
| event_source_id | Event source | UUID | the client Postgres | References event_sources.id. |

#### App Tracker Pixel: app_tracker_pixel

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal app tracker pixel UUID | UUID | the client Postgres | Primary key. |
| app_tracker_id | Parent app tracker | UUID | the client Postgres | References app_tracker.id. |
| impression_tracking_url | Platform-specific impression tracking URL | String | the client Postgres | Required. Treat as integration-sensitive. |
| platform | Platform for the tracking URL | String | the client Postgres | Required. |
| status | Pixel row status | String | the client Postgres | Required. |

#### App Event Conversion Aggregates: app_events_conversion_data

One row represents one app_tracker_id x event_name x hour. The table has a unique constraint on hour, app_tracker_id, and event_name.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| app_tracker_id | App tracker associated with the event | UUID | the client reporting pipeline | References app_tracker.id. |
| event_name | App event name | String | the client reporting pipeline | Required. |
| conversions | Conversion/event count | Integer | the client reporting pipeline | Nullable. |
| hour | Local/reporting hour | Timestamp | the client reporting pipeline | Nullable. |
| hour_utc | UTC reporting hour | Timestamp with timezone | the client reporting pipeline | Nullable; preferred when populated. |

#### Mobile App Event Attribution: mobile_app_event_7_day_attribution, mobile_app_event_14_day_attribution, mobile_app_event_30_day_attribution

These tables share the same structure and differ by attribution window. Each table has a unique constraint on conversion_id.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| conversion_id | Conversion identifier | String | the client attribution pipeline | Unique within each attribution window table. |
| event_name | App event name | String | the client attribution pipeline | Required. |
| event_timestamp_utc | UTC timestamp of the app event | Timestamp with timezone | the client attribution pipeline | Required. |
| app_tracker_id | App tracker associated with the event | UUID | the client attribution pipeline | Nullable. References app_tracker.id. |
| ad_id | the client internal ad UUID | UUID | the client attribution pipeline | Required. References ad.id. |
| app_id | App identifier from the event/source system | String | the client attribution pipeline | Required. Do not assume this is application.id. |
| device_id | Device identifier | String | the client attribution pipeline | Nullable. Treat as privacy-sensitive. |
| device_platform | Device platform | String | the client attribution pipeline | Nullable. |
| impression_id | Impression identifier | String | the client attribution pipeline | Required. |
| ip_address | IP address | String | the client attribution pipeline | Nullable. Treat as privacy-sensitive. |
| bid_hour_utc | UTC bid hour | Timestamp | the client attribution pipeline | Required. |
| bid_time_utc | UTC bid timestamp | Timestamp | the client attribution pipeline | Nullable. |
| revenue | Revenue associated with the event | Float | the client attribution pipeline | Nullable. |
| hhid | Household identifier | String | the client attribution pipeline | Nullable. Treat as privacy-sensitive. |
| ingested_at | Ingestion timestamp | Timestamp | the client attribution pipeline | Required. |

### the web-attribution provider Conversion and Attribution Data

The web-attribution provider data appears in both the client Postgres-style models and query/reporting-layer models. The Postgres attribution tables are keyed by enhanced_pixel_id, conversion_id, and optionally ad_id. The reporting/query models expose raw the web-attribution provider events and gold attribution tables for 7-day, 14-day, and 30-day windows.

#### Web-Attribution Raw Event Data: kochava_data

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| transaction_id | the web-attribution provider transaction identifier | Text | the client Postgres / the web-attribution provider ingest | Nullable in the model. |
| advertiser_name | Advertiser name from the web-attribution provider data | Text | the web-attribution provider ingest | Descriptive. |
| event_timestamp | Event timestamp | Timestamp | the web-attribution provider ingest | Nullable. |
| event_timestamp_hour | Event timestamp truncated/aggregated to hour | Timestamp | the web-attribution provider ingest | Nullable. |
| ip_address | IP address associated with the event | Text | the web-attribution provider ingest | Nullable. Treat as privacy-sensitive. |
| event_name | the web-attribution provider event name | Text | the web-attribution provider ingest | Nullable. |
| user_id | User identifier | Text | the web-attribution provider ingest | Nullable. Treat as privacy-sensitive. |
| page_url | Page URL associated with the event | Text | the web-attribution provider ingest | Nullable. |
| user_email | User email | Text | the web-attribution provider ingest | Nullable. Treat as sensitive personal data. |
| product_name | Product name | Text | the web-attribution provider ingest | Nullable. |
| referrer_url | Referrer URL | Text | the web-attribution provider ingest | Nullable. |
| product_id | Product identifier | Text | the web-attribution provider ingest | Nullable. |
| item_quantity | Item quantity | Text | the web-attribution provider ingest | Nullable. |
| total_price | Total price | Float | the web-attribution provider ingest | Nullable. |
| currency_code | Currency code | Text | the web-attribution provider ingest | Nullable. |
| order_id | Order identifier | Text | the web-attribution provider ingest | Nullable. |

#### Web-Attribution Conversion Aggregate: kochava_conversion_data

One row represents one enhanced_pixel_id x event_name x hour. The table has a unique constraint on hour, enhanced_pixel_id, and event_name.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| enhanced_pixel_id | Enhanced pixel associated with the web-attribution provider event | UUID | the client reporting pipeline | References enhanced_pixel.id. |
| event_name | the web-attribution provider event name | String | the client reporting pipeline | Required. |
| conversions | Conversion/event count | Integer | the client reporting pipeline | Nullable. |
| hour | Local/reporting hour | Timestamp | the client reporting pipeline | Nullable. |
| hour_utc | UTC reporting hour | Timestamp with timezone | the client reporting pipeline | Nullable; preferred when populated. |

#### Web Attribution: kochava_seven_day_attribution, kochava_fourteen_day_attribution, kochava_thirty_day_attribution

These tables share the same structure and differ by attribution window. Each table has a unique constraint on conversion_id.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| conversion_id | the web-attribution provider conversion identifier | String | the client attribution pipeline | Unique within each attribution window table. |
| enhanced_pixel_id | Enhanced pixel associated with the conversion | UUID | the client attribution pipeline | Required. References enhanced_pixel.id. |
| event_name | the web-attribution provider event name | String | the client attribution pipeline | Required, retained in case events are deleted elsewhere. |
| ad_id | the client internal ad UUID | UUID | the client attribution pipeline | Nullable. References ad.id. |
| impression_id | the DSP impression identifier | String | the client attribution pipeline | Required. |
| user_id | User identifier for the conversion | String | the client attribution pipeline | Required in the model. Treat as privacy-sensitive. |
| event_timestamp | Event timestamp | Timestamp | the client attribution pipeline | Required. |
| event_timestamp_utc | UTC event timestamp | Timestamp with timezone | the client attribution pipeline | Required; preferred for cross-system joins. |
| bid_hour | Bid hour | Timestamp | the client attribution pipeline | Required. |
| bid_hour_utc | UTC bid hour | Timestamp | the client attribution pipeline | Required. |
| bid_time_utc | UTC bid timestamp | Timestamp | the client attribution pipeline | Nullable. |
| order_id | Order identifier | String | the client attribution pipeline | Nullable. |
| ga_client_id | Google Analytics client identifier | String | the client attribution pipeline | Nullable. Treat as sensitive identifier data. |
| price | Conversion price/value | Float | the client attribution pipeline | Nullable. |
| hhid | the ad server household identifier | String | the client attribution pipeline | Nullable. Treat as privacy-sensitive. |
| url | Event URL | String | the client attribution pipeline | Nullable. |
| referral_from | Referral source URL/string | String | the client attribution pipeline | Nullable. |

#### Gold Web Attribution: gold_kochava_seven_day_attribution, gold_kochava_fourteen_day_attribution, gold_kochava_thirty_day_attribution

The gold the web-attribution provider attribution models are query-only mappings with similar attribution fields plus reporting-layer metadata.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| conversion_id | the web-attribution provider conversion identifier | String | Warehouse/query source | Primary key for query mapping. |
| enhanced_pixel_id | Enhanced pixel identifier | String | Warehouse/query source | Stored as string in the query model. |
| event_name | the web-attribution provider event name | String | Warehouse/query source | Nullable in query mapping. |
| ad_id | Ad identifier | String | Warehouse/query source | Stored as string in the query model. |
| impression_id | Impression identifier | String | Warehouse/query source | Nullable in query mapping. |
| user_id | User identifier | String | Warehouse/query source | Treat as privacy-sensitive. |
| event_timestamp, event_timestamp_utc | Event timestamps | Timestamp | Warehouse/query source | UTC field preferred for time-series joins. |
| bid_hour, bid_hour_utc, bid_time_utc | Bid timestamps | Timestamp | Warehouse/query source | UTC fields preferred. |
| price | Conversion price/value | Float | Warehouse/query source | Nullable. |
| order_id | Order identifier | String | Warehouse/query source | Nullable. |
| ga_client_id | Google Analytics client identifier | String | Warehouse/query source | Nullable. Treat as sensitive identifier data. |
| hhid | Household identifier | String | Warehouse/query source | Nullable. Treat as privacy-sensitive. |
| ingested_at | Ingestion timestamp | Timestamp | Warehouse/query source | Useful for freshness/debugging. |
| load_id | Pipeline load identifier | String | Warehouse/query source | Useful for lineage/debugging. |
| adaccount_id | Ad account identifier | String | Warehouse/query source | Stored as string in the query model. |

#### Raw Web-Attribution Conversion Source: kochava

The kochava query model represents raw web-attribution conversion events and includes partition columns.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| transaction_id | the web-attribution provider transaction identifier | String | Warehouse/query source | Primary key for query mapping. |
| event_name | the web-attribution provider event name | String | Warehouse/query source | Nullable. |
| event_product | Product/event product payload | String | Warehouse/query source | Nullable. |
| event_timestamp | Event timestamp | Timestamp | Warehouse/query source | Nullable. |
| event_ip | Event IP address | String | Warehouse/query source | Treat as privacy-sensitive. |
| event_user_agent | Event user agent | String | Warehouse/query source | Nullable. |
| event_metadata | Raw event metadata | String | Warehouse/query source |  |
| pixel_id | Pixel identifier partition/context field | String | Warehouse/query source | Not necessarily a client UUID. |
| yyyy, mm, dd, hh | Partition columns | String | Warehouse/query source | Used for partition pruning. |

#### the web-attribution provider-Specific Raw Performance Data: raw_performance_data_kochava

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| auction_id | Auction identifier | Text | the client reporting pipeline | Useful for joining attributed events to delivery context where available. |
| auction_adgroup_id | Auction ad group identifier | Text | the client reporting pipeline | Nullable. |
| bid_hour | Bid hour | Timestamp | the client reporting pipeline | Nullable. |
| bid_time | Bid timestamp | Timestamp | the client reporting pipeline | Nullable. |
| bid_time_utc | UTC bid timestamp | Timestamp | the client reporting pipeline | Preferred for cross-system joins. |
| creative_id | Downstream creative identifier | Integer | the client reporting pipeline | Not a client UUID. |
| creative_alt_id | Alternative creative identifier | Text | the client reporting pipeline | Nullable. |
| ip_address | IP address from request context | Text | the client reporting pipeline | Treat as privacy-sensitive. |
| ipv6_address | IPv6 address from request context | Text | the client reporting pipeline | Treat as privacy-sensitive. |
| impression_ip_address | Impression IP address | Text | the client reporting pipeline | Treat as privacy-sensitive. |
| rx_timestamp_utc | UTC receive timestamp | Timestamp | the client reporting pipeline | Nullable. |

### Custom Segments: custom_segments

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| id | the client internal segment UUID | UUID | the client Postgres | May be referenced in targeting JSON. |
| segment_key | Internal segment key | String | the client Postgres | Required. |
| external_id | Downstream segment identifier | String | the client Postgres / external platform | Use for downstream matching where required. |
| adaccount_id | Owning ad account | UUID | the client Postgres | References adaccount.id. |
| name | Segment name | String | the client Postgres | Descriptive. |
| active | Whether segment is active | Boolean | the client Postgres | Required. |
| pixel_id | Legacy pixel source | UUID | the client Postgres | Nullable. |
| enhanced_pixel_id | Enhanced pixel source | UUID | the client Postgres | Nullable. |
| retention_period | Segment retention window (days) | Integer | the client Postgres | Nullable |
| event_type | Segment event type | String | the client Postgres | Nullable. |
| segment_type | Segment type | String | the client Postgres | Required. |
| size | Segment size | Integer | the client Postgres / external platform | Nullable. May lag actual population. |
| segment_source | Segment source | String | the client Postgres | Examples in code comments include customer_list, ad_viewers, klaviyo. |
| ad_viewer_source | Scope for ad-viewer segment | String | the client Postgres | Examples include ad_account, campaign. |
| campaign_id | Campaign source for campaign-scoped ad-viewer segments | UUID | the client Postgres | Nullable. References campaign.id. |

## Reporting and Log Data Dictionary

### Hourly Performance Aggregate: performance_report_pipeline_merged

One row represents one ad_id x hour. The model has a unique constraint on hour and ad_id.

| Field | Definition | Type | Source | Notes / Rules |
|----|----|----|----|----|
| ad_id | the client internal ad UUID | UUID | the client reporting pipeline | Joins to ad.id. |
| ad_external_id | Downstream ad ID | String | the client reporting pipeline | Bridge to downstream systems. |
| hour | Reporting hour | Timestamp | the client reporting pipeline | Local/reporting timezone representation. |
| hour_utc | UTC reporting hour | Timestamp with timezone | the client reporting pipeline | Preferred for modeling and joins across systems. |
| impressions | Served impression count | Integer | the client reporting pipeline | Nullable. |
| clicks | Click count | Integer | the client reporting pipeline | Nullable. |
| conversions | Conversion count | Integer | the client reporting pipeline | Nullable. |
| spend | Total spend | Float | the client reporting pipeline | Gross spend |
| media_spend | Media cost component | Float | the client reporting pipeline | Useful for cost analysis. |
| vendor_fee_spend | Vendor fee spend component | Float | the client reporting pipeline | Useful for gross/net reconciliation. |
| reach | Estimated unique reach | Integer | the client reporting pipeline | Nullable. |
| frequency | Average frequency | Float | the client reporting pipeline | Nullable. |
| ctr | Click-through rate | Float | the client reporting pipeline | Derived metric. |
| cpc | Cost per click | Float | the client reporting pipeline | Derived metric. |
| cpm | Cost per mille | Float | the client reporting pipeline | Derived metric. |
| cpa | Cost per acquisition/conversion | Float | the client reporting pipeline | Derived metric. |
| conversion_rate | Conversion rate | Float | the client reporting pipeline | Derived metric. |
| video_plays | Video starts/plays | Integer | the client reporting pipeline | Nullable. |
| video_completes | Video completions | Integer | the client reporting pipeline | Nullable. |
| q1, q2, q3 | Video quartile counts | Integer | the client reporting pipeline | q2 corresponds to midpoint. |
| vcr | Video completion rate | Float | the client reporting pipeline | Derived metric. |
| cpcv | Cost per completed view | Float | the client reporting pipeline | Derived metric. |

### Raw Performance / Win Logs: raw_performance_data and win_logs

Raw logs are broader than the Postgres campaign hierarchy. They include downstream ad-server IDs, auction context, bid prices, inventory metadata, geo/device fields, cost fields, conversion fields, and model metadata. The client stores raw DSP delivery/win-log data and raw conversion data in S3. The models in this guide describe the fields the client exposes or queries from those datasets, but the raw storage layout, ingestion flow, and pipeline transformations are covered in the separate data and pipeline documentation. For the upstream DSP batch log schemas, see [Data Schema](link-redacted-dsp-api). Important caveat: in raw logs, fields such as campaign_id, line_item_id, creative_id, and account_id are integers and represent downstream platform IDs, not the client internal UUIDs.

| Field group | Example fields | Meaning | Relevant use |
|----|----|----|----|
| Downstream IDs | account_id, campaign_id, line_item_id, creative_id, advertiser_id, flight_id | External ad-server identifiers | Join to the client config through the corresponding external_id field using the documented downstream ID mapping. |
| Auction IDs | auction_id, exchange_auction_id, exchange_imp_id, request_id | Auction / impression request identity | Deduping, traceability, request-level modeling. |
| Time | bid_time, bid_time_utc, bid_hour, rx_timestamp_utc, bid_time_epoch_in_usecs | Bid and receive timestamps | Time-window features, pacing, recency, hourly aggregation. |
| Bid prices | bid_price_micros_usd, bid_price_micros, pre_reduction_bid_price_micros_usd, bid_floor_micros, bid_floor_currency | Bid and floor prices, often in micros | Bid landscape and price-response modeling. Convert micros before financial reporting. |
| Bid shading / modifiers | bid_shade, bid_shade_reduction_micros, bid_modifier_id, bid_modifier_multipliers_product | Bid-shading and modifier outcomes | Model diagnostics and override feedback. |
| Models / agents | bidding_strategy_id, model_id, delivery_model_id, bid_model_id, bid_agent_id, params fields | Downstream/model metadata | Feature attribution, A/B analysis, and lineage. |
| Costs and fees | clearing_price_micros_usd, win_cost_micros_usd, media_spend_micros_usd, vendor_fee_micros_usd, total_vendor_fees_micros_usd | Auction clearing and spend components | Pacing, cost prediction, margin/gross-net reconciliation. |
| Revenue | campaign_revenue_amount_micros, line_item_revenue_amount_micros, revenue_amount_micros | Revenue configured downstream | ROAS / objective modeling if applicable. |
| Performance | clicks, conversions, conversion_value, ip_conversions, video/audio metrics | Outcome events attached to logs | Labels and KPI calculations. |
| App / site | app_id, app_bundle, app_name, site_id, site_name, domain, page_url | Supply context | Contextual features and supply joins. |
| Placement / inventory | placement, placement_type, inventory_source, inventory_source_relationship, deal_id | Supply placement and deal context | Placement, deal, and supply performance analysis. |
| Geo | geo_country, geo_region, geo_city, geo_zip, geo_lat, geo_lon, geo_type, geo_metro | Location context | Geo targeting validation and model features. |
| Device/platform | platform_os, platform_browser, platform_device_type, platform_device_make, platform_device_model, platform_carrier, platform_device_ifa, platform_device_idfa | User/device context | Device performance modeling; handle privacy requirements. |
| Content | content_title, content_genre, content_language, content_rating, content_network_name, content_channel_name, content_keywords | Contextual content metadata | Contextual targeting and ML features. |
| Segments | segment_id, targeted_segments, matched_user_groups, targeted_lat_long_lists | Audience/segment match context | Segment performance and lookback features. |
| Privacy | is_gdpr, is_gdpr_consented, gdpr_consent_string, us_privacy, dnt, lmt | Consent/privacy signals | Required for privacy-aware feature use and retention rules. |

## Relationship and Join Rules

### Configuration joins in Postgres

Use UUID primary keys for configuration data:

select\
org.id as organization_id,\
aa.id as adaccount_id,\
c.id as campaign_id,\
aset.id as adset_id,\
ad.id as ad_id,\
cr.id as creative_id\
from organization org\
join adaccount aa on aa.organization_id = org.id\
join campaign c on c.adaccount_id = aa.id\
join adset aset on aset.campaign_id = c.id\
join ad ad on ad.adset_id = aset.id\
left join creative cr on cr.id = ad.primary_creative_id;

### Targeting and placement joins

select\
aset.id as adset_id,\
t.id as target_id,\
p.id as placement_id,\
p.external_id as placement_external_id,\
p.bid_floor\
from adset aset\
join target t on t.adset_id = aset.id\
left join target_placement tp on tp.target_id = t.id\
left join placement p on p.id = tp.placement_id;

### Ad set to enhanced pixel joins

select\
aset.id as adset_id,\
ep.id as enhanced_pixel_id,\
ep.name as enhanced_pixel_name,\
ep.status as enhanced_pixel_status\
from adset aset\
join enhanced_pixel_adset_link link on link.adset_id = aset.id\
join enhanced_pixel ep on ep.id = link.enhanced_pixel_id\
where link.status = 'active';

### Ad set to app tracker joins

select\
aset.id as adset_id,\
tracker.id as app_tracker_id,\
tracker.name as app_tracker_name,\
tracker.mmp,\
tracker.ios_app_store_id,\
tracker.android_package_name,\
tracker.app_name,\
tracker.status as app_tracker_status\
from adset aset\
left join app_tracker tracker on tracker.id = aset.app_tracker_id;

### App event conversion aggregate join

select\
aec.hour_utc,\
tracker.id as app_tracker_id,\
tracker.app_name,\
aec.event_name,\
aec.conversions\
from app_events_conversion_data aec\
join app_tracker tracker on tracker.id = aec.app_tracker_id;

### Attributed conversion aggregate join

select\
ac.hour_utc,\
ac.pixel_external_id,\
ac.creative_external_id,\
cr.id as ua_creative_id,\
ac.conversions\
from attributed_conversion_data ac\
left join creative cr on cr.external_id = ac.creative_external_id;

### Mobile app attribution join

select\
maa.event_timestamp_utc,\
maa.bid_hour_utc,\
maa.event_name,\
maa.conversion_id,\
aa.id as adaccount_id,\
c.id as campaign_id,\
aset.id as adset_id,\
ad.id as ad_id,\
tracker.id as app_tracker_id,\
tracker.app_name,\
maa.revenue\
from mobile_app_event_7_day_attribution maa\
join ad ad on ad.id = maa.ad_id\
join adset aset on aset.id = ad.adset_id\
join campaign c on c.id = aset.campaign_id\
join adaccount aa on aa.id = c.adaccount_id\
left join app_tracker tracker on tracker.id = maa.app_tracker_id;

### the web-attribution provider conversion aggregate join

select\
kc.hour_utc,\
ep.id as enhanced_pixel_id,\
ep.name as enhanced_pixel_name,\
kc.event_name,\
kc.conversions\
from kochava_conversion_data kc\
join enhanced_pixel ep on ep.id = kc.enhanced_pixel_id;

### the web-attribution provider attribution join

select\
ka.event_timestamp_utc,\
ka.bid_hour_utc,\
ka.event_name,\
ka.conversion_id,\
ep.id as enhanced_pixel_id,\
aa.id as adaccount_id,\
c.id as campaign_id,\
aset.id as adset_id,\
ad.id as ad_id,\
ka.price\
from kochava_seven_day_attribution ka\
join enhanced_pixel ep on ep.id = ka.enhanced_pixel_id\
left join ad ad on ad.id = ka.ad_id\
left join adset aset on aset.id = ad.adset_id\
left join campaign c on c.id = aset.campaign_id\
left join adaccount aa on aa.id = c.adaccount_id;

### Reporting aggregate join

Hourly performance_report_pipeline_merged uses the client internal ad_id:

select\
pr.hour_utc,\
c.id as campaign_id,\
aset.id as adset_id,\
ad.id as ad_id,\
pr.impressions,\
pr.clicks,\
pr.conversions,\
pr.spend,\
pr.media_spend,\
pr.vendor_fee_spend\
from performance_report_pipeline_merged pr\
join ad ad on ad.id = pr.ad_id\
join adset aset on aset.id = ad.adset_id\
join campaign c on c.id = aset.campaign_id;

### Raw log join warning

For raw logs, use downstream IDs to join through the corresponding the client external_id fields. The example below is illustrative:

-- Illustrative example; use the validated downstream-ID mapping for production joins.\
select\
raw.bid_time_utc,\
c.id as ua_campaign_id,\
aset.id as ua_adset_id,\
raw.campaign_id as downstream_campaign_id,\
raw.line_item_id as downstream_line_item_id,\
raw.creative_id as downstream_creative_id,\
raw.bid_price_micros_usd,\
raw.win_cost_micros_usd,\
raw.app_id,\
raw.app_bundle,\
raw.app_name\
from raw_performance_data raw\
left join campaign c on c.external_id = raw.campaign_id::text\
left join adset aset on aset.external_id = raw.line_item_id::text;

## Source-of-Truth Rules

| Data | Source of truth | Consumer rule |
|----|----|----|
| the client hierarchy | Postgres organization -\> adaccount -\> campaign -\> adset -\> ad | Use UUIDs for internal hierarchy joins. |
| Downstream IDs | external_id fields on the client config objects | For the client objects represented in the DSP, external_id stores the corresponding the DSP object ID. The client object’s internal id is stored in the DSP as alt_id, providing a direct mapping between the client and BW records. |
| Entity Statuses | the client status fields are the source of truth for entity lifecycle state. | the client status, downstream external_status, archive state, and flight dates together determine whether an entity is eligible for delivery in BW. |
| Budgets | Campaign/adset budget fields in Postgres | Enforced at campaign first level, then ad set |
| Pacing / delivery override | adset_delivery_override when present | Override table should take precedence over normal the client defaults. |
| Targeting | target JSON plus target_placement / placement rows | Do not infer all targeting from flattened columns alone. |
| Creative eligibility | creative status lookups plus approval_status; ad status also matters | Creative approval can block delivery even if an ad set is active. |
| Spend and performance | Reporting pipeline / raw logs | Use UTC hour for time-series joins. |
| App event measurement | app_tracker, app_events_conversion_data, and mobile_app_event\_\*\_day_attribution | Use app_tracker_id for app-event measurement joins when available. |
| Attributed conversions | attributed_conversion_data and raw_attributed_conversion_data | Use attributed aggregates for pixel/creative/hour summaries and raw data for conversion-level traceability. |
| the web-attribution provider conversions | kochava_conversion_data, kochava\_*day_attribution, gold_kochava*\_day_attribution, kochava, and kochava_data | Use enhanced_pixel_id where available; treat raw/query-layer IDs as strings unless explicitly mapped. |
| App / supply identifiers | Log fields such as app_id, app_bundle, app_name | Treat app identifiers in delivery data as supply/provider identifiers, not the client internal application UUIDs unless explicitly mapped. |
| Names | name, app_name, site_name, publisher_name | Descriptive only. Do not use names as durable join keys. |

## Easy-to-Misinterpret Details

- The client Postgres entity IDs are UUIDs. Entities map to raw delivery logs through external_id fields containing downstream integer identifiers.

- campaign.id is a client UUID; raw campaign_id is a downstream integer ID.

- adset.id is a client UUID; raw line_item_id is the downstream line item/ad set identifier.

- ad.id is a client UUID; performance_report_pipeline_merged.ad_id is also a UUID and is safe to join to ad.id.

- creative.id is a client UUID; raw creative_id is a downstream integer ID.

- application.id is the client/developer application metadata. Delivery-log app_id, app_bundle, and app_name describe inventory/supply context and should not be assumed to join to application.id.

- app_tracker.id is the client UUID for app measurement configuration. It is not the same as delivery-log app_id.

- app_tracker.app_name is descriptive and should not be used as a durable join key.

- The web-attribution provider attribution tables use enhanced_pixel_id, while app-event attribution tables use app_tracker_id.

- kochava\_\*\_day_attribution.ad_id is nullable, so some web-attributed conversions may not join all the way to ad, ad set, or campaign.

- gold_kochava\_\*\_day_attribution stores IDs as strings in query-only mappings, unlike the UUID fields in the client Postgres models.

- media.application_id is a nullable string, not a UUID foreign key to application.id.

- name, app_name, site_name, and similar fields are descriptive and should not be used as durable join keys.

- start_date / end_date and start_date_utc / end_date_utc both exist on campaigns and ad sets. Runtime systems should prefer UTC fields.

- status and external_status are separate. A the client object can exist locally before or after downstream sync.

- Budget fields are floats in Postgres, while raw log cost fields are often micros. Convert and reconcile before comparing.

- Some JSON fields are business-critical, especially adset.bidding, adset.frequency_cap, target.*, delivery.delivery, and adset_delivery_override.*.

- Placement external_id may contain comma-separated values. Use the split semantics if mapping bid requests to placement IDs.

- Admin overrides are intentionally separate from normal advertiser-managed ad set and targeting data.

## Relevant Data Groups

### Status / Control Data

| Feature | Source |
|----|----|
| Campaign/adset/ad active flags | campaign.status, adset.status, ad.status |
| Downstream active flags | external_status fields |
| Flight windows | campaign.start_date_utc, campaign.end_date_utc, adset.start_date_utc, adset.end_date_utc |
| Daily/lifetime budgets | campaign.daily_budget, campaign.lifetime_budget, adset.daily_budget, adset.lifetime_budget |
| Bid | adset.bid, adset.bidding |
| Frequency cap | campaign/adset frequency cap fields |
| Pacing override | adset_delivery_override.pacing_type |
| Bid/delivery modifiers | adset_delivery_override.delivery_modifier_id, adset_delivery_override.bid_modifier |
| Creative rotation | ad.rotation_weight, adset_delivery_override.dynamic_creative_rotation, creative_rotation_weights |

### Targeting / Context Data

| Feature | Source |
|----|----|
| Placement IDs and bid floors | target_placement, placement.external_id, placement.bid_floor |
| Geo targeting | target.location |
| Age/gender targeting | target.age, target.gender |
| Device targeting | target.device_type |
| Audience segments | target.segment, custom_segments where referenced |
| Genre/contextual targeting | target.genre, raw log content fields |
| Dayparting | target.day_part |
| Content language | target.content_language |
| Inventory | adset.inventory, raw inventory_source fields |
| Deal restrictions | adset_delivery_override.included_deal_ids, raw deal_id |
| Publisher exclusions | adset_delivery_override.publisher_exclusion_ids, raw publisher_id |

### Performance / Measurement Data

| Feature | Source |
|----|----|
| Impressions, clicks, conversions | performance_report_pipeline_merged, raw logs |
| Attributed web conversions | attributed_conversion_data, raw_attributed_conversion_data |
| App event conversions | app_events_conversion_data, mobile_app_event_7_day_attribution, mobile_app_event_14_day_attribution, mobile_app_event_30_day_attribution |
| the web-attribution provider conversions and attribution | kochava_conversion_data, kochava_seven_day_attribution, kochava_fourteen_day_attribution, kochava_thirty_day_attribution, gold_kochava\_\*\_day_attribution, kochava |
| Spend | performance_report_pipeline_merged.spend, media_spend, vendor_fee_spend; raw micros cost fields |
| Bid price and bid floor | raw bid_price_micros, bid_floor_micros |
| CTR, CVR, CPA, CPM, CPC | performance_report_pipeline_merged derived metrics or recomputed from raw data |
| App/site performance | raw app_id, app_bundle, site_id, domain, publisher_id |
| Device performance | raw platform/device fields |
| Geo performance | raw geo fields |
| Content performance | raw content fields |
| Model lineage | raw model_id, bid_model_id, bid_agent_id, params fields |
