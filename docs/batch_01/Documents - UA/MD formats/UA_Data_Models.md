# Data Models

# UA Data Dictionary and Relationship Guide

## Purpose

UA is sharing relevant campaign, ad set, targeting, creative, delivery, and performance data with the partner teams. This includes contextual and operational information such as flight dates, status, budgets, targeting rules, delivery overrides, pacing, spend, and historical bid/win/conversion signals.
This document is intended to explain what the data means and how the major entities relate to each other. It is not a raw database schema dump.

## Audience

- Engineering teams consuming UA configuration data from Postgres.
- Data science / ML teams using pacing, spend, and performance data.
- Data engineering teams joining UA configuration data to win logs, bid requests, spend, and conversion datasets.

## Scope

This guide covers the core advertiser configuration and reporting entities visible in the UA backend models:

- Organization and ad account ownership.
- Campaign, ad set, ad, creative, media, targeting, and placements.
- Enhanced pixel, app tracker, and conversion measurement relationships.
- Raw delivery / win-log-style data and hourly reporting aggregates.
- Relationship and join guidance for the relevant data.

This guide should be reviewed against the production warehouse / event-log contracts before creating hard dependencies on delivery-log field names or grain.

## Core Grain Summary

| Dataset | Grain | Primary join keys | Source of truth | Notes |
| --- | --- | --- | --- | --- |
| organization | One row per UA organization | organization.id | UA Postgres | Business owner / tenant-level context. |
| adaccount | One row per advertiser account | adaccount.id, organization\_id | UA Postgres | Campaigns live under ad accounts. |
| campaign | One row per campaign | campaign.id, adaccount\_id, external\_id | UA Postgres | Top-level flight, budget, objective, and status settings. |
| adset | One row per ad set / downstream line item | adset.id, campaign\_id, external\_id | UA Postgres | Primary delivery configuration object. Contains bid, budget, dates, pacing-related fields, inventory, and tracker links. |
| target | One row per ad set | target.id, adset\_id | UA Postgres | Targeting criteria are mostly JSON fields. |
| target\_placement | One row per target-placement association | target\_id, placement\_id | UA Postgres | Normalized join between targeting and placements. |
| placement | One row per available placement | placement.id, external\_id, network\_id | UA Postgres | Placement names and external placement identifiers. |
| ad | One row per ad under an ad set | ad.id, adset\_id, external\_id | UA Postgres | Links ad delivery object to creative assets. |
| creative | One row per creative asset record | creative.id, external\_id, media\_id | UA Postgres | Creative eligibility, approval state, and media linkage. |
| media | One row per uploaded media object | media.id | UA Postgres / object storage | Contains object storage key and bucket, not necessarily a public URL. |
| adset\_delivery\_override | At most one row per ad set | adset\_id | UA Postgres admin data | Admin-managed delivery and pacing overrides that should take precedence over normal defaults. |
| app\_tracker | One row per app measurement tracker | app\_tracker.id, adaccount\_id | UA Postgres | Used by app promotion ad sets and app event measurement. |
| app\_tracker\_pixel | One row per platform-specific app tracker pixel URL | app\_tracker\_id, platform | UA Postgres | Stores impression tracking URLs by platform. |
| performance\_report\_pipeline\_merged | One row per ad\_id x hour | ad\_id, hour, hour\_utc | UA reporting pipeline | Aggregated delivery/performance metrics. |
| raw\_performance\_data | Event/log export grain, usually lower than report aggregate | downstream IDs such as campaign\_id, line\_item\_id, creative\_id | Log / reporting pipeline | Contains auction, bid, inventory, device, geo, spend, and performance fields. |
| win\_logs | Win-log query structure, not a Postgres table model | downstream IDs such as campaign\_id, line\_item\_id, creative\_id | Parquet / Athena / DuckDB query source | Used for safe query generation against external log data. |
| conversion\_data | One row per pixel\_external\_id x hour | pixel\_external\_id, hour, hour\_utc | UA reporting pipeline | Hourly conversion aggregate. |
| attributed\_conversion\_data | One row per pixel\_external\_id x creative\_external\_id x hour | pixel\_external\_id, creative\_external\_id, hour, hour\_utc | UA reporting pipeline | Hourly attributed conversion aggregate. |
| raw\_attributed\_conversion\_data | Raw attributed conversion event grain | downstream IDs such as campaign\_id, line\_item\_id, creative\_id; conversion\_id | UA reporting pipeline | Lower-level attributed conversion records. |
| app\_events\_conversion\_data | One row per app\_tracker\_id x event\_name x hour | app\_tracker\_id, event\_name, hour, hour\_utc | UA reporting pipeline | Hourly app event conversion aggregate. |
| mobile\_app\_event\_\*\_day\_attribution | One row per attributed app conversion | conversion\_id, app\_tracker\_id, ad\_id | UA Postgres / attribution pipeline | Separate 7-day, 14-day, and 30-day attribution windows. |
| kochava\_conversion\_data | One row per enhanced\_pixel\_id x event\_name x hour | enhanced\_pixel\_id, event\_name, hour, hour\_utc | UA reporting pipeline | Hourly Kochava conversion aggregate. |
| kochava\_\*\_day\_attribution | One row per Kochava-attributed conversion | conversion\_id, enhanced\_pixel\_id, ad\_id | UA Postgres / attribution pipeline | Separate 7-day, 14-day, and 30-day attribution windows. |
| gold\_kochava\_\*\_day\_attribution | One row per Kochava-attributed conversion in query/reporting layer | conversion\_id, enhanced\_pixel\_id, ad\_id, adaccount\_id | Warehouse/query source | Query-only mappings for 7-day, 14-day, and 30-day attribution windows. |
| kochava | Raw Kochava conversion source | transaction\_id, pixel\_id, partition fields | Warehouse/query source | Query-only mapping for raw Kochava conversion events. |
| raw\_performance\_data\_kochava | Kochava-specific raw performance join data | auction\_id, creative\_id, timestamps | UA reporting pipeline | Contains a focused set of fields for Kochava attribution joins. |

## Common Field Conventions

Most UA Postgres models all inherit common metadata.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal identifier | UUID | UA Postgres | Primary key for most Postgres entities. Prefer this for internal Postgres joins. |
| created\_at | Row creation timestamp | Timestamp without timezone | UA Postgres | Server default. |
| updated\_at | Last update timestamp | Timestamp without timezone | UA Postgres | Server update timestamp. |
| created\_by | User that created the row | UUID | UA Postgres | References user.id when set. |
| updated\_by | User that last updated the row | UUID | UA Postgres | References user.id when set. |
| created\_by\_app | Application that created the ad object | UUID | UA Postgres | Present on ad objects. |
| updated\_by\_app | Application that updated the ad object | UUID | UA Postgres | Present on ad objects. |
| status | UA internal lifecycle status | String or integer depending on table | UA Postgres | Do not assume every table uses the same enum type (**all core objects use string**). Campaign/adset/ad status values are strings. |
| external\_id | Downstream system identifier | String | UA Postgres / external ad server | Primary bridge from UA records to BW objects. |
| external\_status | Downstream system status | String | UA Postgres / external ad server | Separate from UA internal status. |
| archived\_at | Archive timestamp | Timestamp without timezone | UA Postgres | Present on campaign, adset, and ad. |
| archived\_from\_status | Status before archive | String | UA Postgres | Useful for audits, not active eligibility. |

## Business Definitions

