# Performance Testing Strategy

[Performance Testing Strategy [1](#performance-testing-strategy)](#performance-testing-strategy)

[Purpose [1](#purpose)](#purpose)

[Requirements [1](#requirements)](#requirements)

[Workload Conditions and Assumptions [1](#_Toc1437570934)](#_Toc1437570934)

[Performance Testing Types [2](#performance-testing-types)](#performance-testing-types)

[Scenario Execution Approach [2](#scenario-execution-approach)](#scenario-execution-approach)

[Metrics to Collect [3](#metrics-to-collect)](#metrics-to-collect)

[Acceptance Criteria [4](#acceptance-criteria)](#acceptance-criteria)

## Purpose

The Performance Testing Strategy defines the approach for validating the performance, scalability, stability, and reliability of the Traffic Shaping / Bid Processing solution.

The system receives high-volume bid requests over HTTP using protobuf. Each bid request can contain multiple ad candidates. Candidate processing includes retrieval of pacing information, ML prediction, bid calculation and response generation.

The strategy focuses on the performance characteristics of:

1.  Online bid processing.

2.  Candidate-level processing.

3.  ML serving.

4.  Pacing-state access and updates.

5.  Infrastructure and scaling behavior.

## Requirements

The current primary performance requirements are:

|    **Requirement**     | **Target**      |
|:----------------------:|-----------------|
| Bid request throughput | 1M requests/sec |
|      E2E latency       | p99 ≤ 10 ms     |
| ML prediction latency  | p99 ≤ 3 ms      |

<span id="_Toc1437570934" class="anchor"></span>Workload Conditions and Assumptions

| **Condition / Assumption** | **Current Value** | **Comment** |
|:--:|----|----|
| Candidates per bid request | 10 | Initial assumption until production statistics are available |
| ML predictions per candidate | 1 |  |
| Request protocol | HTTP POST / protobuf |  |
| ML serving implementation | CPU-based GBDT exported to ONNX |  |
| Candidate-count distribution |  | TBD from production statistics |
| Payload-size distribution |  | TBD from production statistics |
| Maximum practical candidate count |  | To be determined through stress testing |

## Performance Testing Types

Testing types represent different **load profiles**. Specific scenarios are executed within these profiles.

| **Testing Type** | **Load Profile** | **Objective** |
|:--:|----|----|
| **Baseline / Latency** | Low and stable workload | Establish reference latency and resource consumption |
| **Load** | Gradual increase to expected/target load, then sustained traffic | Validate production workload and SLOs |
| **Stress** | Progressive increase beyond target load | Identify saturation and degradation points |
| **Spike** | Abrupt increase/decrease in traffic | Validate burst handling and recovery |
| **Soak / Endurance** | Sustained workload over an extended period | Detect long-term performance degradation |
| **Scalability / Capacity** | Same workload with different resource/replica configurations | Determine capacity per instance and scaling efficiency |
| **Degraded-Mode Performance** | Normal/high load combined with controlled degradation | Validate performance when dependencies/resources are impaired |

## Scenario Execution Approach

Performance tests must produce repeatable results and distinguish warm-up effects from steady-state behavior.

For standard performance scenarios, **one warm-up run** will be executed first, followed by **10 measured runs** using the same configuration.

The warm-up run allows model/runtime initialization, connection establishment, cache population, memory allocation and other startup effects to stabilize.

For long-running or infrastructure-intensive scenarios such as soak or full-scale stress testing, fewer repetitions may be used where ten repetitions are operationally impractical. The warm-up principle remains mandatory and any deviation must be documented.

**Cold-start behavior is out of scope and should be tested separately.**

The standard execution flow is the following:

1.  Deploy or reset the target SUT version

2.  Validate environment and monitoring readiness

3.  Initialize representative test data

4.  Execute one warm-up run

5.  Execute 10 measured runs

6.  Validate load-generator health

7.  Collect application, ML, infrastructure, and load-generator metrics

8.  Validate each measured run against performance gates

9.  Compare results across runs and against the approved baseline

10. Publish consolidated performance results

## Metrics to Collect

The following metrics should be collected for each performance test run:

- p99 latency

- CPU utilization

- Memory utilization

- Error rate

- Replica count

- OOM events

- Network throughput

- Network errors / dropped packets

- Rejected / dropped requests

p99 should be evaluated separately for each measured run. Percentile values from different runs should not be averaged.

If an aggregated p99 across multiple runs is required, it should be calculated from the combined raw latency samples or from mergeable histogram data.

For the 10 measured runs, the following should be checked:

1.  Number of runs that passed the p99 threshold

2.  Minimum and maximum p99 across runs

3.  Median p99 across runs

4.  Variability between runs

## Acceptance Criteria

A performance test run is considered valid and successful when all applicable criteria are met:

- **E2E p99 latency ≤ 10 ms**

- **ML prediction p99 ≤ 3 ms**

- Target workload is successfully generated and processed

- No OOM events occur

- No unexpected pod/container restarts occur

- No significant network packet loss or network errors occur

- Rejected/dropped requests remain within the agreed threshold

- Technical error rate remains within the agreed threshold

- The system remains stable without continuous resource growth or degradation during the test

For the 10-run approach:

1.  Each measured run should be evaluated independently against the applicable acceptance criteria.

2.  The number of runs that pass/fail the p99 thresholds should be reported.

3.  Any failed run should be investigated rather than hidden by aggregation.

4.  Large variability between otherwise identical runs should be treated as a stability issue and investigated.

Environment
