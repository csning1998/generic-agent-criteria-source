# Sub-doc 90. GitOps and Observability (Argo CD / Flux / LGTM / OpenTelemetry)

Sections 2, 5, and 9 of `ENGINEERING_PRINCIPLES.md` are prerequisites for this file. The baseline date is 2026-08-18.

## Section 1. GitOps

1. **Repository as the Sole Desired State**. Desired state inside the cluster MUST come from Git only. A drift created by `kubectl apply`, `helm upgrade`, or a console click MUST be repaired by changing Git. Changing the cluster to match the console is forbidden. Section 2 Item B of `ENGINEERING_PRINCIPLES.md` applies.

2. **Prerequisite for Auto-pruning**. Before prune is enabled, the executing Agent MUST confirm that no resource inside the managed range is owned by another mechanism. The range MUST be explicit (a label selector or a namespace allow-list). A default that matches the whole cluster is forbidden.

3. **Application and Infrastructure Layering**. Cluster components (CNI, CSI, controllers, Operators) and application workloads MUST belong to different sync units. The application layer is downstream of the infrastructure layer. Section 1 Item B of `ENGINEERING_PRINCIPLES.md` applies.

4. **Secrets Do Not Enter Git**. Cleartext secret material MUST NOT enter Git. Accepted forms are an external secret reference (VSO, External Secrets, or SOPS ciphertext that a controller decrypts). Which form the repository uses is an architecture decision.

5. **Environment Differences**. An environment difference MUST be an overlay or a values file. A branch MUST NOT express an environment. A branch per environment breaks linear history. Section 9 Item A of `ENGINEERING_PRINCIPLES.md` applies.

6. **Controller Self-bootstrap**. The deploy of a GitOps controller MUST NOT be owned only by that same controller. That edge is a cycle. Section 1 Item B of `ENGINEERING_PRINCIPLES.md` applies. The bootstrap path MUST exist outside that controller.

## Section 2. Observability Data

1. **Telemetry Collection Is Downstream**. A collector (Alloy, OpenTelemetry Collector, or an exporter) reads the workload. That collector MUST NOT change the state of the observed system.

2. **Independent Audit Path**. Observability storage MUST NOT sit in the failure domain of the observed system. Section 9 Item B of `ENGINEERING_PRINCIPLES.md` applies. Storage that monitors a cluster MUST live outside that cluster, or MUST have a replica that does not depend on that cluster.

3. **Label Contract**. Correlation among metrics, logs, and traces depends on shared labels (`namespace`, `service`, `pod`, `trace_id`). That label set is a global naming contract. Section 4 Item B of `ENGINEERING_PRINCIPLES.md` applies. Those labels MUST match the architecture decisions. Each component MUST NOT invent its own set.

4. **Cardinality Control**. A high-cardinality label (a user ID, a request ID, or a full URL) MUST NOT be a metric label. That information belongs on a trace or a log.

## Section 3. LGTM Components

1. **Licensing**. Grafana, Loki, and Tempo have used AGPLv3 since 2021-04. When the plan is to modify the source and offer the result as a network service, a compliance judgment MUST finish first.

    Official source URL is <https://grafana.com/blog/grafana-loki-tempo-relicensing-to-agplv3/>

2. **Version Behavior**. Mimir 3.0 shipped in 2025-11 and split the read path from the write path. Loki 3.x added structured metadata and native OpenTelemetry support, and the Helm chart moved to a separate community repository. Before the executing Agent writes a setting, the executing Agent MUST verify the component topology and the chart source of the target version.

    Official source URL is <https://grafana.com/docs/>

3. **Object Storage Dependency**. Loki, Tempo, and Mimir use object storage as the durable tier. That object storage follows Section 5 of `80-stateful-and-quorum.md` and is upstream of those three components.

4. **Dashboards and Alerts as Code**. A dashboard and an alert rule MUST be defined as code and MUST be in version control. A dashboard created by hand in the UI MUST NOT be a long-term asset. Section 9 Item A of `ENGINEERING_PRINCIPLES.md` applies.

## Section 4. OpenTelemetry

1. **Explicit Collector Configuration**. A pipeline (receiver, processor, exporter) MUST be declared in full. A default pipeline is forbidden.

2. **Centralized Sampling Decisions**. A sampling strategy MUST be decided in one place and MUST be recorded. Each service MUST NOT implement its own sampling. Section 5 Item A of `ENGINEERING_PRINCIPLES.md` applies.

3. **Semantic Conventions**. Attribute names MUST follow OpenTelemetry semantic conventions. A custom attribute MUST have a dedicated prefix and MUST be registered in the architecture-decision file.

## Section 5. Alerting

1. **Alert Maps to Action**. Each alert MUST map to one concrete human action. An alert with no action MUST be deleted or MUST be reduced to a dashboard metric.

2. **Dependency-based Suppression**. An upstream alert MUST suppress the chained downstream alerts. A suppression rule is part of the DAG. Section 1 Item B of `ENGINEERING_PRINCIPLES.md` applies. That rule MUST match the real dependency.
