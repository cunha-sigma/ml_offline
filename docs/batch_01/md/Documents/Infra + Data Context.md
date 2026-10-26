# the client Infra and Data Context



## the client Infrastructure And Data Platform Overview

The client runs in AWS within a private cloud architecture that supports campaign management, delivery integrations, event ingestion, reporting, attribution, and data science workflows.

The platform combines application services, relational configuration data, raw event data, governed data lake storage, and third-party integrations such as the DSP, the web-attribution provider, Stripe, and the ad server-managed infrastructure.

The advanced bidder work is most closely connected to the client’s raw delivery data, event ingestion paths, governed warehouse datasets, attribution outputs, and the client-to-DSP identity mapping.

## 1a. Infrastructure Code And CI/CD

client infrastructure code is managed in GitHub. Changes to infrastructure code trigger AWS CI/CD workflows that plan, review, and apply Terraform changes.

Infrastructure is managed with Terraform, with separate environment roots for `dev`, `stg`, and `prod`, and shared modules reused across environments. Terraform pipelines support controlled deployment of platform infrastructure, including AWS resources used by APIs, data services, background jobs, networking, security, and warehouse access.

## 1b. Core Application Code And CI/CD

The client application code is also managed through GitHub-backed AWS deployment pipelines. Different sections of the application, including APIs, background services, UI applications, and supporting jobs, have their own deployment paths.

This allows the client to deploy platform services independently while keeping changes tied to source control, build pipelines, and environment-specific release processes.

## 2. AWS VPC And Subnets

The client runs inside a private AWS VPC. The VPC and subnet configuration are managed by the ad server, and the client imports those resources into Terraform as existing AWS data objects.

The client-managed services are deployed into this private network boundary. Access between services is controlled through security groups, IAM roles, service permissions, VPC endpoints, and private networking patterns.

## 3. The client Data Warehouse

The client uses Postgres, S3, Athena, Apache Iceberg tables, Glue Catalog, and Lake Formation as its data warehouse and analytical data platform.

Postgres stores relational platform data, including users, organizations, ad accounts, campaigns, ad sets, ads, configuration state, and aggregated reporting outputs. It is the source of truth for core the client configuration and entity state.

S3 stores raw and semi-processed data, including impression-level delivery data, event data from web pixels and app pixels, vendor fee data, and other raw or partner-provided data sources.

Athena is used to query datasets prepared in S3. Iceberg tables provide table-level structure over S3-backed datasets, including schema management and analytical access patterns. Lake Formation governs data lake permissions across Glue Catalog databases and tables.

## 4. Platform Entry Points

The client has multiple controlled entry points into the platform. These entry points support event ingestion, campaign management, application usage, developer workflows, and static UI delivery.

## 4a. Event API And Data Ingestion

The client’s event ingestion API receives raw conversion and event data from external systems. These events can later be attributed to ads, impressions, campaigns, ad sets, and other client entities.

The client also has a dedicated Kinesis stream for impression-level data coming from the DSP. This path is important for raw delivery and win-log style data that later supports reporting, attribution, warehouse processing, and bidder analysis.

Data may enter the client through direct S3 batch delivery, streaming ingestion through Kinesis, or event ingestion APIs.

## 4b. Backend API And Developer API

The backend API and developer API are the primary programmatic interfaces for creating and managing campaign objects in the client.

These APIs read from and write to Postgres, which stores core campaign configuration and entity state. They also support workflows that involve S3 uploads, event publishing, asynchronous processing, and longer-running platform actions such as reporting jobs or downstream syncs.

## 4c. The client User Interfaces

The client operates several user interfaces on top of the platform APIs.

Ads Manager is the customer-facing interface for creating and managing advertising campaigns. The developer portal supports API discovery, documentation, and credential management. The admin panel is an internal the client's parent company/the client interface used to inspect accounts, manage controls, review account state, and perform operational actions such as spend locks or account checks.

## 4d. CDN And Static Assets

The client serves UI assets through a CDN backed by S3. This supports delivery of static frontend assets for the customer-facing and internal user interfaces.