| Object | Definition | Relevance |
| --- | --- | --- |
| Organization | UA tenant / business entity that owns ad accounts. | Provides account hierarchy, timezone, inventory enablement, and financial context. |
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
| Kochava data | Kochava conversion and attribution data. | Connects enhanced pixels, conversion events, attributed impressions, ads, and attribution windows. |
| Custom segment | Audience segment available to an ad account or campaign. | Can affect targeting and model features when referenced by ad set targeting JSON. |
| Performance report tables | Hourly aggregate of delivery and outcomes. | Useful for pacing, spend, CTR/CVR, and model training labels. |
| Attributed conversion data | Conversion events attributed back to ads, creatives, campaigns, line items, pixels, or app trackers. | Useful for connecting outcomes to delivery and measurement configuration. |
| Raw logs / win logs | Lower-level auction and win-event data. | Useful for bid shading, clearing price, supply quality, contextual features, and ML training. |

## Entity Data Dictionary

### Organization: organization

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal organization UUID | UUID | UA Postgres | Parent of ad accounts. |
| name | Organization display name | String | UA Postgres | Descriptive; do not use as durable key. |
| organization\_type | Organization category | String enum | UA Postgres | Defaults to regular. |
| network\_id | Required/associated network | UUID | UA Postgres | Nullable. References network.id. |
| timezone | Organization timezone | String | UA Postgres | Required. Ad account timezone is more directly relevant for campaign/adset date normalization. |
| inventory\_enabled | Whether inventory-specific behavior is enabled | Boolean | UA Postgres | Relevant for ad set inventory targeting rules. |
| credit\_limit | Organization credit limit | Float | UA Postgres | Organization-level financial context. |
| status | Organization lifecycle status | String enum | UA Postgres | Pending/active/etc. |

### Ad Account: adaccount

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal ad account UUID | UUID | UA Postgres | Parent of campaigns and creatives. |
| organization\_id | Owning organization | UUID | UA Postgres | References organization.id. |
| account\_id | Linked internal account | UUID | UA Postgres | Nullable. |
| name | Ad account name | String | UA Postgres | Descriptive; do not use as durable key. |
| external\_id | External account identifier | String | UA Postgres / external platform | Useful for downstream mapping. |
| domain | Advertiser/account domain | String | UA Postgres |  |
| category | Account category | String | UA Postgres | Political rules depend on this in current flows. |
| default\_continent | Default geography group | String | UA Postgres |  |
| default\_currency | Default currency | String | UA Postgres | Campaign creation uses this as campaign currency. |
| timezone | Ad account timezone | String | UA Postgres | Important: campaign/adset user-entered dates are normalized through this timezone. |
| attributes | Additional account attributes | JSON | UA Postgres |  |
| threshold\_amount | Spend threshold | Integer | UA Postgres | Financial/account-control context. |
| legacy\_pixel\_enabled | Whether legacy pixels are enabled | Boolean | UA Postgres | Pixel integration behavior can vary. |
| status | UA account status | String enum | UA Postgres | Defaults to paused. |
| external\_status | External account status | String | UA Postgres / external platform | Nullable. |

### Campaign: campaign

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal campaign UUID | UUID | UA Postgres | Parent of ad sets. |
| adaccount\_id | Owning ad account | UUID | UA Postgres | References adaccount.id. |
| external\_id | Downstream campaign identifier | String | UA Postgres / external platform | Bridge to external systems and some logs. |
| name | Campaign name | String | UA Postgres | Descriptive; do not use as durable key. |
| currency | Campaign currency | String | UA Postgres | Usually from adaccount.default\_currency. |
| start\_date | Campaign start in account/user timezone representation | Timestamp | UA Postgres | Required. Use UTC fields for cross-system processing. |
| end\_date | Campaign end in account/user timezone representation | Timestamp | UA Postgres | Nullable. |
| start\_date\_utc | Campaign start in UTC | Timestamp with timezone | UA Postgres | Preferred for cross-system date comparisons and pacing windows. |
| end\_date\_utc | Campaign end in UTC | Timestamp with timezone | UA Postgres | Nullable. |
| min\_bid | Minimum bid | Integer | UA Postgres | Nullable. Not used. |
| max\_bid | Maximum bid | Integer | UA Postgres | Nullable. Not used. |
| continents | Continent targeting / defaults | String | UA Postgres | Nullable. |
| budget\_type | Campaign budget interpretation | String enum | UA Postgres | Current supported value includes spend including vendor fees. |
| objective\_type | Campaign objective | String enum | UA Postgres | Known values include web\_conversions, awareness, app\_promotion. |
| lifetime\_budget | Campaign lifetime budget | Float | UA Postgres | Max budget to spend of the campaigns lifetime |
| daily\_budget | Campaign daily budget | Float | UA Postgres | Nullable. Cannot exceed lifetime budget in creation flow. |
| frequency\_cap\_duration | Frequency cap window duration (seconds) | Integer | UA Postgres | Must be paired with impressions when set. |
| frequency\_cap\_impressions | Impression count in cap window | Integer | UA Postgres | Must be paired with duration when set. |
| frequency\_cap | Structured frequency cap config | JSON | UA Postgres | Nullable. Use as authoritative when populated. |
| network\_id | Scoped network | UUID | UA Postgres | Nullable. References network.id. Required for scoped campaigns, disallowed for performance campaign path. |
| campaign\_type | Campaign behavior type | String enum | UA Postgres | Known values include standard, legacy, performance, scoped. |
| status | UA campaign lifecycle status | String enum | UA Postgres | Known values include active, draft, error, pending, paused, deleted, completed, archived. |
| external\_status | Downstream campaign status | String enum | UA Postgres / external platform | Known values include active, inactive. |
| advocacy | Political advocacy classification | String enum | UA Postgres | Required for political ad accounts; disallowed for non-political accounts. |
| jurisdiction\_scope | Political jurisdiction scope | String enum | UA Postgres | Required for political ad accounts; disallowed for non-political accounts. |

### Ad Set: adset

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal ad set UUID | UUID | UA Postgres | Parent of ads and targeting. |
| campaign\_id | Parent campaign | UUID | UA Postgres | References campaign.id. |
| external\_id | Downstream ad set / line item identifier | String | UA Postgres / external platform | Important bridge to log data. |
| name | Ad set name | String | UA Postgres | Descriptive; do not use as durable key. |
| adset\_type | Ad set creative/media type | String enum | UA Postgres | Current enum includes video. |
| budget\_type | Ad set budget interpretation | String enum | UA Postgres | Current supported value includes spend including vendor fees. |
| lifetime\_budget | Ad set lifetime budget | Float | UA Postgres | Max budget to spend over the ad sets lifetime |
| daily\_budget | Ad set daily budget | Float | UA Postgres | Nullable. Cannot exceed lifetime budget in creation flow. |
| status | UA ad set lifecycle status | String enum | UA Postgres | Known values include active, draft, error, pending, paused, deleted, completed, archived. |
| external\_status | Downstream line item status | String enum | UA Postgres / external platform | Known values include active, inactive. |
| guaranteed | Guaranteed delivery flag/value | Integer | UA Postgres | Nullable. Not used. |
| start\_date | Ad set start in account/user timezone representation | Timestamp | UA Postgres | Required. |
| end\_date | Ad set end in account/user timezone representation | Timestamp | UA Postgres | Nullable. |
| start\_date\_utc | Ad set start in UTC | Timestamp with timezone | UA Postgres | Preferred for cross-system date comparisons and pacing. |
| end\_date\_utc | Ad set end in UTC | Timestamp with timezone | UA Postgres | Nullable. |
| user\_timezone | User/account timezone attached to ad set | String | UA Postgres | Nullable. |
| enable\_skad\_tracking | SKAd tracking flag/value | Integer | UA Postgres | Nullable. Relevant to app promotion / iOS measurement. |
| currency | Ad set currency | String | UA Postgres | Nullable. |
| bid | Ad set bid | Float | UA Postgres | CPM bid amount |
| fee | Ad set fee | Float | UA Postgres | Defaults to 0. |
| bidding | Structured bidding config | JSON | UA Postgres |  |
| bid\_shading | Whether bid shading is enabled | Boolean | UA Postgres | Required. |
| bid\_shading\_control | Bid shading control mode | String | UA Postgres | Nullable. |
| frequency\_cap\_duration | Frequency cap window duration | Integer | UA Postgres | Must be paired with impressions when set. |
| frequency\_cap\_impressions | Impression count in cap window | Integer | UA Postgres | Must be paired with duration when set. |
| frequency\_cap | Structured frequency cap config | JSON | UA Postgres | Nullable. |
| segment\_extension | Segment extension config | JSON | UA Postgres | Nullable. Related constants include person/household modes. |
| regulated\_content | Whether content is regulated | String | UA Postgres | Hybrid property defaults missing value to unregulated. |
| app\_tracker\_id | App tracker dependency | UUID | UA Postgres | Required by app promotion campaign flow. |
| inventory | Inventory-specific setting | String | UA Postgres | Nullable. Requires inventory-enabled account and specific network behavior. |

