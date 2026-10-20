# **Bidder Agent Initial Skeleton and Benchmark Proposal**

## **Introduction**

This proposal compares two deployment architectures for the client bidding agent: distributed Go microservices communicating through gRPC, and a single Go application with modular internal components. Benchmarks will also compare concurrency patterns within the single application.

Choose the simplest architecture that meets the agreed latency, throughput, and reliability requirements with sufficient headroom.

## **External Integration Contract**

The ad server sends an HTTP POST with a protobuf bid.BidAgentRequest body. The agent returns HTTP 200 with a protobuf bid.BidAgentResponse, or HTTP 204 with no bid. The ad server documents a strict 10-ms HTTP response timeout and recommends deployment in the same AWS region. Our processing budget must leave room for transport time. [Bidding Agent guide](link-redacted-ad-server-vendor)

This external interface stays the same for every benchmark variant. gRPC is an internal communication option for the distributed architecture.

## **Logical Components**

1.  **Handler / Processor:** Decode and validate requests, extract candidates and context, coordinate work, and encode the response.

2.  **Discount Pacing:** Periodically update line-item pacing factors and expose the current values for request-time lookup.

3.  **ML Prediction:** Produce an action probability for each candidate from its features. The production model and serving implementation remain undecided.

4.  **Bid Decision:** Combine pacing, advertiser value, and probability; produce bid or no-bid decisions.

The initial prediction interface should return probabilities explicitly. Expected value is calculated once as Max CPA × P(Action), followed by bid = λ × expected value. These are logical boundaries, not requirements for separate deployments or goroutines.

## **Approach 1 — Distributed Microservices**

The processor fans out to pacing and prediction services through gRPC, collects their results, and invokes bid calculation. For the initial comparison, bid calculation stays with the processor to avoid adding a separate deployment variable.

Compare unary calls and streaming separately. Reuse connections, define request/result correlation for streams, and report connection setup separately from steady-state latency. Measure serialization and deserialization as well as network and queueing time.

## **Approach 2 — Modular In-Process Application**

A single deployable Go application contains the four components behind an orchestrator, with no internal network communication. Multiple replicas may serve traffic.

Compare these execution patterns:

<table style="width:100%;">
<colgroup>
<col style="width: 23%" />
<col style="width: 76%" />
</colgroup>
<thead>
<tr>
<th style="text-align: center;"><strong>Variant</strong></th>
<th style="text-align: center;"><strong>Execution within each request</strong></th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: center;"><ol type="A">
<li><p>Sequential</p></li>
</ol></td>
<td>Call pacing lookup, prediction, and bid calculation directly in sequence. Requests can still execute concurrently.</td>
</tr>
<tr>
<td style="text-align: center;"><ol start="2" type="A">
<li><p>Per-request goroutines</p></li>
</ol></td>
<td>Launch independent pacing lookup and prediction operations concurrently, collect their results, then calculate bids.</td>
</tr>
<tr>
<td style="text-align: center;"><ol start="3" type="A">
<li><p>Persistent worker pools</p></li>
</ol></td>
<td>Start workers at initialization; dispatch work through separate bounded pacing and prediction channels and collect results for the originating request.</td>
</tr>
<tr>
<td style="text-align: center;"><ol start="4" type="A">
<li><p>Direct pacing lookup with inference workers</p></li>
</ol></td>
<td>Read an in-memory pacing snapshot directly and dispatch prediction work to a bounded pool before calculating bids.</td>
</tr>
</tbody>
</table>

Pacing recalculation runs outside the request path in every variant. Pool sizes, channel capacities, deadlines, and overload behavior must be recorded. Workers must handle cancellation without blocking on replies to expired requests. Bid arithmetic and response construction remain in the request orchestrator.

## **Benchmark Payload Contract**

Use the official bid.BidAgentRequest envelope, which contains bid_request and repeated adcandidates, and the matching response type from [request.proto](link-redacted-dsp-api).

The nested auction message uses the DSP's [OpenRTB schemas and extensions](link-redacted-dsp-api). Candidate configuration follows [adcandidate.proto](link-redacted-dsp-api), including line-item and creative IDs, bidding settings, frequency-cap information, and fees where populated.