The CDN layer is separate from the backend APIs, which handle authenticated application behavior and data access.

## 5a. The client Background Jobs

The client background jobs handle asynchronous work that should not run directly in customer-facing request paths.

These jobs support interactions with the DSP, billing workflows, customer segment processing, reporting workflows, delivery syncs, and other long-running platform operations. Background services may read from Postgres, write to S3, call external integrations, consume queues, and update platform state.

## 5b. The client Events

The client uses cron-based and queue-based event flows to trigger asynchronous processing.

Events can be generated by platform activity, scheduled workflows, ingestion processes, or API-driven actions. These events are routed to background services that perform work outside the synchronous API request lifecycle.

This means some platform updates may be created through an API first, then later synchronized, enriched, attributed, aggregated, or reflected in reporting through asynchronous jobs.

## 6. Third-Party Integrations

The client depends on several external systems and partner platforms. Key integrations include the DSP for ad delivery, the web-attribution provider for web event and attribution workflows, Stripe for billing-related flows, and the ad server-managed infrastructure or data sources.

The DSP is especially important because the client campaign configuration is synced downstream for delivery, while impression-level and win-log data flows back into the client’s data platform.

The client stores its own internal UUIDs for core entities. For the client objects that also exist in the DSP, the client stores the DSP object ID in the client object’s `external_id` field and stores the client UUID in the DSP as `alt_id`. This creates a direct bridge between the client and DSP identity spaces.

Raw DSP logs may contain downstream integer IDs such as `campaign_id`, `line_item_id`, `creative_id`, and `account_id`. Those IDs should not be treated as client UUIDs without mapping.

## 7. The client Data Jobs

client data jobs are implemented through a combination of AWS Glue and MWAA/Airflow workflows. The infrastructure for these jobs is managed outside the core platform infrastructure, but their outputs are central to reporting, attribution, and analytics.

These jobs collect raw impression-level data and prepare governed datasets in S3, including Athena-accessible Iceberg tables where appropriate. They also support the client’s asynchronous reporting engine and produce aggregated reporting data that is written back to Postgres for dashboard and customer-facing reporting.

Data jobs also process event data, perform attribution at the impression level where possible, and write attribution outputs to both Postgres and Athena-accessible warehouse tables. Attribution outputs may support different lookback windows, such as 7-day, 14-day, and 30-day views.

The existing data team pipelines and prepared warehouse datasets are expected to provide the foundation for advanced bidder analysis, including training data, feature engineering, historical delivery analysis, attribution joins, and feedback loops into optimization workflows.

## 8. Secrets And Key Management

The client uses AWS Secrets Manager and KMS to manage secrets, credentials, encryption keys, and sensitive service configuration.

Secrets are used by APIs, background jobs, data jobs, and integrations that need controlled access to databases, third-party platforms, queues, buckets, or encrypted data. KMS supports encryption and controlled decryption for sensitive resources and service workflows.

Access to secrets and encrypted data is governed through IAM roles, service-specific permissions, and AWS-managed authorization boundaries.

## 9. Monitoring And Observability

The client uses CloudWatch alerts, Slack notifications, and Datadog APM for monitoring, observability, and tracing.

CloudWatch provides infrastructure and service-level alarms. Slack notifications support operational alerting. Datadog APM provides application tracing and runtime visibility across APIs, background jobs, and other services.

These observability systems help monitor ingestion delays, job failures, service errors, sync issues, data freshness, attribution delays, and operational health across the client platform.


## Infrastructure Tagging And Naming Recommendations

The advanced bidder infrastructure will most likely live in a separate AWS account from the core the client platform. As a result, bidder compute, storage, networking, IAM roles, monitoring, and deployment workflows will likely be managed independently from the client’s primary application infrastructure.

The client’s existing infrastructure conventions are included here as context for integration planning, operational alignment, and data access design. They are not intended to prescribe how the bidder account must be implemented.