### Targeting: target

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal targeting row UUID | UUID | UA Postgres | Usually one target per ad set. |
| adset\_id | Ad set being targeted | UUID | UA Postgres | References adset.id. |
| external\_id | Downstream targeting identifier | String | UA Postgres / external platform | Nullable. |
| target | Full targeting payload | JSON | UA Postgres | Required. Broad container for targeting details. |
| location | Geo/location targeting | JSON | UA Postgres | Nullable. |
| age | Age targeting | JSON | UA Postgres | Nullable. |
| gender | Gender targeting | JSON | UA Postgres | Nullable. |
| advanced\_demographic | Advanced demographic targeting | JSON | UA Postgres | Nullable. Political rules may restrict use. |
| device\_type | Device targeting | JSON | UA Postgres | Nullable. Not allowed on some networks such as UK flow. |
| segment | Audience segment targeting | JSON | UA Postgres | Nullable. May reference custom segments or external segments. |
| genre | Genre targeting | JSON | UA Postgres | Nullable. Limited to specific networks / automatic network behavior. |
| day\_part | Dayparting targeting | JSON | UA Postgres | Nullable. Current validation disallows overlapping or duplicate windows. |
| content\_language | Content language targeting | JSON | UA Postgres | Nullable. Current validation allows at most one included language. |

### Placement: placement and target\_placement

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| placement.id | UA internal placement UUID | UUID | UA Postgres | Referenced by target\_placement.placement\_id. |
| placement.name | Placement display name | String | UA Postgres | Descriptive. |
| placement.external\_id | Downstream placement ID(s) | String | UA Postgres / external platform | Can contain comma-separated IDs; model exposes split\_external\_ids. |
| placement.network\_id | Owning network | UUID | UA Postgres | References network.id. Must match campaign/adset network rules. |
| placement.status | Placement lifecycle status | String enum | UA Postgres | Defaults active. |
| placement.bid\_floor | Placement bid floor | Float | UA Postgres | Nullable. Useful supply-side pricing context if populated. |
| target\_placement.target\_id | Targeting row | UUID | UA Postgres | References target.id. |
| target\_placement.placement\_id | Placement row | UUID | UA Postgres | References placement.id. |

### Ad: ad

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal ad UUID | UUID | UA Postgres | Joins to hourly performance\_report\_pipeline\_merged.ad\_id. |
| adset\_id | Parent ad set | UUID | UA Postgres | References adset.id. |
| external\_id | Downstream ad identifier | String | UA Postgres / external platform | Bridge to external systems. |
| name | Ad name | String | UA Postgres | Descriptive. |
| url | Destination or creative URL | String | UA Postgres | Nullable. |
| thumbnail\_url | Thumbnail URL | String | UA Postgres | Nullable. |
| click\_url | Click-through URL | String | UA Postgres | Nullable. |
| ad\_type | Downstream ad type integer | Integer | UA Postgres | FreeWheel mapping: banner 0, video 1, native 2. |
| ad\_template\_type | Creative template ID | Integer | UA Postgres | Known values include VAST inline 3 and VAST inline dynamic 25. |
| status | UA ad lifecycle status | String enum | UA Postgres | Known values include active, pending, paused, rejected, archived. |
| external\_status | Downstream ad status | String enum | UA Postgres / external platform | Known values include not\_created, pending, active, inactive. |
| primary\_creative\_id | Primary creative | UUID | UA Postgres | References creative.id. Nullable. |
| secondary\_creative\_id | Secondary creative | UUID | UA Postgres | References creative.id. Nullable. |
| creative\_duration | Creative duration (seconds) | Integer | UA Postgres | Nullable |
| rotation\_weight | Ad rotation weight | Float | UA Postgres | Nullable. Must be between 0 and 1 when set. |
| clock\_number | Clock number / traffic identifier | String | UA Postgres | Nullable. |

### Creative: creative

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal creative UUID | UUID | UA Postgres | Referenced by ads. |
| external\_id | Downstream creative identifier | String | UA Postgres / external platform | Bridge to logs / ad server where applicable. |
| name | Creative name | String | UA Postgres | Nullable and descriptive. |
| url | Creative asset URL | String | UA Postgres | Nullable. |
| thumbnail\_url | Creative thumbnail URL | String | UA Postgres | Nullable. |
| adaccount\_id | Owning ad account | UUID | UA Postgres | References adaccount.id. |
| creative\_asset\_type\_id | Creative type lookup | UUID | UA Postgres | References creative\_asset\_type.id. |
| creative\_status\_id | Internal creative status lookup | UUID | UA Postgres | References creative\_internal\_status.id. |
| external\_creative\_status\_id | External creative status lookup | UUID | UA Postgres | References creative\_external\_status.id. |
| media\_id | Backing media object | UUID | UA Postgres | References media.id. |
| duration | Creative duration | Interval | UA Postgres | Nullable. |
| political\_details | Political creative metadata | JSON | UA Postgres | Nullable. |
| approval\_status | Political/compliance approval status | String enum | UA Postgres | Deliverable values are approved or not\_required. |
| jurisdiction\_scope | Political jurisdiction scope | String enum | UA Postgres | Nullable. |

Creative deliverability should consider both internal creative status and approval status. Current helper logic treats a creative as deliverable when creative\_status = active and approval\_status is either approved or not\_required.

### Media: media

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal media UUID | UUID | UA Postgres | Referenced by creative. |
| mime\_type | Asset MIME type | String | UA Postgres | Required. |
| key | Object storage key | String | UA Postgres / object storage | Required. |
| bucket | Object storage bucket | String | UA Postgres / object storage | Required. |
| status | Media lifecycle status | String enum | UA Postgres | Defaults pending. |
| adaccount\_id | Owning ad account | UUID | UA Postgres | Nullable. |
| application\_id | Associated application identifier | String | UA Postgres | Nullable. This is a string and should not be assumed to equal application.id. |

### Delivery Overrides: adset\_delivery\_override

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal override UUID | UUID | UA Postgres | Admin-managed row. |
| adset\_id | Ad set receiving overrides | UUID | UA Postgres | References adset.id; unique, so at most one override row per ad set. |
| publisher\_exclusion\_ids | Publisher IDs to exclude | JSON | UA Postgres admin data | Should be applied as targeting exclusions downstream. |
| included\_deal\_ids | Deal IDs explicitly included | JSON | UA Postgres admin data | Useful for PMP/deal-constrained delivery. |
| delivery\_modifier\_id | Downstream delivery modifier ID | Integer | UA Postgres admin data | If present, should take precedence over defaults. |
| bid\_modifier | Bid modifier config | JSON | UA Postgres admin data | Downstream bid modifier identifier and min + max bids |
| pacing\_type | Pacing override | String | UA Postgres admin data | Nullable |
| dynamic\_creative\_rotation | Whether dynamic creative rotation is enabled | Boolean | UA Postgres admin data | Defaults false. |
| creative\_rotation\_weights | Creative/ad rotation weight overrides | JSON | UA Postgres admin data | Nullable. |