Fixtures should be maintained in protobuf text format for review and compiled to binary protobuf for HTTP benchmarks. JSON is not the benchmark wire format. Pin the upstream repository commit and include all transitive schema imports when generating Go bindings. Record that commit with each benchmark run.

### **Initial Example Request**

The following is a proposed synthetic banner fixture for validating the envelope and basic bid arithmetic. It is not a production traffic sample or a substitute for video workloads. It has not yet been compiled against pinned schemas.

bid_request {\
id: "benchmark-banner-0001"\
test: true\
imp {\
id: "imp-1"\
banner {\
w: 300\
h: 250\
}\
bidfloor: 1.0\
bidfloorcur: "USD"\
}\
site {\
id: "benchmark-site-1"\
domain: "example.com"\
}\
cur: "USD"\
}\
adcandidates {\
line_item_id: 1001\
campaign_id: 2001\
account_id: 3001\
advertiser_id: 4001\
creative_ids: 5001\
creative_ids: 5002\
}

For this fixture, benchmark-owned state supplies λ = 0.8, Max CPA = USD 20, and a deterministic prediction of 0.001. These values are separate from the incoming request; they are not additional the ad server protobuf fields. Candidate IDs key the configuration and pacing lookups.

The expected bid is 0.8 × 20 × 0.001 = USD 0.016 per impression, equivalent to USD 16 CPM. The response uses integer micros per impression, as specified by [request.proto](link-redacted-dsp-api):

bids {\
line_item_id: 1001\
bid_price_micros: 16000\
creative {\
id: 5001\
}\
}

Return this encoded response with HTTP 200. Creative 5001 is deliberately selected from the incoming candidate's eligible IDs. A separate no-bid fixture expects HTTP 204 and an empty body.

### **Proposed Payload Matrix**

These counts are initial synthetic benchmark parameters, not observed the client traffic distributions. Start with one impression per request so candidate count can be varied independently.

| **Profile** | **Candidates** | **Creatives per candidate** | **Context** | **Purpose** |
|:--:|----|----|----|----|
| Minimal banner | 1 | 2 | Example above | Envelope and arithmetic correctness |
| Small video | 1 | 2 | App, video, and device context | Basic video request cost |
| Medium video | 10 | 4 | Same context as small video | Candidate scaling |
| Large video | 100 | 4 | Same context as small video | Higher candidate workload |
| Candidate stress | 500 | 4 | Same context as small video | Queueing and saturation exploration |
| Rich context | 10 | 4 | Add content, geo, segments, deals, and frequency-cap data | Effect of populated optional fields |
| Creative stress | 10 | 20 | Same context as medium video | Creative-list parsing and selection cost |

Use valid fields and enum values from the pinned schemas. Populate video MIME types, duration constraints, dimensions, and supported protocols consistently. Use synthetic identifiers and context values. Add multiple-impression scenarios once the applicable candidate-to-impression and response semantics are confirmed.

Record actual serialized request and response byte sizes for every fixture; do not infer sizes from candidate counts or pad messages with meaningless strings. Add missing optional context, empty candidates, malformed protobuf, and unavailable pacing/prediction cases as separately reported correctness and failure scenarios. Their fallback policies remain to be defined.

### **Separate Request Payloads from Model Workloads**

Every architecture variant must receive the same external binary fixtures and use equivalent configuration, pacing snapshots, feature preparation, and prediction behavior. Internal gRPC messages should carry the data required by each component, rather than automatically copying the full external envelope. Their exact contracts and encoded sizes must be documented when implemented.

Run two benchmark categories:

- **Orchestration baseline:** A deterministic prediction implementation and fixed pacing snapshot isolate parsing, dispatch, collection, arithmetic, and encoding costs.

- **Representative inference:** Replace the stub with an agreed model and realistic feature preparation to measure achievable bidder performance. Until that exists, baseline results cannot establish production inference capacity.

Where results must match exactly, specify the same candidate ordering, creative selection, rounding, and missing-data behavior across variants. The example above uses an exact integer-micros result; general rounding policy is still an implementation decision.

