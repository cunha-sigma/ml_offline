# Entity Mapping

# the client Object and the DSP Mapping Overview

This document summarizes the client objects and external mappings that are relevant to the sigma data dictionary. It is intentionally focused on the data used for hierarchy, delivery configuration, targeting, measurement, raw logs, and attribution.

| the client object / dataset | High-level definition | the DSP / external mapping | User-visible? | Notes / nuance |
| --- | --- | --- | --- | --- |
| Organization | Top-level business entity for the customer. Owns ad accounts and provides tenant-level context. | the DSP account / client account context | Yes | Useful for customer hierarchy, account ownership, timezone, inventory access, and financial context. |
| Ad account | Advertiser-level business entity under an organization. Owns campaigns, creatives, audiences, pixels, and app trackers. | the DSP advertiser | Yes | Main advertiser container for campaign execution and reporting joins. |
| Campaign | Top-level advertising container that defines budget, objective, and flight dates. Parent of ad sets. | the DSP campaign | Yes | Campaign objective and flight settings influence child ad set behavior. |
| Ad set | Child of campaign that defines targeting, pacing, budget behavior, placement selection, inventory, bid settings, and tracking associations. | DSP line item, targeting, event association | Yes | A single the client ad set maps to multiple the DSP concepts and is the central object for delivery configuration. |
| Ad | Delivery object that ties a creative to an ad set. | the DSP creative, creative-line-item association | Yes | Distinct from creative. Ad status and creative status both matter for delivery context. |
| Creative | Reusable ad-serving asset wrapper used by ads. | the DSP creative asset | Yes | Creative encoding, processing, and approval are separate from raw media upload. |
| Media | Raw uploaded file used by creative and audience workflows. | None | No | Supporting object only. Media is not itself a the DSP delivery object. |
| Network | the client inventory grouping representing a publisher, partner, owned-and-operated group, or event-based inventory group. | Expressed through downstream delivery and targeting configuration | Yes | Network controls inventory availability and placement behavior. |
| Placement | Targetable inventory grouping beneath a network. | the DSP deal ID | Yes | Every network has an automatic placement. Some networks also support additional placements. |
| Genre | Content grouping used to narrow delivery based on content type. | the DSP content genre | Yes | Network-dependent targeting classification rather than a free-form field. |
| Custom segment / audience | Audience data used for targeting, such as uploaded hashed emails, IPs, or similar identifiers. | the DSP segment | Yes | Processing may take time before a segment becomes eligible for targeting. |
| Enhanced pixel | Conversion-tracking model used at the ad set level for web/event measurement. | None | Yes | Used to use the DSP pixel, now we leverage the web-attribution provider for our web conversion measurement tool. |
| App tracker | App-promotion tracking model for app metadata, MMP context, app attribution, and app event alignment. | External app tracker / attribution provider integration | Yes | Distinct from enhanced pixel, we support multiple MMP providers. |
| Conversion aggregates | Hourly conversion summaries for pixels, app trackers, and the web-attribution provider events. | None | No | Includes `conversion_data`, `app_events_conversion_data`, and `kochava_conversion_data`. |
| Attributed conversion data | Conversion events attributed back to ads, creatives, line items, campaigns, pixels, or app trackers. | None | Yes | Includes raw and aggregated attribution datasets across web, app, and the web-attribution provider workflows. |
| Raw DSP delivery / win logs | Lower-level auction and win-event data containing delivery context, bid details, cost, supply, user/device, content, and outcome fields. | the DSP batched and streamed log | No | Raw DSP delivery/win-log data is stored in S3; upstream schema details are available in the DSP data schema docs. |
| Raw conversion data | Lower-level conversion/event source data used to build aggregates and attribution outputs. | Conversion providers, the web-attribution provider, app-event sources | No | Raw conversion data is stored in S3; deeper storage and transformation details live in the separate data and pipeline docs. |