Override precedence rule: when an override field is present, downstream sync logic should treat it as higher priority than UA-derived defaults.

### Enhanced Pixel and Conversion Measurement

#### Enhanced Pixel: enhanced\_pixel

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal enhanced pixel UUID | UUID | UA Postgres | Referenced by ad set links and custom segments. |
| adaccount\_id | Owning ad account | UUID | UA Postgres | References adaccount.id. |
| name | Pixel name | String | UA Postgres | Required. |
| status | Pixel status | String enum | UA Postgres | Required. |
| installation\_type | Pixel installation type | String | UA Postgres | Required. |
| activity\_key | Activity/event key | String | UA Postgres | Nullable. |
| event\_source\_id | Event source | UUID | UA Postgres | References event\_sources.id. |

#### Ad Set Link: enhanced\_pixel\_adset\_link

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| adset\_id | Ad set using the enhanced pixel | UUID | UA Postgres | References adset.id. |
| enhanced\_pixel\_id | Enhanced pixel used for measurement | UUID | UA Postgres | References enhanced\_pixel.id. |
| status | Link status | String enum | UA Postgres | Defaults active. |

#### Conversion Aggregates: conversion\_data and pixel\_events

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| pixel\_id | UA internal pixel UUID | UUID | UA reporting pipeline | Present on conversion\_data; nullable. |
| pixel\_external\_id | External pixel identifier | String | UA reporting pipeline | Join key for hourly conversion aggregates. |
| conversions | Conversion count | Integer | UA reporting pipeline | Nullable. |
| count | Pixel event count | Integer | UA reporting pipeline | Present on pixel\_events. |
| hour | Local/reporting hour | Timestamp | UA reporting pipeline | Used with pixel ID for uniqueness. |
| hour\_utc | UTC hour | Timestamp with timezone | UA reporting pipeline | Preferred for time-series modeling. |

#### Legacy Attributed Conversion Aggregates: attributed\_conversion\_data 

One row represents one pixel\_external\_id x creative\_external\_id x hour. The table has a unique constraint on hour, pixel\_external\_id, and creative\_external\_id.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| pixel\_id | UA internal pixel UUID | UUID | UA reporting pipeline | Nullable. |
| pixel\_external\_id | External pixel identifier | String | UA reporting pipeline | Used to connect attribution back to pixel-based measurement. |
| creative\_id | UA internal creative UUID | UUID | UA reporting pipeline | Nullable. |
| creative\_external\_id | External creative identifier | String | UA reporting pipeline | Used with pixel and hour for uniqueness. |
| conversions | Attributed conversion count | Integer | UA reporting pipeline | Nullable. |
| hour | Local/reporting hour | Timestamp | UA reporting pipeline | Used in the unique aggregate key. |
| hour\_utc | UTC reporting hour | Timestamp with timezone | UA reporting pipeline | Preferred for time-series joins. |

#### Legacy Raw Attributed Conversion Data: raw\_attributed\_conversion\_data

Legacy raw attributed conversion data is lower-level than hourly aggregates and includes conversion identifiers, attribution method, downstream delivery identifiers, geo context, app bundle, and conversion value fields.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| conversion\_id | Conversion event identifier | String | UA attribution pipeline | Useful for deduping and traceability. |
| conversion\_ord / conversion\_order | Conversion order fields | String | UA attribution pipeline |  |
| conversion\_value | Parsed conversion value | Float | UA attribution pipeline | Nullable. |
| conversion\_value\_raw | Raw conversion value | String | UA attribution pipeline | Nullable. Useful for debugging parsing issues. |
| conversion\_type | Conversion type | String | UA attribution pipeline | Nullable. |
| event\_id | Event identifier | Integer | UA attribution pipeline | Nullable. |
| attribution\_method | Method used to attribute the conversion | String | UA attribution pipeline | Nullable. |
| campaign\_id | Downstream campaign identifier | Integer | UA attribution pipeline | Not a UA UUID; map through campaign.external\_id when appropriate. |
| line\_item\_id | Downstream line item/ad set identifier | Integer | UA attribution pipeline | Not a UA UUID; map through adset.external\_id when appropriate. |
| creative\_id | Downstream creative identifier | Integer | UA attribution pipeline | Not a UA UUID; map through external creative identifiers where available. |
| account\_id | Downstream account identifier | Integer | UA attribution pipeline | Not a UA UUID. |
| advertiser\_id | Downstream advertiser identifier | Integer | UA attribution pipeline | Not a UA UUID. |
| auction\_id | Auction identifier | String | UA attribution pipeline | Useful for connecting conversion attribution to delivery events where available. |
| bid\_time | Bid timestamp | Timestamp | UA attribution pipeline | Nullable. |
| bid\_time\_utc | UTC bid timestamp | Timestamp | UA attribution pipeline | Preferred for cross-system joins. |
| rx\_timestamp | Receive timestamp | Timestamp | UA attribution pipeline | Nullable. |
| rx\_timestamp\_utc | UTC receive timestamp | Timestamp | UA attribution pipeline | Preferred for cross-system joins. |
| create\_time\_utc | UTC conversion creation timestamp | Timestamp | UA attribution pipeline | Nullable. |
| app\_bundle | App bundle associated with the conversion | String | UA attribution pipeline | Supply/app context; not necessarily a UA application UUID. |
| postback\_url | Postback URL | String | UA attribution pipeline | Nullable. Treat as sensitive integration data. |
| geo\_city, geo\_country, geo\_region, geo\_zip, geo\_metro | Geo fields associated with the conversion | String | UA attribution pipeline | Nullable. |
| test\_group\_id, experiment\_user\_index, test\_plan\_id, experiment\_id\_type | Experiment metadata | Integer/String | UA attribution pipeline | Nullable. |

### App Tracker and App Event Measurement

#### App Tracker: app\_tracker

App trackers are used for app promotion measurement. An ad set can reference an app tracker through adset.app\_tracker\_id.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal app tracker UUID | UUID | UA Postgres | Referenced by adset.app\_tracker\_id, app event aggregates, and mobile app attribution tables. |
| adaccount\_id | Owning ad account | UUID | UA Postgres | References adaccount.id. |
| name | Tracker name | String | UA Postgres | Required. |
| mmp | Mobile measurement partner | String | UA Postgres | Required. |
| ios\_app\_store\_id | iOS App Store identifier | String | UA Postgres | Nullable. |
| android\_package\_name | Android package name | String | UA Postgres | Nullable. |
| app\_name | App display name | String | UA Postgres | Required; descriptive, not a durable join key. |
| status | App tracker status | String | UA Postgres | Required. |
| event\_source\_id | Event source | UUID | UA Postgres | References event\_sources.id. |

#### App Tracker Pixel: app\_tracker\_pixel

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal app tracker pixel UUID | UUID | UA Postgres | Primary key. |
| app\_tracker\_id | Parent app tracker | UUID | UA Postgres | References app\_tracker.id. |
| impression\_tracking\_url | Platform-specific impression tracking URL | String | UA Postgres | Required. Treat as integration-sensitive. |
| platform | Platform for the tracking URL | String | UA Postgres | Required. |
| status | Pixel row status | String | UA Postgres | Required. |

#### App Event Conversion Aggregates: app\_events\_conversion\_data

One row represents one app\_tracker\_id x event\_name x hour. The table has a unique constraint on hour, app\_tracker\_id, and event\_name.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| app\_tracker\_id | App tracker associated with the event | UUID | UA reporting pipeline | References app\_tracker.id. |
| event\_name | App event name | String | UA reporting pipeline | Required. |
| conversions | Conversion/event count | Integer | UA reporting pipeline | Nullable. |
| hour | Local/reporting hour | Timestamp | UA reporting pipeline | Nullable. |
| hour\_utc | UTC reporting hour | Timestamp with timezone | UA reporting pipeline | Nullable; preferred when populated. |