### **Upstream Request Tool**

The [DSP bid tools directory](link-redacted-dsp-api) provides a generator archive. Its README describes ASCII requests separated by ===, sample request files, optional response capture, and a secret-header option.

Inspect the archive and its samples before adopting it. It has not yet been downloaded or executed for this proposal. It may help verify protocol compatibility; its suitability as a load generator must be measured independently.

## **Measurement and Result Matrix**

Use equivalent workloads and decision logic across variants. Pre-generate fixtures outside the timed path, reuse client connections, and keep hardware resources, logging settings, and request mixes comparable. Record replica counts, worker counts, model/runtime versions, and deployment topology.

Measure:

- End-to-end HTTP p50, p95, and p99 latency, including queue wait and response encoding.

- Throughput while meeting the agreed latency target, plus timeout and error rates.

- Parsing, feature preparation, pacing lookup, inference, bid calculation, and serialization time.

- Internal RPC or channel queue wait, CPU, memory, allocations, and garbage-collection behavior.

- Behavior under increasing offered request rates and bursts, including rejected and expired requests.

- Implementation and operational complexity.

Report offered and completed request rates, including failures. Ensure the load generator does not hide overload by slowing its offered rate while waiting for responses. Local measurements characterize processing; testing in the intended deployment topology is required to assess the external timeout.

| **Architecture / execution variant** | **Payload profile** | **Offered / completed RPS** | **p50 / p95 / p99** | **Timeout / error rate** | **CPU / memory** | **Complexity** |
|:--:|----|----|----|----|----|----|
| To be measured | To be measured | — | — | — | — | — |

## **Decisions Still Required**

- Pin the schema revision, compile fixtures, and validate request/response round trips.

- Obtain sanitized samples or aggregate traffic statistics to calibrate synthetic payload profiles and request rates.

- Confirm production inference and feature requirements, pacing freshness, and missing-data policies.

- Define the target throughput, latency percentile, and operating headroom used for architecture selection.

## **Payloads for the benchmarks**

The following three payloads came bundled with the [ad-server/DSP tool](link-redacted-dsp-api), in sample_bid_request_1.txt. They were not newly generated by the tool. Their binary protobuf versions were generated locally using the tool's bundled schemas and parsing/serialization operations. The original HTTP client was not run.

All three passed protobuf required-field checks and binary encode/decode checks using the bundled schemas. The sizes below are request-body sizes, excluding HTTP headers. These are the tool's banner examples, not verified examples of current client production traffic.

| **Payload** | **Candidates** | **Creatives per candidate** | **Text size (bytes)** | **Binary protobuf size (bytes)** |
|:--:|----|----|----|----|
| [Payload 1](link-redacted-ad-server-vendor) | 1 | 2 | 4,008 | [1,261](link-redacted-ad-server-vendor) |
| [Payload 2](link-redacted-ad-server-vendor) | 2 | 1, 1 | 6,033 | [2,057](link-redacted-ad-server-vendor) |
| [Payload 3](link-redacted-ad-server-vendor) | 1 | 3 | 3,448 | [1,089](link-redacted-ad-server-vendor) |

The complete payloads are included below. The [manifest](link-redacted-ad-server-vendor) records their source and checksums.

### **Payload 1**