Within the client’s AWS environment, infrastructure is managed with Terraform, deployed through CI/CD, tagged for ownership and environment, and governed through IAM, security groups, KMS, Secrets Manager, and Lake Formation. The client uses private networking, controlled data ingress/egress paths, and governed warehouse access for sensitive datasets.

For bidder integration, the main architectural concern is the boundary between the client account and the bidder account. The client will need controlled mechanisms to share delivery-relevant state, curated datasets, attribution outputs, and performance feedback across that boundary. Depending on the final design, this may involve cross-account IAM roles, Lake Formation sharing, S3 replication or export buckets, event streams, APIs, or other approved transfer mechanisms.

The important distinction is that the client remains the source of truth for campaign configuration, delivery eligibility, attribution logic, and governed warehouse outputs, while the bidder account operates its own infrastructure for model execution, decisioning, experimentation, and bidder-specific processing.

Common the client tagging fields include:

- `Organization`: owning organization, such as `UA`
- `Owner`: responsible engineering or data owner
- `ENV`: environment, such as `DEV`, `STG`, or `PROD`
- `Project`: project or platform name
- `Application`: application or business capability
- `Service`: AWS service or logical service area
- `Entity`: resource category, dataset, job, API, queue, or delivery component
- `Description`: short human-readable purpose

The client resource names commonly include the environment, project, service, and resource purpose where practical. Existing patterns include examples such as:

```
SG-<ENV>-<Project>-<Service>
TFCI-<ENV>-<Project>
<region-prefix>-<env>-<project>-<dataset-or-service>
```

For advanced bidder integration, similar tagging concepts may be useful for distinguishing resources involved in cross-account data sharing, curated bidder datasets, delivery-control feeds, attribution outputs, monitoring, and operational ownership.

The main goal is alignment at the integration boundary: both the client and the bidder environment should be able to clearly identify which resources support data exchange, delivery-state synchronization, reporting feedback, and model-training workflows.

## Advanced Bidder Data Flow Context

The advanced bidder work connects campaign configuration, delivery data, event data, attribution, and warehouse outputs.

At a high level:

- Campaign configuration is created in the client and stored in Postgres.
- The client syncs eligible delivery configuration to the DSP.
- The DSP produces impression-level delivery and win-log data.
- Raw delivery data lands in S3 through Kinesis and batch ingestion paths.
- Web, app, and partner conversion events enter through the client event ingestion APIs or raw data feeds.
- Glue and MWAA jobs prepare warehouse datasets in S3, Athena, Iceberg, and Lake Formation.
- Attribution and reporting outputs are written to Athena-accessible datasets and, where needed, Postgres aggregates.

## Advanced Bidder Data Needs And Prepared Datasets

The advanced bidder work will require multiple categories of client data, but those categories do not all have the same latency, grain, or operational purpose. The client should treat delivery-control data separately from historical training data and reporting data.

The bidder integration is expected to use curated outputs prepared by the client rather than direct reads from internal production tables or raw warehouse locations. The client can use its existing systems of record, raw logs, attribution jobs, and reporting pipelines to prepare bidder-facing datasets on a defined cadence. This keeps the bidder integration decoupled from internal schema changes while giving the client control over data quality, identity mapping, attribution rules, privacy boundaries, and access governance.

### Delivery-Control Data

Delivery-control and pacing data is the most time-sensitive category. It includes the campaign, ad set, ad, creative, targeting, budget, override, spend, and impression state needed to determine whether the bidder should actively bid and how aggressively it should pace delivery.

This data needs to move quickly because user, admin, and delivery-system changes can immediately affect eligibility or pacing. If a campaign or ad set is paused in the client, archived, outside its flight dates, budget constrained, disabled through an override, or pacing ahead/behind target, the bidder needs that state soon enough to adjust or stop bidding on affected traffic.

Examples of delivery-control and pacing inputs include:

- Campaign status and archive state
- Ad set status and archive state
- Ad and creative eligibility
- Budget and pacing configuration
- Current spend
- Current impressions
- Spend locks or administrative delivery disables
- Targeting details:
    - Flight start and end dates
    - Delivery overrides
    - Publisher exclusions
    - Included deal IDs / inventory
    - Bid modifier configuration
    - Pacing type
    - Audience segments
    - Geos
    - Content genres