#### Mobile App Event Attribution: mobile\_app\_event\_7\_day\_attribution, mobile\_app\_event\_14\_day\_attribution, mobile\_app\_event\_30\_day\_attribution

These tables share the same structure and differ by attribution window. Each table has a unique constraint on conversion\_id.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| conversion\_id | Conversion identifier | String | UA attribution pipeline | Unique within each attribution window table. |
| event\_name | App event name | String | UA attribution pipeline | Required. |
| event\_timestamp\_utc | UTC timestamp of the app event | Timestamp with timezone | UA attribution pipeline | Required. |
| app\_tracker\_id | App tracker associated with the event | UUID | UA attribution pipeline | Nullable. References app\_tracker.id. |
| ad\_id | UA internal ad UUID | UUID | UA attribution pipeline | Required. References ad.id. |
| app\_id | App identifier from the event/source system | String | UA attribution pipeline | Required. Do not assume this is application.id. |
| device\_id | Device identifier | String | UA attribution pipeline | Nullable. Treat as privacy-sensitive. |
| device\_platform | Device platform | String | UA attribution pipeline | Nullable. |
| impression\_id | Impression identifier | String | UA attribution pipeline | Required. |
| ip\_address | IP address | String | UA attribution pipeline | Nullable. Treat as privacy-sensitive. |
| bid\_hour\_utc | UTC bid hour | Timestamp | UA attribution pipeline | Required. |
| bid\_time\_utc | UTC bid timestamp | Timestamp | UA attribution pipeline | Nullable. |
| revenue | Revenue associated with the event | Float | UA attribution pipeline | Nullable. |
| hhid | Household identifier | String | UA attribution pipeline | Nullable. Treat as privacy-sensitive. |
| ingested\_at | Ingestion timestamp | Timestamp | UA attribution pipeline | Required. |

### Kochava Conversion and Attribution Data

Kochava data appears in both UA Postgres-style models and query/reporting-layer models. The Postgres attribution tables are keyed by enhanced\_pixel\_id, conversion\_id, and optionally ad\_id. The reporting/query models expose raw Kochava events and gold attribution tables for 7-day, 14-day, and 30-day windows.

#### Kochava Raw Event Data: kochava\_data

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| transaction\_id | Kochava transaction identifier | Text | UA Postgres / Kochava ingest | Nullable in the model. |
| advertiser\_name | Advertiser name from Kochava data | Text | Kochava ingest | Descriptive. |
| event\_timestamp | Event timestamp | Timestamp | Kochava ingest | Nullable. |
| event\_timestamp\_hour | Event timestamp truncated/aggregated to hour | Timestamp | Kochava ingest | Nullable. |
| ip\_address | IP address associated with the event | Text | Kochava ingest | Nullable. Treat as privacy-sensitive. |
| event\_name | Kochava event name | Text | Kochava ingest | Nullable. |
| user\_id | User identifier | Text | Kochava ingest | Nullable. Treat as privacy-sensitive. |
| page\_url | Page URL associated with the event | Text | Kochava ingest | Nullable. |
| user\_email | User email | Text | Kochava ingest | Nullable. Treat as sensitive personal data. |
| product\_name | Product name | Text | Kochava ingest | Nullable. |
| referrer\_url | Referrer URL | Text | Kochava ingest | Nullable. |
| product\_id | Product identifier | Text | Kochava ingest | Nullable. |
| item\_quantity | Item quantity | Text | Kochava ingest | Nullable. |
| total\_price | Total price | Float | Kochava ingest | Nullable. |
| currency\_code | Currency code | Text | Kochava ingest | Nullable. |
| order\_id | Order identifier | Text | Kochava ingest | Nullable. |

#### Kochava Conversion Aggregate: kochava\_conversion\_data

One row represents one enhanced\_pixel\_id x event\_name x hour. The table has a unique constraint on hour, enhanced\_pixel\_id, and event\_name.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| enhanced\_pixel\_id | Enhanced pixel associated with the Kochava event | UUID | UA reporting pipeline | References enhanced\_pixel.id. |
| event\_name | Kochava event name | String | UA reporting pipeline | Required. |
| conversions | Conversion/event count | Integer | UA reporting pipeline | Nullable. |
| hour | Local/reporting hour | Timestamp | UA reporting pipeline | Nullable. |
| hour\_utc | UTC reporting hour | Timestamp with timezone | UA reporting pipeline | Nullable; preferred when populated. |

#### Kochava Attribution: kochava\_seven\_day\_attribution, kochava\_fourteen\_day\_attribution, kochava\_thirty\_day\_attribution

These tables share the same structure and differ by attribution window. Each table has a unique constraint on conversion\_id.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| conversion\_id | Kochava conversion identifier | String | UA attribution pipeline | Unique within each attribution window table. |
| enhanced\_pixel\_id | Enhanced pixel associated with the conversion | UUID | UA attribution pipeline | Required. References enhanced\_pixel.id. |
| event\_name | Kochava event name | String | UA attribution pipeline | Required, retained in case events are deleted elsewhere. |
| ad\_id | UA internal ad UUID | UUID | UA attribution pipeline | Nullable. References ad.id. |
| impression\_id | Beeswax impression identifier | String | UA attribution pipeline | Required. |
| user\_id | User identifier for the conversion | String | UA attribution pipeline | Required in the model. Treat as privacy-sensitive. |
| event\_timestamp | Event timestamp | Timestamp | UA attribution pipeline | Required. |
| event\_timestamp\_utc | UTC event timestamp | Timestamp with timezone | UA attribution pipeline | Required; preferred for cross-system joins. |
| bid\_hour | Bid hour | Timestamp | UA attribution pipeline | Required. |
| bid\_hour\_utc | UTC bid hour | Timestamp | UA attribution pipeline | Required. |
| bid\_time\_utc | UTC bid timestamp | Timestamp | UA attribution pipeline | Nullable. |
| order\_id | Order identifier | String | UA attribution pipeline | Nullable. |
| ga\_client\_id | Google Analytics client identifier | String | UA attribution pipeline | Nullable. Treat as sensitive identifier data. |
| price | Conversion price/value | Float | UA attribution pipeline | Nullable. |
| hhid | FreeWheel household identifier | String | UA attribution pipeline | Nullable. Treat as privacy-sensitive. |
| url | Event URL | String | UA attribution pipeline | Nullable. |
| referral\_from | Referral source URL/string | String | UA attribution pipeline | Nullable. |

#### Gold Kochava Attribution: gold\_kochava\_seven\_day\_attribution, gold\_kochava\_fourteen\_day\_attribution, gold\_kochava\_thirty\_day\_attribution

The gold Kochava attribution models are query-only mappings with similar attribution fields plus reporting-layer metadata.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| conversion\_id | Kochava conversion identifier | String | Warehouse/query source | Primary key for query mapping. |
| enhanced\_pixel\_id | Enhanced pixel identifier | String | Warehouse/query source | Stored as string in the query model. |
| event\_name | Kochava event name | String | Warehouse/query source | Nullable in query mapping. |
| ad\_id | Ad identifier | String | Warehouse/query source | Stored as string in the query model. |
| impression\_id | Impression identifier | String | Warehouse/query source | Nullable in query mapping. |
| user\_id | User identifier | String | Warehouse/query source | Treat as privacy-sensitive. |
| event\_timestamp, event\_timestamp\_utc | Event timestamps | Timestamp | Warehouse/query source | UTC field preferred for time-series joins. |
| bid\_hour, bid\_hour\_utc, bid\_time\_utc | Bid timestamps | Timestamp | Warehouse/query source | UTC fields preferred. |
| price | Conversion price/value | Float | Warehouse/query source | Nullable. |
| order\_id | Order identifier | String | Warehouse/query source | Nullable. |
| ga\_client\_id | Google Analytics client identifier | String | Warehouse/query source | Nullable. Treat as sensitive identifier data. |
| hhid | Household identifier | String | Warehouse/query source | Nullable. Treat as privacy-sensitive. |
| ingested\_at | Ingestion timestamp | Timestamp | Warehouse/query source | Useful for freshness/debugging. |
| load\_id | Pipeline load identifier | String | Warehouse/query source | Useful for lineage/debugging. |
| adaccount\_id | Ad account identifier | String | Warehouse/query source | Stored as string in the query model. |