bid_request {\
id: "565542320920730572"\
imp {\
id: "1"\
banner {\
w: 320\
h: 50\
id: "1"\
pos: ABOVE_THE_FOLD\
btype: XHTML_TEXT\
btype: IFRAME\
battr: EXPANDABLE_AUTOMATIC\
battr: POP_UP\
battr: PROVOCATIVE_OR_SUGGESTIVE\
battr: VIDEO_IN_BANNER_AUTO_PLAY\
battr: VIDEO_IN_BANNER_USER_INITIATED\
battr: ANNOYING\
battr: AD_CAN_EXPAND_LEFT\
battr: AD_CAN_EXPAND_RIGHT\
battr: AD_CAN_EXPAND_UP\
battr: AD_CAN_EXPAND_DOWN\
battr: AD_CAN_EXPAND_FULLSCREEN\
topframe: YES\
api: ORMMA\
api: MRAID\
api: MRAID_2\
wmin: 300\
hmin: 50\
ext {\
}\
}\
instl: NO\
bidfloor: 1.7948717948717949\
bidfloorcur: "USD"\
secure: 0\
ext {\
placement_type: BANNER\
environment_type: APP\
viewability {\
predicted_viewability: 0\
}\
}\
}\
app {\
id: "602789"\
name: "iFunny :)"\
cat: "IAB1"\
cat: "IAB9"\
bundle: "429610587"\
publisher {\
id: "4119"\
name: "Flysoft"\
ext {\
}\
}\
storeurl: "<http://itunes.apple.com/us/app/ifunny/id429610587?mt=8>"\
ext {\
}\
}\
device {\
dnt: NO\
ua: "Mozilla/5.0 (iPhone; CPU iPhone OS 10_0_2 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) Mobile/14A456"\
ip: "216.4.56.166"\
geo {\
lat: 37.751\
lon: -97.822\
country: "USA"\
type: IP\
ext {\
}\
}\
dpidsha1: "B949D721CF2020CB7BDE3C69290350919941A6C5"\
dpidmd5: "5F5863F80354E60DE16DC98F867947F2"\
carrier: "150"\
language: "en"\
make: "Apple"\
model: "iPhone"\
os: "iOS"\
osv: "10"\
js: YES\
connectiontype: CELL_4G\
devicetype: PHONE\
w: 320\
h: 568\
ifa: "D89C3F28-C6DE-4817-87A0-EE6E67FCAD32"\
ext {\
augmented_device_screen_size: "M"\
augmented_browser: "Safari"\
augmented_browser_version: "10"\
}\
}\
user {\
gender: ""\
geo {\
country: "USA"\
}\
data {\
id: "stinger"\
segment {\
id: "stinger-5566"\
value: ""\
}\
ext {\
beeswax_augmented: true\
}\
}\
ext {\
user_id: "mid.D89C3F28-C6DE-4817-87A0-EE6E67FCAD32"\
user_id_type: IDFA\
}\
}\
at: 2\
tmax: 250\
bcat: "IAB25"\
bcat: "IAB26"\
badv: "[www.weeeireland.ie](https://www.weeeireland.ie)"\
badv: "newholland.com"\
badv: "<http://www.tescomobile.ie/>"\
badv: "<http://www.audi.ie/>"\
badv: "budweiser.co.uk"\
badv: "Heineken.com"\
badv: "g.doubleclick.net"\
badv: "visitseattle.org"\
badv: "snickers.com"\
badv: "ugg.com"\
badv: "drpepper.com"\
badv: "aarons.com"\
badv: "cadillac.com"\
badv: "delta.com"\
badv: "rossstores.com"\
badv: "nissanusa.com"\
badv: "verizonwireless.com"\
regs {\
coppa: NO\
}\
ext {\
inventory_source: INNERACTIVE\
auction_id {\
hostid: 4035294731\
tid: 4756\
timestamp: 1475209741393069\
}\
targeting_geo {\
country: "USA"\
lat_long_present: true\
lat: 37.751\
lon: -97.822\
type: IP\
}\
time_of_week: 7229\
buzz_key: "stinger"\
augmentor_data {\
id: "BW_Managed_List"\
segment {\
id: "app_bundle_list"\
value: "26"\
}\
segment {\
id: "app_bundle_list"\
value: "36"\
}\
}\
auctionid_str: "1475209741393069.4035294731.4756.stinger"\
}\
}\
adcandidates {\
line_item_id: 278\
creative_ids: 331\
creative_ids: 332\
bidding {\
custom_strategy {\
name: "FLAT_PRICE_STRATEGY"\
custom_params{\
key: "flat_price_micros_usd"\
value: "5010"\
}\
}\
}\
pacing {\
pace_delivery: true\
}\
campaign_id: 18\
account_id: 2\
buzz_key: "stinger"\
advertiser_id: 13\
line_item_frequency_caps_info {\
frequency_cap {\
max_impressions: 3\
duration_seconds: 86400\
current_impression_count: 0\
}\
}\
campaign_frequency_caps_info {\
frequency_cap {\
max_impressions: 10\
duration_seconds: 2592000\
current_impression_count: 0\
}\
}\
}

