# Sub-doc 62. Service Mesh and Cluster Network

Sections 1, 5, and 8 of `ENGINEERING_PRINCIPLES.md` are prerequisites for this file. The baseline date is 2026-08-18.

## Section 1. Adoption Prerequisites

1. **Mesh Does Not Patch Application Defects**. A service mesh provides transport identity, encryption, and observability. A mesh retry, timeout, or circuit breaker MUST NOT hide an application-level correctness defect. That use violates Section 2 Item C of `ENGINEERING_PRINCIPLES.md`.

### Item B. Data Plane Mode Is an Architecture Decision

The choice between sidecar and ambient MUST be written in `planning/decisions.md`, and that entry MUST record the trade-off. Istio ambient mode is GA from 1.24. ztunnel handles L4 on the node (mTLS, L4 authorization, telemetry). A waypoint handles L7 at the namespace or the service. Ambient admission is a namespace label and does not restart a Pod. Sidecar admission restarts a Pod.

Official source URL is <https://istio.io/latest/docs/overview/dataplane-modes/>

One cluster MAY run both modes. The mix boundary MUST be recorded. The mix MUST NOT spread without a record.

1. **L7 Capability Enabled on Demand**. A waypoint MUST be created only in a namespace that needs L7 (HTTP routing, header authorization, or request-level metrics). A namespace that does not need L7 MUST NOT receive a waypoint, so that the failure surface stays small.

## Section 2. Identity

1. **Workload Identity Originates from the Platform**. An mTLS identity MUST be issued by the platform (an Istio SPIFFE ID, a Consul Connect service identity, or Vault PKI). An application-supplied certificate is forbidden. Section 5 Item A of `ENGINEERING_PRINCIPLES.md` applies.

2. **Authorization Default Deny**. An `AuthorizationPolicy` or an equivalent object MUST default to deny and MUST open each path one by one. Opening every path first and tightening later is forbidden.

3. **Division of Labor with NetworkPolicy**. L3/L4 isolation belongs to NetworkPolicy. Service-layer authorization belongs to the mesh. The two rule sets MUST NOT contradict each other. Each rule set MUST be reviewable on its own. Mesh authorization MUST NOT replace NetworkPolicy.

## Section 3. Traffic Configuration

1. **Single Source for Route Declaration**. The routes of one service MUST NOT be declared both as Gateway API resources and as vendor resources such as VirtualService. The repository MUST choose one form and MUST record that choice. In ambient mode, Gateway API is the documented path. Some vendor resources have weaker support in that mode.

2. **Explicit Timeout and Retry**. A timeout and a retry MUST be set explicitly, and the executing Agent MUST record the reason. An implementation default is forbidden. Section 5 Item B of `ENGINEERING_PRINCIPLES.md` applies. A retry MUST be bounded and MUST NOT apply to a non-idempotent method.

3. **Egress**. Egress MUST pass through a declared egress setting. Allowing an unknown destination as the normal case is forbidden.

## Section 4. Consul Connect

1. **ACL Prerequisite**. Before Connect is enabled, ACL MUST already default to `deny`. See Section 5 of `40-identity-and-secrets.md`.

2. **Intention as the Authorization Source**. Service-to-service authorization MUST be an intention in version control. An intention created by hand through the API MUST NOT be long-term state. Section 9 Item A of `ENGINEERING_PRINCIPLES.md` applies.

## Section 5. Upgrades

1. **Control Plane Before Data Plane**. A mesh control-plane upgrade MUST finish before the data-plane upgrade. The executing Agent MUST verify the cross-version compatibility window before stating that window.

2. **Data Plane Replacement**. A sidecar-mode data-plane upgrade restarts every admitted Pod. That time cost MUST enter the change plan. Section 7 Item C of `ENGINEERING_PRINCIPLES.md` applies. An ambient ztunnel upgrade affects the node and still MUST NOT cross a majority of failure domains in one step.