#### Raw Kochava Conversion Source: kochava

The kochava query model represents raw Kochava conversion events and includes partition columns.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| transaction\_id | Kochava transaction identifier | String | Warehouse/query source | Primary key for query mapping. |
| event\_name | Kochava event name | String | Warehouse/query source | Nullable. |
| event\_product | Product/event product payload | String | Warehouse/query source | Nullable. |
| event\_timestamp | Event timestamp | Timestamp | Warehouse/query source | Nullable. |
| event\_ip | Event IP address | String | Warehouse/query source | Treat as privacy-sensitive. |
| event\_user\_agent | Event user agent | String | Warehouse/query source | Nullable. |
| event\_metadata | Raw event metadata | String | Warehouse/query source |  |
| pixel\_id | Pixel identifier partition/context field | String | Warehouse/query source | Not necessarily a UA UUID. |
| yyyy, mm, dd, hh | Partition columns | String | Warehouse/query source | Used for partition pruning. |

#### Kochava-Specific Raw Performance Data: raw\_performance\_data\_kochava

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| auction\_id | Auction identifier | Text | UA reporting pipeline | Useful for joining attributed events to delivery context where available. |
| auction\_adgroup\_id | Auction ad group identifier | Text | UA reporting pipeline | Nullable. |
| bid\_hour | Bid hour | Timestamp | UA reporting pipeline | Nullable. |
| bid\_time | Bid timestamp | Timestamp | UA reporting pipeline | Nullable. |
| bid\_time\_utc | UTC bid timestamp | Timestamp | UA reporting pipeline | Preferred for cross-system joins. |
| creative\_id | Downstream creative identifier | Integer | UA reporting pipeline | Not a UA UUID. |
| creative\_alt\_id | Alternative creative identifier | Text | UA reporting pipeline | Nullable. |
| ip\_address | IP address from request context | Text | UA reporting pipeline | Treat as privacy-sensitive. |
| ipv6\_address | IPv6 address from request context | Text | UA reporting pipeline | Treat as privacy-sensitive. |
| impression\_ip\_address | Impression IP address | Text | UA reporting pipeline | Treat as privacy-sensitive. |
| rx\_timestamp\_utc | UTC receive timestamp | Timestamp | UA reporting pipeline | Nullable. |

### Custom Segments: custom\_segments

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| id | UA internal segment UUID | UUID | UA Postgres | May be referenced in targeting JSON. |
| segment\_key | Internal segment key | String | UA Postgres | Required. |
| external\_id | Downstream segment identifier | String | UA Postgres / external platform | Use for downstream matching where required. |
| adaccount\_id | Owning ad account | UUID | UA Postgres | References adaccount.id. |
| name | Segment name | String | UA Postgres | Descriptive. |
| active | Whether segment is active | Boolean | UA Postgres | Required. |
| pixel\_id | Legacy pixel source | UUID | UA Postgres | Nullable. |
| enhanced\_pixel\_id | Enhanced pixel source | UUID | UA Postgres | Nullable. |
| retention\_period | Segment retention window (days) | Integer | UA Postgres | Nullable |
| event\_type | Segment event type | String | UA Postgres | Nullable. |
| segment\_type | Segment type | String | UA Postgres | Required. |
| size | Segment size | Integer | UA Postgres / external platform | Nullable. May lag actual population. |
| segment\_source | Segment source | String | UA Postgres | Examples in code comments include customer\_list, ad\_viewers, klaviyo. |
| ad\_viewer\_source | Scope for ad-viewer segment | String | UA Postgres | Examples include ad\_account, campaign. |
| campaign\_id | Campaign source for campaign-scoped ad-viewer segments | UUID | UA Postgres | Nullable. References campaign.id. |

## Reporting and Log Data Dictionary

### Hourly Performance Aggregate: performance\_report\_pipeline\_merged

One row represents one ad\_id x hour. The model has a unique constraint on hour and ad\_id.

| Field | Definition | Type | Source | Notes / Rules |
| --- | --- | --- | --- | --- |
| ad\_id | UA internal ad UUID | UUID | UA reporting pipeline | Joins to ad.id. |
| ad\_external\_id | Downstream ad ID | String | UA reporting pipeline | Bridge to downstream systems. |
| hour | Reporting hour | Timestamp | UA reporting pipeline | Local/reporting timezone representation. |
| hour\_utc | UTC reporting hour | Timestamp with timezone | UA reporting pipeline | Preferred for modeling and joins across systems. |
| impressions | Served impression count | Integer | UA reporting pipeline | Nullable. |
| clicks | Click count | Integer | UA reporting pipeline | Nullable. |
| conversions | Conversion count | Integer | UA reporting pipeline | Nullable. |
| spend | Total spend | Float | UA reporting pipeline | Gross spend |
| media\_spend | Media cost component | Float | UA reporting pipeline | Useful for cost analysis. |
| vendor\_fee\_spend | Vendor fee spend component | Float | UA reporting pipeline | Useful for gross/net reconciliation. |
| reach | Estimated unique reach | Integer | UA reporting pipeline | Nullable. |
| frequency | Average frequency | Float | UA reporting pipeline | Nullable. |
| ctr | Click-through rate | Float | UA reporting pipeline | Derived metric. |
| cpc | Cost per click | Float | UA reporting pipeline | Derived metric. |
| cpm | Cost per mille | Float | UA reporting pipeline | Derived metric. |
| cpa | Cost per acquisition/conversion | Float | UA reporting pipeline | Derived metric. |
| conversion\_rate | Conversion rate | Float | UA reporting pipeline | Derived metric. |
| video\_plays | Video starts/plays | Integer | UA reporting pipeline | Nullable. |
| video\_completes | Video completions | Integer | UA reporting pipeline | Nullable. |
| q1, q2, q3 | Video quartile counts | Integer | UA reporting pipeline | q2 corresponds to midpoint. |
| vcr | Video completion rate | Float | UA reporting pipeline | Derived metric. |
| cpcv | Cost per completed view | Float | UA reporting pipeline | Derived metric. |

### Raw Performance / Win Logs: raw\_performance\_data and win\_logs