### **Payload 2**

bid_request {\
id: "965f7b72-49c7-4f8a-9df1-364254dc8905"\
imp {\
id: "965f7b72-49c7-4f8a-9df1-364254dc8905-1"\
banner {\
w: 320\
h: 50\
pos: FOOTER\
btype: XHTML_TEXT\
battr: AUDIO_AUTO_PLAY\
battr: AUDIO_USER_INITIATED\
battr: EXPANDABLE_AUTOMATIC\
battr: EXPANDABLE_ROLLOVER_INITIATED\
battr: VIDEO_IN_BANNER_AUTO_PLAY\
battr: VIDEO_IN_BANNER_USER_INITIATED\
battr: POP_UP\
battr: PROVOCATIVE_OR_SUGGESTIVE\
battr: TEXT_ONLY\
battr: USER_INTERACTIVE\
battr: WINDOWS_DIALOG_OR_ALERT_STYLE\
battr: HAS_AUDIO_ON_OFF_BUTTON\
battr: AD_CAN_EXPAND_LEFT\
battr: AD_CAN_EXPAND_RIGHT\
battr: AD_CAN_EXPAND_UP\
battr: AD_CAN_EXPAND_DOWN\
battr: AD_CAN_EXPAND_FULLSCREEN\
api: MRAID_2\
api: MRAID\
}\
displaymanager: "millennial"\
displaymanagerver: "6.1.0-5323db4"\
instl: NO\
bidfloor: 6.18\
ext {\
placement_type: BANNER\
environment_type: APP\
viewability {\
predicted_viewability: 0\
}\
}\
}\
app {\
id: "400672"\
name: "New Words with Friends - Android - Banner"\
domain: "zynga.com"\
cat: "IAB1"\
cat: "IAB9"\
bundle: "com.zynga.wwf2.free"\
publisher {\
id: "5041102"\
name: "Zynga"\
ext {\
}\
}\
storeurl: "<https://play.google.com/store/apps/details?id=com.zynga.words>"\
}\
device {\
dnt: NO\
ua: "Mozilla/5.0 (Linux; Android 5.1.1; SM-G360T1 Build/LMY47X; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.124 Mobile Safari/537.36"\
ip: "76.105.224.54"\
geo {\
lat: 45.5269\
lon: -122.8573\
country: "USA"\
region: "OR"\
metro: "820"\
zip: "97006"\
type: IP\
}\
carrier: "WIFI"\
language: "en"\
make: "Samsung"\
model: "-1"\
os: "Android"\
osv: "5.1"\
js: YES\
connectiontype: WIFI\
devicetype: PHONE\
lmt: false\
hwv: "SM-G360T1"\
ppi: 240\
ifa: "1bb22640-b067-4418-9a90-3ce74453ca87"\
ext {\
augmented_device_screen_size: "NA"\
augmented_browser: "-1"\
augmented_browser_version: "53"\
}\
}\
user {\
id: "1bb22640-b067-4418-9a90-3ce74453ca87"\
geo {\
country: "USA"\
region: "USA/OR"\
metro: "820"\
city: "5731371"\
zip: "97124"\
type: USER\
}\
data {\
id: "stinger"\
segment {\
id: "stinger-807"\
value: ""\
}\
ext {\
beeswax_augmented: true\
}\
}\
ext {\
user_id: "mid.1BB22640-B067-4418-9A90-3CE74453CA87"\
user_id_type: AD_ID\
}\
}\
at: 2\
bcat: "IAB22_1"\
bcat: "IAB23"\
bcat: "IAB19_25"\
bcat: "IAB7_29"\
bcat: "IAB7_28"\
bcat: "IAB7_45"\
bcat: "IAB7_44"\
bcat: "IAB26"\
bcat: "IAB25"\
bcat: "IAB24"\
bcat: "IAB7_30"\
bcat: "IAB7_31"\
bcat: "IAB7_38"\
bcat: "IAB7_18"\
bcat: "IAB7_39"\
bcat: "IAB19_30"\
bcat: "IAB7_41"\
bcat: "IAB7_42"\
bcat: "IAB19_3"\
bcat: "IAB7_3"\
bcat: "IAB14_3"\
bcat: "IAB14_2"\
bcat: "IAB14_1"\
bcat: "IAB15_5"\
bcat: "IAB9_9"\
badv: "drinkbai.com"\
badv: "wordbrain.com"\
badv: "harryconnickjr.com"\
badv: "ifunny.co"\
badv: "cm.best-thing.eu"\
badv: "wordox.com"\
badv: "fanatee.com"\
badv: "maginteractive.com"\
badv: "scopely.com"\
badv: "badoo.com"\
badv: "dicewithbuddies.com"\
badv: "pg.com"\
badv: "californialottery.com"\
badv: "classesusa.com"\
badv: "apprope.com"\
badv: "fogs.com"\
badv: "abc.com"\
badv: "zynga.com"\
badv: "peakgames.net"\
badv: "mediasmart.com"\
badv: "etermax.com"\
badv: "puzzlesocial.com"\
badv: "triviacrack.com"\
badv: "yahtzeewithbuddies.com"\
regs {\
coppa: NO\
}\
ext {\
inventory_source: MILLENNIAL\
auction_id {\
hostid: 12966349\
tid: 12891\
timestamp: 1475209787191604\
}\
targeting_geo {\
country: "USA"\
region: "USA/OR"\
city: "5731371"\
zip: "97124"\
metro: "820"\
lat_long_present: true\
lat: 45.5269\
lon: -122.8573\
type: IP\
}\
time_of_week: 7229\
buzz_key: "stinger"\
augmentor_data {\
id: "BW_Managed_List"\
segment {\
id: "app_id_list"\
value: "32"\
}\
segment {\
id: "app_id_list"\
value: "50"\
}\
segment {\
id: "app_id_list"\
value: "44"\
}\
segment {\
id: "app_id_list"\
value: "31"\
}\
segment {\
id: "app_bundle_list"\
value: "33"\
}\
segment {\
id: "app_bundle_list"\
value: "36"\
}\
segment {\
id: "app_bundle_list"\
value: "8"\
}\
segment {\
id: "app_bundle_list"\
value: "13"\
}\
segment {\
id: "app_bundle_list"\
value: "15"\
}\
segment {\
id: "app_bundle_list"\
value: "19"\
}\
segment {\
id: "app_bundle_list"\
value: "22"\
}\
segment {\
id: "app_bundle_list"\
value: "25"\
}\
}\
auctionid_str: "1475209787191604.12966349.12891.stinger"\
}\
}\
adcandidates {\
line_item_id: 520\
creative_ids: 1080\
bidding {\
custom_strategy {\
name: "FLAT_PRICE_STRATEGY"\
custom_params{\
key: "flat_price_micros_usd"\
value: "1850"\
}\
}\
}\
pacing {\
pace_delivery: true\
}\
campaign_id: 199\
account_id: 2\
buzz_key: "stinger"\
advertiser_id: 37\
campaign_frequency_caps_info {\
frequency_cap {\
max_impressions: 3\
duration_seconds: 86400\
current_impression_count: 0\
}\
}\
}\
adcandidates {\
line_item_id: 523\
creative_ids: 1075\
bidding {\
custom_strategy {\
name: "FLAT_PRICE_STRATEGY"\
custom_params{\
key: "flat_price_micros_usd"\
value: "1850"\
}\
}\
}\
pacing {\
pace_delivery: true\
}\
campaign_id: 199\
account_id: 2\
buzz_key: "stinger"\
advertiser_id: 37\
campaign_frequency_caps_info {\
frequency_cap {\
max_impressions: 3\
duration_seconds: 86400\
current_impression_count: 0\
}\
}\
}