- Dynamic creative rotation settings
- Creative rotation weights

This feed is different from a daily warehouse extract. It is closer to a control-plane and pacing feedback sync between the client and the bidder environment. The target cadence and implementation details are still to be determined.

### Performance And Delivery Feedback Data

Performance and delivery feedback data connects bidder decisions to actual delivery outcomes. This data is related to pacing data, but it is broader than the fast delivery-control feed. It supports bidder evaluation, diagnostics, optimization analysis, and model feedback.

Relevant inputs include impression counts, spend, bids, wins, win price, bid price, supply metadata, app or site metadata, deal information, device and geo fields, bid shading metadata, model metadata, and delivery diagnostics. Raw DSP delivery and win-log data is an important input here, especially data arriving through Kinesis and S3.

Some spend and impression metrics may need to be included in the faster delivery-control. More detailed performance and delivery feedback can be prepared separately at a lower cadence, depending on source freshness and reporting needs.

Example source datasets may include:

- Impression-level data
- Vendor fee and cost datasets
- Hourly reporting aggregates

Cost and spend fields need explicit normalization before they are shared as bidder-ready data. Raw log values may be stored in micros or downstream-specific units, while reporting outputs may use normalized currency values.

### Measurement, Conversion, And Attribution Data

Measurement and attribution data provides the labels and outcomes needed for model training, bidder evaluation, and longer-term optimization. This includes web events, app events, partner conversion events, the web-attribution provider attribution data, and the client attribution outputs.

This data is generally less time-sensitive than delivery-control and pacing data. Conversion events and attribution results may arrive later than delivery data because attribution windows can remain open for several days.

Relevant source datasets may include:

- The web-attribution provider pixel events
- App event data
- Other Partner conversion events
- `gold_kochava_seven_day_attribution`
- `gold_kochava_fourteen_day_attribution`
- `gold_kochava_thirty_day_attribution`
- etc.

Attribution data arrives later than delivery data because conversion windows can remain open for several days. For this reason, bidder training datasets may need both early feedback datasets and later finalized attribution snapshots.

### Bidder-Prepared Datasets

A practical dataset split could include:

- **Delivery-control feed:** low-latency campaign, ad set, ad, creative, budget, status, targeting, and override state.
- **Impression-level training dataset:** joined delivery, campaign, ad set, ad, creative, supply, bid, win, spend, and event outcome data.
- **Attribution labels dataset:** conversion and attribution outputs joined back to impressions, ads, ad sets, campaigns, and attribution windows.
- **Aggregate performance dataset:** hourly or daily rollups for pacing, reporting validation, spend reconciliation, and optimization analysis.
- **Bidder response dataset:** bidder decisions and model outputs returned from the bidder environment to the client.

The bidder response dataset is important because the client will need visibility into how the bidder made decisions and how those decisions performed. Depending on the final integration, this may include auction/request IDs, the client and DSP IDs, bid/no-bid decision, bid price, model version, decision timestamp, latency, no-bid reason, and selected optimization strategy.

### Identity Mapping Requirements

The unified bidder datasets need to make identity mapping explicit. client UUIDs, DSP IDs, and raw log IDs should be included as separate fields with clear names.

### Cadence Expectations

The cadence should vary by data type.

- **Immediate or event-driven:** delivery eligibility changes such as pause, archive, spend lock, delivery disable, critical override changes, and budget-related stop conditions.
- **Frequent or near-real-time:** active delivery settings, bid configuration, targeting eligibility, deal inclusion/exclusion, and creative eligibility.
- **Hourly:** delivery metrics, spend, impressions, clicks, win rate, bid/win diagnostics, and aggregate performance feedback.
- **Daily:** attributed conversions, finalized reporting views, training labels, and model feature snapshots.
- **Weekly or backfill-based:** large historical training sets, attribution reprocessing, feature rebuilds, and model experiment datasets.
