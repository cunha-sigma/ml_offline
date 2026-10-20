# testing_estimate.xlsx

Converted from `testing/testing_estimate.xlsx` (sheet: "Estimation of TA solu"). Hours per item.

| Estimation of TA solution creation with/without AI harness |  |  |  |  |  |  |  |
|---|---|---|---|---|---|---|---|
|  | Without AI harness |  |  | With AI harness |  |  | Comment |
|  | Optimistic | Most likely | Pessimistic | Optimistic | Most likely | Pessimistic |  |
| 1. Requirements analysis |  |  |  |  |  |  |  |
| 1.1 Requirements review/ testing | 2 | 3 | 4 | 0.1 | 0.25 | 0.5 | Optimistic column represents S size documentation analysis, Most likely - M size, Pessimistic - L size and bigger. |
| 1.2 Requirement analysis > artefact review | - | - | - | 0.5 | 1 | 1.5 | This is applicable only for AI supported process. The artefact represents the .md or html file with the results of the requirements review, performed by AI agent. It can contain questions for clarification, inconsistencies, conclusions. Human needs to look through it carefully and make decision. |
| 1.3 Questions clarification | 0.5 | 1 | 2 | 0.5 | 1 | 2 | The estimate is the same for both AI/non-AI supported process since in scope of this task QA engineer should clarify the questions, collected during Requirements review/AI-artefact review, with DEV/Product team. |
| 1 TOTAL: | 2.5 | 4 | 6 | 1.1 | 2.25 | 4 |  |
| 2. Test Design |  |  |  |  |  |  |  |
| 2.1 Test design (scenarios preparation and documenting) | 4 | 6 | 8 | 0.25 | 0.5 | 0.75 | Optimistic column represents test design estimate for feature S size. Most likely column contains estimate for feature M size, Pessimistic - for L size accordingly. |
| 2.3 Test scenarios review | 1 | 2 | 3 | 0.5 | 1 | 1.5 | Manually check the scenarios correctness. In case of AI, QA Engineer checks the prepared flows match to expected system behaviour, according to the Requirements analysis artefact. The estimate contains 2 review sessions including comments addressing. |
| 2 TOTAL: | 5 | 8 | 11 | 0.75 | 1.5 | 2.25 |  |
| 3. TA solution architecture, tests implementation |  |  |  |  |  |  |  |
| 3.1 Core Framework setup (structure, configuration management, environment configuration, fixtures, reporting) | 8 | 10 | 12 | 4 | 6 | 8 | In scope: the TA solution creation with or without AI help. Out of scope: AI harness setup |
| 3.2 API base client class implementation | 0.5 | 0.5 | 0.5 | 0.25 | 0.25 | 0.25 |  |
| 3.3 API client implementation (inherits base API client class) | 0.25 | 0.5 | 0.75 | 0.1 | 0.2 | 0.3 | Optimistic column represents API client class implementation for feature S size, Most likely - for feature M size, Pessimistic - for feature L size. |
| 3.4 One API test implementation (including debugging) | 0.5 | 0.5 | 0.75 | 0.1 | 0.2 | 0.3 |  |
| 3.5 One API contract schema creation | 0.25 | 0.5 | 0.75 | 0.1 | 0.1 | 0.2 |  |
| 3.6 One Page Object creation (including locators description, methods creation) | 0.5 | 1 | 1.5 | 0.1 | 0.25 | 0.5 | Optimistic column represents Page Object implementation for page S size, Most likely - for page M size, Pessimistic - for page L size. |
| 3.7 Code review | 0.5 | 1 | 1.5 | 0.25 | 0.5 | 0.75 | Most likely contains 2 review sessions, Pessimistic - 3 review sessions |
| 3.9 Code review comments fixing | 0.5 | 1 | 1.5 | 0.1 | 0.25 | 0.5 | Estimate depends on the changes complexity (naming, minor changes can be applied faster, architectural changes can take more time) |
| 3.8 Test CI/CD pipeline creation | 6 | 8 | 10 | 0.25 | 0.5 | 1 |  |
| 3 TOTAL: | 17 | 23 | 29.25 | 5.25 | 8.25 | 11.8 |  |
| 4. Failure analysis, solution maintenance |  |  |  |  |  |  |  |
| 4.1 Failures analysis in the pipeline (including the root cause definition/analysis, tracking, issue reporting) | 0.5 | 1 | 1.5 | 0.25 | 0.5 | 0.5 | The estimate represents time spent on one failed test analysis/processing, optimistic column shows time for trivial failure processing, Most likely describes middle-complex case, pessimistic - when the failure is flaky or isn’t reproduced on local machine. |
| 4 TOTAL: | 0.5 | 1 | 1.5 | 0.25 | 0.5 | 0.5 |  |