### **Payload 3**

bid_request {\
id: "93102ee8-c993-4ea9-aaff-ad5cdaf1ae4e"\
imp {\
id: "93102ee8-c993-4ea9-aaff-ad5cdaf1ae4e"\
banner {\
w: 300\
h: 250\
battr: AUDIO_AUTO_PLAY\
battr: AUDIO_USER_INITIATED\
battr: VIDEO_IN_BANNER_AUTO_PLAY\
battr: VIDEO_IN_BANNER_USER_INITIATED\
battr: PROVOCATIVE_OR_SUGGESTIVE\
battr: ANNOYING\
battr: SURVEYS\
battr: WINDOWS_DIALOG_OR_ALERT_STYLE\
ext {\
}\
}\
secure: 0\
ext {\
placement_type: BANNER\
environment_type: WEB\
viewability {\
predicted_viewability: 0\
}\
}\
}\
site {\
id: "537231578"\
domain: "patch.com"\
cat: "IAB12_3"\
page: "http://patch.com/georgia/cascade/the-ugly-side-of-the-beauty-supply-market"\
ref: "https://www.google.com/"\
publisher {\
id: "537123427"\
}\
mobile: true\
ext {\
}\
}\
device {\
dnt: NO\
ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36"\
ip: "71.56.67.56"\
geo {\
lat: 33.876\
lon: -84.455\
country: "USA"\
region: "GA"\
zip: "30339"\
type: IP\
utcoffset: 240\
ext {\
}\
}\
language: "en"\
make: "-1"\
model: "-1"\
os: "Windows"\
osv: "10"\
devicetype: PC\
w: 1600\
h: 900\
ext {\
augmented_device_screen_size: "XL"\
augmented_browser: "Chrome"\
augmented_browser_version: "53"\
}\
}\
user {\
id: "8ae8cefa-8e09-4368-ab85-7787d3842c1e"\
buyeruid: "AALBuE6vLQUAAGAGE97QIA"\
customdata: "AALBuE6vLQUAAGAGE97QIA"\
geo {\
country: "USA"\
region: "USA/GA"\
metro: "524"\
city: "4223379"\
zip: "30080"\
}\
data {\
id: "bluekai"\
segment {\
id: "bluekai-42965"\
value: ""\
}\
segment {\
id: "bluekai-17531"\
value: ""\
}\
segment {\
id: "bluekai-42958"\
value: ""\
}\
segment {\
id: "bluekai-34455"\
value: ""\
}\
ext {\
beeswax_augmented: true\
}\
}\
ext {\
user_id: "bito.AALBuE6vLQUAAGAGE97QIA"\
user_id_type: BEESWAX\
}\
}\
cur: "USD"\
bcat: "IAB17_18"\
bcat: "IAB23"\
bcat: "IAB24"\
bcat: "IAB25"\
bcat: "IAB25_3"\
regs {\
coppa: NO\
}\
test: false\
ext {\
inventory_source: OPENX\
auction_id {\
hostid: 170433165\
tid: 4613\
timestamp: 1475209798669330\
}\
targeting_geo {\
country: "USA"\
region: "USA/GA"\
city: "4223379"\
zip: "30080"\
metro: "524"\
lat_long_present: true\
lat: 33.876\
lon: -84.455\
type: IP\
}\
time_of_week: 7229\
buzz_key: "stinger"\
augmentor_data {\
id: "BW_Managed_List"\
segment {\
id: "domain_list"\
value: "39"\
}\
}\
auctionid_str: "1475209798669330.170433165.4613.stinger"\
}\
}\
adcandidates {\
line_item_id: 612\
creative_ids: 1182\
creative_ids: 1183\
creative_ids: 1184\
bidding {\
custom_strategy {\
name: "FLAT_PRICE_STRATEGY"\
custom_params{\
key: "flat_price_micros_usd"\
value: "2510"\
}\
}\
}\
pacing {\
pace_delivery: false\
}\
campaign_id: 185\
account_id: 2\
buzz_key: "stinger"\
advertiser_id: 52\
campaign_frequency_caps_info {\
frequency_cap {\
max_impressions: 5\
duration_seconds: 86400\
current_impression_count: 0\
}\
}\
}