Raw logs are broader than the Postgres campaign hierarchy. They include downstream ad-server IDs, auction context, bid prices, inventory metadata, geo/device fields, cost fields, conversion fields, and model metadata.
UA stores raw Beeswax delivery/win-log data and raw conversion data in S3. The models in this guide describe the fields UA exposes or queries from those datasets, but the raw storage layout, ingestion flow, and pipeline transformations are covered in the separate data and pipeline documentation.
For the upstream Beeswax batch log schemas, see [Data Schema](https://github.com/BeeswaxIO/beeswax-api/tree/master/beeswax/logs/batch/schemas).
Important caveat: in raw logs, fields such as campaign\_id, line\_item\_id, creative\_id, and account\_id are integers and represent downstream platform IDs, not UA internal UUIDs.

| Field group | Example fields | Meaning | Relevant use |
| --- | --- | --- | --- |
| Downstream IDs | account\_id, campaign\_id, line\_item\_id, creative\_id, advertiser\_id, flight\_id | External ad-server identifiers | Join to UA config through the corresponding external\_id field using the documented downstream ID mapping. |
| Auction IDs | auction\_id, exchange\_auction\_id, exchange\_imp\_id, request\_id | Auction / impression request identity | Deduping, traceability, request-level modeling. |
| Time | bid\_time, bid\_time\_utc, bid\_hour, rx\_timestamp\_utc, bid\_time\_epoch\_in\_usecs | Bid and receive timestamps | Time-window features, pacing, recency, hourly aggregation. |
| Bid prices | bid\_price\_micros\_usd, bid\_price\_micros, pre\_reduction\_bid\_price\_micros\_usd, bid\_floor\_micros, bid\_floor\_currency | Bid and floor prices, often in micros | Bid landscape and price-response modeling. Convert micros before financial reporting. |
| Bid shading / modifiers | bid\_shade, bid\_shade\_reduction\_micros, bid\_modifier\_id, bid\_modifier\_multipliers\_product | Bid-shading and modifier outcomes | Model diagnostics and override feedback. |
| Models / agents | bidding\_strategy\_id, model\_id, delivery\_model\_id, bid\_model\_id, bid\_agent\_id, params fields | Downstream/model metadata | Feature attribution, A/B analysis, and lineage. |
| Costs and fees | clearing\_price\_micros\_usd, win\_cost\_micros\_usd, media\_spend\_micros\_usd, vendor\_fee\_micros\_usd, total\_vendor\_fees\_micros\_usd | Auction clearing and spend components | Pacing, cost prediction, margin/gross-net reconciliation. |
| Revenue | campaign\_revenue\_amount\_micros, line\_item\_revenue\_amount\_micros, revenue\_amount\_micros | Revenue configured downstream | ROAS / objective modeling if applicable. |
| Performance | clicks, conversions, conversion\_value, ip\_conversions, video/audio metrics | Outcome events attached to logs | Labels and KPI calculations. |
| App / site | app\_id, app\_bundle, app\_name, site\_id, site\_name, domain, page\_url | Supply context | Contextual features and supply joins. |
| Placement / inventory | placement, placement\_type, inventory\_source, inventory\_source\_relationship, deal\_id | Supply placement and deal context | Placement, deal, and supply performance analysis. |
| Geo | geo\_country, geo\_region, geo\_city, geo\_zip, geo\_lat, geo\_lon, geo\_type, geo\_metro | Location context | Geo targeting validation and model features. |
| Device/platform | platform\_os, platform\_browser, platform\_device\_type, platform\_device\_make, platform\_device\_model, platform\_carrier, platform\_device\_ifa, platform\_device\_idfa | User/device context | Device performance modeling; handle privacy requirements. |
| Content | content\_title, content\_genre, content\_language, content\_rating, content\_network\_name, content\_channel\_name, content\_keywords | Contextual content metadata | Contextual targeting and ML features. |
| Segments | segment\_id, targeted\_segments, matched\_user\_groups, targeted\_lat\_long\_lists | Audience/segment match context | Segment performance and lookback features. |
| Privacy | is\_gdpr, is\_gdpr\_consented, gdpr\_consent\_string, us\_privacy, dnt, lmt | Consent/privacy signals | Required for privacy-aware feature use and retention rules. |

## Relationship and Join Rules

### Configuration joins in Postgres

Use UUID primary keys for configuration data:

```sql
select
  org.id as organization_id,
  aa.id as adaccount_id,
  c.id as campaign_id,
  aset.id as adset_id,
  ad.id as ad_id,
  cr.id as creative_id
from organization org
join adaccount aa on aa.organization_id = org.id
join campaign c on c.adaccount_id = aa.id
join adset aset on aset.campaign_id = c.id
join ad ad on ad.adset_id = aset.id
left join creative cr on cr.id = ad.primary_creative_id;
```

### Targeting and placement joins

```sql
select
  aset.id as adset_id,
  t.id as target_id,
  p.id as placement_id,
  p.external_id as placement_external_id,
  p.bid_floor
from adset aset
join target t on t.adset_id = aset.id
left join target_placement tp on tp.target_id = t.id
left join placement p on p.id = tp.placement_id;
```

### Ad set to enhanced pixel joins

```sql
select
  aset.id as adset_id,
  ep.id as enhanced_pixel_id,
  ep.name as enhanced_pixel_name,
  ep.status as enhanced_pixel_status
from adset aset
join enhanced_pixel_adset_link link on link.adset_id = aset.id
join enhanced_pixel ep on ep.id = link.enhanced_pixel_id
where link.status = 'active';
```

### Ad set to app tracker joins

```sql
select
  aset.id as adset_id,
  tracker.id as app_tracker_id,
  tracker.name as app_tracker_name,
  tracker.mmp,
  tracker.ios_app_store_id,
  tracker.android_package_name,
  tracker.app_name,
  tracker.status as app_tracker_status
from adset aset
left join app_tracker tracker on tracker.id = aset.app_tracker_id;
```

### App event conversion aggregate join

```sql
select
  aec.hour_utc,
  tracker.id as app_tracker_id,
  tracker.app_name,
  aec.event_name,
  aec.conversions
from app_events_conversion_data aec
join app_tracker tracker on tracker.id = aec.app_tracker_id;
```

### Attributed conversion aggregate join

```sql
select
  ac.hour_utc,
  ac.pixel_external_id,
  ac.creative_external_id,
  cr.id as ua_creative_id,
  ac.conversions
from attributed_conversion_data ac
left join creative cr on cr.external_id = ac.creative_external_id;
```

### Mobile app attribution join

```sql
select
  maa.event_timestamp_utc,
  maa.bid_hour_utc,
  maa.event_name,
  maa.conversion_id,
  aa.id as adaccount_id,
  c.id as campaign_id,
  aset.id as adset_id,
  ad.id as ad_id,
  tracker.id as app_tracker_id,
  tracker.app_name,
  maa.revenue
from mobile_app_event_7_day_attribution maa
join ad ad on ad.id = maa.ad_id
join adset aset on aset.id = ad.adset_id
join campaign c on c.id = aset.campaign_id
join adaccount aa on aa.id = c.adaccount_id
left join app_tracker tracker on tracker.id = maa.app_tracker_id;
```

### Kochava conversion aggregate join

```sql
select
  kc.hour_utc,
  ep.id as enhanced_pixel_id,
  ep.name as enhanced_pixel_name,
  kc.event_name,
  kc.conversions
from kochava_conversion_data kc
join enhanced_pixel ep on ep.id = kc.enhanced_pixel_id;
```

### Kochava attribution join

```sql
select
  ka.event_timestamp_utc,
  ka.bid_hour_utc,
  ka.event_name,
  ka.conversion_id,
  ep.id as enhanced_pixel_id,
  aa.id as adaccount_id,
  c.id as campaign_id,
  aset.id as adset_id,
  ad.id as ad_id,
  ka.price
from kochava_seven_day_attribution ka
join enhanced_pixel ep on ep.id = ka.enhanced_pixel_id
left join ad ad on ad.id = ka.ad_id
left join adset aset on aset.id = ad.adset_id
left join campaign c on c.id = aset.campaign_id
left join adaccount aa on aa.id = c.adaccount_id;
```

### Reporting aggregate join

Hourly performance\_report\_pipeline\_merged uses UA internal ad\_id:

```sql
select
  pr.hour_utc,
  c.id as campaign_id,
  aset.id as adset_id,
  ad.id as ad_id,
  pr.impressions,
  pr.clicks,
  pr.conversions,
  pr.spend,
  pr.media_spend,
  pr.vendor_fee_spend
from performance_report_pipeline_merged pr
join ad ad on ad.id = pr.ad_id
join adset aset on aset.id = ad.adset_id
join campaign c on c.id = aset.campaign_id;
```

### Raw log join warning

For raw logs, use downstream IDs to join through the corresponding UA external\_id fields. The example below is illustrative:

```sql
-- Illustrative example; use the validated downstream-ID mapping for production joins.
select
  raw.bid_time_utc,
  c.id as ua_campaign_id,
  aset.id as ua_adset_id,
  raw.campaign_id as downstream_campaign_id,
  raw.line_item_id as downstream_line_item_id,
  raw.creative_id as downstream_creative_id,
  raw.bid_price_micros_usd,
  raw.win_cost_micros_usd,
  raw.app_id,
  raw.app_bundle,
  raw.app_name
from raw_performance_data raw
left join campaign c on c.external_id = raw.campaign_id::text
left join adset aset on aset.external_id = raw.line_item_id::text;
```

## Source-of-Truth Rules

| Data | Source of truth | Consumer rule |
| --- | --- | --- |
| UA hierarchy | Postgres organization -\> adaccount -\> campaign -\> adset -\> ad | Use UUIDs for internal hierarchy joins. |
| Downstream IDs | external\_id fields on UA config objects | For UA objects represented in Beeswax, `external_id` stores the corresponding Beeswax object ID. The UA object’s internal `id` is stored in Beeswax as `alt_id`, providing a direct mapping between UA and BW records. |
| Entity Statuses | UA status fields are the source of truth for entity lifecycle state. | UA status, downstream `external_status`, archive state, and flight dates together determine whether an entity is eligible for delivery in BW. |
| Budgets | Campaign/adset budget fields in Postgres | Enforced at campaign first level, then ad set |
| Pacing / delivery override | adset\_delivery\_override when present | Override table should take precedence over normal UA defaults. |
| Targeting | target JSON plus target\_placement / placement rows | Do not infer all targeting from flattened columns alone. |
| Creative eligibility | creative status lookups plus approval\_status; ad status also matters | Creative approval can block delivery even if an ad set is active. |
| Spend and performance | Reporting pipeline / raw logs | Use UTC hour for time-series joins. |
| App event measurement | app\_tracker, app\_events\_conversion\_data, and mobile\_app\_event\_\*\_day\_attribution | Use app\_tracker\_id for app-event measurement joins when available. |
| Attributed conversions | attributed\_conversion\_data and raw\_attributed\_conversion\_data | Use attributed aggregates for pixel/creative/hour summaries and raw data for conversion-level traceability. |
| Kochava conversions | kochava\_conversion\_data, kochava\_*day\_attribution, gold\_kochava*\_day\_attribution, kochava, and kochava\_data | Use enhanced\_pixel\_id where available; treat raw/query-layer IDs as strings unless explicitly mapped. |
| App / supply identifiers | Log fields such as app\_id, app\_bundle, app\_name | Treat app identifiers in delivery data as supply/provider identifiers, not UA internal application UUIDs unless explicitly mapped. |
| Names | name, app\_name, site\_name, publisher\_name | Descriptive only. Do not use names as durable join keys. |

## Easy-to-Misinterpret Details

- UA Postgres entity IDs are UUIDs. Entities map to raw delivery logs through `external_id` fields containing downstream integer identifiers.
- campaign.id is a UA UUID; raw campaign\_id is a downstream integer ID.
- adset.id is a UA UUID; raw line\_item\_id is the downstream line item/ad set identifier.
- ad.id is a UA UUID; performance\_report\_pipeline\_merged.ad\_id is also a UUID and is safe to join to ad.id.
- creative.id is a UA UUID; raw creative\_id is a downstream integer ID.
- application.id is UA/developer application metadata. Delivery-log app\_id, app\_bundle, and app\_name describe inventory/supply context and should not be assumed to join to application.id.
- app\_tracker.id is the UA UUID for app measurement configuration. It is not the same as delivery-log app\_id.
- app\_tracker.app\_name is descriptive and should not be used as a durable join key.
- Kochava attribution tables use enhanced\_pixel\_id, while app-event attribution tables use app\_tracker\_id.
- kochava\_\*\_day\_attribution.ad\_id is nullable, so some Kochava conversions may not join all the way to ad, ad set, or campaign.
- gold\_kochava\_\*\_day\_attribution stores IDs as strings in query-only mappings, unlike the UUID fields in UA Postgres models.
- media.application\_id is a nullable string, not a UUID foreign key to application.id.
- name, app\_name, site\_name, and similar fields are descriptive and should not be used as durable join keys.
- start\_date / end\_date and start\_date\_utc / end\_date\_utc both exist on campaigns and ad sets. Runtime systems should prefer UTC fields.
- status and external\_status are separate. A UA object can exist locally before or after downstream sync.
- Budget fields are floats in Postgres, while raw log cost fields are often micros. Convert and reconcile before comparing.
- Some JSON fields are business-critical, especially adset.bidding, adset.frequency\_cap, target.*, delivery.delivery, and adset\_delivery\_override.*.
- Placement external\_id may contain comma-separated values. Use the split semantics if mapping bid requests to placement IDs.
- Admin overrides are intentionally separate from normal advertiser-managed ad set and targeting data.

## Relevant Data Groups

### Status / Control Data

| Feature | Source |
| --- | --- |
| Campaign/adset/ad active flags | campaign.status, adset.status, ad.status |
| Downstream active flags | external\_status fields |
| Flight windows | campaign.start\_date\_utc, campaign.end\_date\_utc, adset.start\_date\_utc, adset.end\_date\_utc |
| Daily/lifetime budgets | campaign.daily\_budget, campaign.lifetime\_budget, adset.daily\_budget, adset.lifetime\_budget |
| Bid | adset.bid, adset.bidding |
| Frequency cap | campaign/adset frequency cap fields |
| Pacing override | adset\_delivery\_override.pacing\_type |
| Bid/delivery modifiers | adset\_delivery\_override.delivery\_modifier\_id, adset\_delivery\_override.bid\_modifier |
| Creative rotation | ad.rotation\_weight, adset\_delivery\_override.dynamic\_creative\_rotation, creative\_rotation\_weights |

### Targeting / Context Data

| Feature | Source |
| --- | --- |
| Placement IDs and bid floors | target\_placement, placement.external\_id, placement.bid\_floor |
| Geo targeting | target.location |
| Age/gender targeting | target.age, target.gender |
| Device targeting | target.device\_type |
| Audience segments | target.segment, custom\_segments where referenced |
| Genre/contextual targeting | target.genre, raw log content fields |
| Dayparting | target.day\_part |
| Content language | target.content\_language |
| Inventory | adset.inventory, raw inventory\_source fields |
| Deal restrictions | adset\_delivery\_override.included\_deal\_ids, raw deal\_id |
| Publisher exclusions | adset\_delivery\_override.publisher\_exclusion\_ids, raw publisher\_id |

### Performance / Measurement Data

| Feature | Source |
| --- | --- |
| Impressions, clicks, conversions | performance\_report\_pipeline\_merged, raw logs |
| Attributed web conversions | attributed\_conversion\_data, raw\_attributed\_conversion\_data |
| App event conversions | app\_events\_conversion\_data, mobile\_app\_event\_7\_day\_attribution, mobile\_app\_event\_14\_day\_attribution, mobile\_app\_event\_30\_day\_attribution |
| Kochava conversions and attribution | kochava\_conversion\_data, kochava\_seven\_day\_attribution, kochava\_fourteen\_day\_attribution, kochava\_thirty\_day\_attribution, gold\_kochava\_\*\_day\_attribution, kochava |
| Spend | performance\_report\_pipeline\_merged.spend, media\_spend, vendor\_fee\_spend; raw micros cost fields |
| Bid price and bid floor | raw bid\_price\_micros, bid\_floor\_micros |
| CTR, CVR, CPA, CPM, CPC | performance\_report\_pipeline\_merged derived metrics or recomputed from raw data |
| App/site performance | raw app\_id, app\_bundle, site\_id, domain, publisher\_id |
| Device performance | raw platform/device fields |
| Geo performance | raw geo fields |
| Content performance | raw content fields |
| Model lineage | raw model\_id, bid\_model\_id, bid\_agent\_id, params fields |
