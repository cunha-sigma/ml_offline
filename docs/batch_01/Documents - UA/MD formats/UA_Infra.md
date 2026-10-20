# UA Infra


This document covers the UA Ads Manager AWS infrastructure across two related areas:

- Core application infrastructure
- Data jobs infrastructure

All application-level infrastructure is managed with Terraform to keep environments reproducible, reviewable, and version controlled.

## Repositories

| Area | Repository | Purpose |
| --- | --- | --- |
| Core infra | [UA Infra](https://github.freewheel.tv/connective/ua-infra) | VPC integration, ECS, RDS, S3, WAF, deployment pipelines, app IAM, and shared Terraform modules |
| Data jobs infra | [UA Data Jobs](https://github.freewheel.tv/connective/ua-data-jobs) | Airflow/MWAA, Glue, Athena, Iceberg tables, Lake Formation, data buckets, and data-job CI/CD |

## Core Infrastructure

The core infrastructure repository owns the AWS resources required to run the UA Ads Manager application stack.

### Networking

The stack uses an existing VPC and subnet layout. Terraform consumes those foundational resources through data sources and manages the application networking layered on top.

Core networking includes:

- VPC and subnet references
- Public and private subnet usage
- Security groups for ECS services, jobs, RDS, Glue, and supporting components
- Public or private load balancers depending on the workload
- Route53 records
- ACM certificates
- WAF rules and associations
- GitHub/CodeStar connection networking for deployment pipelines

RDS remains private. New workloads should be granted database access by adding their security group to the RDS security group ingress rules on port `5432`.

### ECS and Application Compute

Application workloads run on ECS/Fargate.

Core ECS infrastructure includes:

- ECS clusters
- ECS services
- ECS task definitions
- Scheduled or one-off ECS task jobs
- Service-specific task roles
- Task execution roles
- CloudWatch log groups
- ECR repositories
- Load balancers, target groups, listeners, and health checks

Each service should have a dedicated IAM task role with the minimum permissions required by that service.

### RDS / Postgres

Postgres is hosted on RDS and managed through Terraform.

Terraform manages:

- RDS instance configuration
- Subnet groups
- Security groups
- Backup settings
- Multi-AZ behavior
- Storage configuration
- Read replica settings where applicable

Access is controlled through:

- Network permissions via security groups
- Runtime credentials via Secrets Manager or the existing ECS secret pattern

### Deployment Pipeline

Core application deployments use AWS developer tooling:

- CodePipeline for orchestration
- CodeBuild for Docker image builds
- CodeDeploy for ECS deployments
- ECR for container images
- GitHub/CodeStar connections for source integration

Deployment roles should remain separate from runtime task roles.

## Data Jobs Infrastructure

The data jobs repository owns the infrastructure used by Airflow DAGs, Glue jobs, Athena queries, crawlers, Iceberg tables, and Lake Formation permissions.

### Airflow / MWAA

MWAA runs the Airflow DAGs from the data jobs repository.

Terraform manages:

- MWAA environments
- MWAA execution roles
- DAG storage
- Requirements/startup script storage
- MWAA networking
- Environment-specific Airflow variables

MWAA still depends on core infra for RDS connectivity. After MWAA is deployed, its security group must be allowed inbound to the RDS security group on port `5432`.

### Glue Jobs and Crawlers

Data jobs Terraform manages:

- Glue ETL jobs
- Glue crawlers
- The reporting Glue catalog database
- ETL script uploads
- Job-specific IAM policies

Current data processing areas include:

- Win logs
- App events
- Graph data
- Kochava attribution
- Tooling and backfill jobs

### Athena and Iceberg Tables

Athena is the query layer for the data lake.

Terraform manages:

- Athena workgroups
- Athena query result buckets
- Iceberg table DDL synchronization
- Reporting database tables

Application services that query Athena need permissions for:

- Athena query execution
- Athena result bucket access
- Glue catalog reads
- Lake Formation access when tables are governed
- Any required S3 prefixes

### Lake Formation and IAM

Lake Formation controls access to governed data lake resources.

IAM alone is not sufficient for workloads querying governed Athena tables. A principal generally needs:

- IAM permissions for Athena
- IAM permissions for Glue catalog reads
- IAM permissions for Athena result S3 locations
- `lakeformation:GetDataAccess`
- Lake Formation grants on the database and tables

Lake Formation principals should be static, known IAM role ARNs.

## Custom Customer Ad Bidder Infrastructure

The custom customer ad bidder should be managed separately from the shared core infrastructure. It should have its own Terraform ownership boundary, even if it consumes shared resources such as the VPC, Postgres, or Athena datasets.

The bidder stack should not be embedded directly into the shared `ua-infra` core application stack unless there is a strong reason to couple the lifecycle.

### Purpose

The custom bidder infrastructure exists to support customer-specific bidding workloads without tightly coupling them to shared UA Ads Manager application services.

It should provide isolation for:

- Deployment lifecycle
- IAM permissions
- Runtime configuration
- Customer-specific scaling needs
- Customer-specific data access
- Operational ownership

### Expected Infrastructure

The custom bidder stack should define:

- Dedicated EKS cluster
- Dedicated ECR repository
- Dedicated deployment pipeline
- Dedicated IAM roles
- Dedicated security group
- Private subnet placement unless public ingress is required
- CloudWatch logging
- Secrets Manager configuration
- Customer-specific tags and naming
    - No strict requirement on our side

The bidder may still reference shared infrastructure through stable IDs or remote outputs, including:

- VPC ID
- Private subnet IDs
- RDS endpoint or secret reference
- RDS security group ID
- Athena workgroup
- Glue database/table names
- S3 bucket ARNs or prefixes

### Postgres Access

The bidder will need Postgres connectivity.

Required infra work:

- Add the bidder security group to RDS ingress on port `5432`
- Keep RDS private
- Use bidder-specific database credentials
- Store database connection values in Secrets Manager
- Avoid sharing broad app credentials with the bidder

Because RDS is owned by core infra, the bidder stack should not attempt to own the RDS security group directly. Instead, coordinate a small core infra change that permits the bidder security group to connect.

### Athena Data Access

The bidder will also need access to Athena-backed data.

Required infra work:

- Identify required Athena workgroup
- Identify required Glue database and tables
- Grant Athena query permissions to the bidder task role
- Grant Glue catalog read permissions to the bidder task role
- Grant S3 access to Athena query result locations
- Add Lake Formation grants in the data jobs repo for governed tables
- Scope access to the smallest useful set of tables and prefixes

Because Athena, Glue, and Lake Formation are owned by data jobs infra, the bidder stack should consume those resources rather than owning or duplicating them.

### IAM Permission Management

IAM permission management is the main design consideration for the bidder.

The bidder role should be managed in Terraform and reviewed carefully because it may need access to:

- Postgres credentials
- Athena query execution
- Glue catalog metadata
- Athena result S3 locations
- Lake Formation-governed data
- CloudWatch logs
- KMS keys
- Secrets Manager secrets

Permissions should be scoped per customer, per table, and per S3 prefix wherever possible.

## Ownership Boundaries

Core infra, data jobs infra, and custom bidder infra should use separate Terraform ownership boundaries.

| Resource Type | Owner |
| --- | --- |
| Shared ECS application services/jobs | `ua-infra` |
| RDS and RDS security group | `ua-infra` |
| Shared app deployment pipelines | `ua-infra` |
| Shared app task IAM roles | `ua-infra` |
| MWAA / Airflow | `ua-data-jobs` |
| Glue jobs and crawlers | `ua-data-jobs` |
| Athena workgroups/results | `ua-data-jobs` |
| Iceberg tables | `ua-data-jobs` |
| Lake Formation grants | `ua-data-jobs` |
| Customer bidder EKS service | Custom bidder infra |
| Customer bidder deployment pipeline | Custom bidder infra |
| Customer bidder runtime IAM role | Custom bidder infra |
| Customer bidder security group | Custom bidder infra |

Cross-boundary dependencies should use stable IDs, ARNs, outputs, or documented handoffs rather than duplicating ownership.

## Operational Notes

- Keep the custom bidder isolated from shared core application infrastructure.
- Prefer security group references over broad CIDR ingress.
- Keep deployment roles separate from runtime roles.
- Keep data access least privilege.
- Coordinate cross-repo changes, especially RDS ingress and Lake Formation grants.
- Add new workloads by following existing Terraform module patterns.
