# Engineering Principles (Infrastructure as Code and Platform Engineering)

This file is the expanded form of the collaboration rules. Grok does not load this file at session start. The file that Grok loads on every session is `~/.grok/rules/ENGINEERING_PRINCIPLES.md`.

The PreToolUse hook blocks only the static cases named in `99-hook-contract.md`. The PreToolUse hook does not inject this file into context.

This file states stack-neutral rules. Stack-specific rules live in the sibling files in this directory. The executing Agent MUST open a sibling file only when the current task matches that file.

---

## Section 0. Loading Protocol

### Item A. Always-loaded vs. On-demand

Grok loads `~/.grok/rules/ENGINEERING_PRINCIPLES.md` on every session.

The executing Agent MUST open `00-loading-protocol.md` before opening any other file in this directory. The executing Agent MUST then open only the sibling files that the routing table in `00-loading-protocol.md` selects for the current task.

The executing Agent MUST NOT open a sibling file whose stack the current task does not touch.

The SessionStart hook MUST NOT inject any file from this directory. The UserPromptSubmit hook MUST NOT inject any file from this directory.

### Item B. Timeliness Statement

Every version number, default, and deprecation claim in this directory carries a verification date. The baseline date is 2026-08-18.

Before the executing Agent states a versioned behavior, a CLI flag, an API version, a default, or a license term, the executing Agent MUST verify that claim against the current official document or the current release notes. Training data MUST NOT substitute for that verification. Context from an earlier session MUST NOT substitute for that verification.

When verification fails, the executing Agent MUST write the sentence `目前缺乏足夠的最新資訊` and MUST stop on the unverified claim. The executing Agent MUST NOT fill the gap with a guess.

Items that changed in 2025 and 2026, and that training data commonly misstates, are listed in `00-loading-protocol.md` under the high-volatility list.

---

## Section 1. Lifecycle Alignment

### Item A. Lifecycle Tier Alignment

A secret MUST share the lifecycle tier of the storage that the secret decrypts. A secret that decrypts durable data MUST NOT live in an ephemeral layer.

A layer is ephemeral when a rebuild of that layer does not require a data-migration procedure. An ephemeral layer MUST NOT hold the only material that decrypts durable data.

1. **Unidirectional DAG Consumption**. Dependencies MUST form a directed acyclic graph. A downstream layer MAY read an upstream output. An upstream layer MUST NOT write into a downstream layer. A layer MUST NOT assume that a peer that has not yet applied is already ready.

### Item C. Failure Domain and Quorum

A component that depends on majority vote (etcd, a Consul server, the DCS used by Patroni, Redis Sentinel, a MinIO erasure set) MUST declare the failure domain of each member in code. A majority of those members MUST NOT share one failure domain.

The failure-domain declaration MUST cover physical host, rack or hypervisor cluster, and availability zone. The placement rule MUST be readable in the declared configuration. Operator memory MUST NOT be the only record of that rule.

The member count MUST be odd. A membership change MUST add or remove one member per step. A single step MUST NOT replace a majority of members.

1. **State Storage Tiering**. Terraform state, a Vault storage backend, etcd data, and a database PGDATA directory are authoritative state. The backup of that state MUST live outside the resources that the state describes. The restore procedure MUST remain executable after those resources are gone.

---

## Section 2. Declarative Convergence and Pure Idempotency

1. **Zero Drift After N Runs**. After the declared configuration has been applied more than once, the second apply MUST report zero changes.

### Item B. Runtime Patching Rejected

When the declared configuration and the live system diverge, the executing Agent MUST change the declared source, or the executing Agent MUST assert and stop. Automation MUST NOT stamp a side effect onto the live system.

Forbidden actions include a Terraform `local-exec` or `remote-exec` provisioner that patches a field the provider does not manage, an Ansible `shell` or `command` task that replaces an existing idempotent module, and a `kubectl patch` after `helm install`.

1. **Fail-Fast**. On a state mismatch the executing Agent MUST assert and fail. A playbook or an IaC module MUST NOT probe the live system and then force a reset.

### Item D. The Sole Exception: Bounded Retry

The only retry that Item C permits is a cloud-provider delay that the provider documents as eventual consistency, such as IAM binding propagation. That retry MUST meet all four of the following conditions.

1. The retry count and the timeout are finite constants written in code.
2. The retry matches a documented error code or a documented error string. A catch-all retry is forbidden.
3. The code cites the provider document that describes the delay.
4. After the timeout the retry raises an error. The retry MUST NOT continue after a warning.

A retry that misses any of those four conditions violates Item C.

---

## Section 3. Generic Module Purity

1. **Zero Business Logic**. A generic module MUST declare resource structure only. A generic module MUST NOT contain a business-specific branch, a live-state lookup, or an automatic merge of caller-specific data.
2. **Context-Free**. A generic module MUST NOT hard-code an environment alias or a concrete provider address. The caller MUST pass credentials and context, or the caller MUST inherit those values through an explicit provider mapping.
3. **Product and Tenant Name Isolation**. A variable name, resource name, tag key, or output key inside a generic module MUST NOT contain a product name, a customer name, or a project code. Those names MAY appear only as values that the caller passes.

---

## Section 4. Interface Contracts over Hardcoded Scalars

1. **Object-based Interface**. A cross-layer input or output MUST be a structured object (a map or an object type). A scalar variable that names one service is forbidden. Adding a field MUST remain backward compatible.
2. **Semantic Consistency**. Global names and keys MUST match the names recorded in the architecture decisions. A leftover historical name is forbidden. A tautological binding that carries no meaning is forbidden.
3. **Explicit Type Constraints**. An input MUST declare a complete type. The type `any` is forbidden. An optional field MUST be marked optional and MUST state what the field means. An implicit default that applies when the caller omits the field is forbidden.

---

## Section 5. Single Source of Truth and Explicit Binding

1. **Single Authoritative Generator**. Each secret and each configuration item MUST have one owner that generates or mints that value. Every other component MUST subscribe or MUST read a reference.
2. **Explicit Binding**. An implicit variable override is forbidden. An undocumented default is forbidden. Every dependency MUST be readable in code.
3. **Cross-layer Reference via Declared Interface Only**. A cross-layer read MUST use a named interface (a remote-state output, a Consul KV path, or a Vault path). Deriving another layer's resource identifier by string concatenation is forbidden.

---

## Section 6. Immutability and Supply Chain

1. **Artifact Immutability**. A published artifact (an OCI image, a machine image, a Helm chart, a Terraform module version) MUST NOT be mutated in place. A fix MUST be a new version.
2. **Reference by Digest**. A production reference to an OCI artifact MUST pin a digest (`sha256:`). A tag MAY exist as a human-readable label. Resolution MUST use the digest. The PreToolUse hook does not enforce this rule.
3. **Lock File Version Control**. A dependency lock file MUST be in version control and MUST be reviewed. That set includes Terraform or OpenTofu `.terraform.lock.hcl`, Helm `Chart.lock`, pinned versions in Ansible `requirements.yml`, and a digest list for base container images. The PreToolUse hook does not block an edit to a lock file.
4. **Build and Runtime Separation**. A build stage MAY run imperative steps. A runtime stage MUST NOT. Installing a package after node boot violates Section 2 Item B.

---

## Section 7. Change Safety and Reversibility

1. **Plan Before Apply**. Every change MUST produce a plan and MUST wait for the owner to confirm that plan. Accepted plans include Terraform or OpenTofu `plan`, Ansible `--check --diff`, Kubernetes server-side dry-run, and Helm diff. Applying without a plan is forbidden.
2. **Explicit Destructive Operations**. When a plan contains a destroy, a replace, a data-volume delete, or a database parameter that forces a restart, the executing Agent MUST ask the owner for a separate confirmation. That step MUST NOT share an apply with ordinary changes.
3. **Blast Radius Cap**. One apply MUST NOT cover a majority of members across more than one failure domain. One apply MUST NOT cover both the control plane and the data plane.
4. **Recovery Path Before Change**. Before a change runs, a recovery path MUST already exist and MUST already have been tested. An irreversible change (an irreversible data-format upgrade) MUST wait for a restorable backup and MUST record the restore drill.

---

## Section 8. Identity and Least Privilege

1. **Long-lived Credential Prohibition**. A long-lived static credential MUST NOT live in code, in an image, or in a CI variable. Cross-system authentication MUST use a short-lived credential and a federated identity (OIDC, Workload Identity Federation, or a Kubernetes ServiceAccount token).
2. **Identity Bound to Workload**. A principal MUST bind to the smallest workload unit. A principal MUST NOT bind to a node. Two applications MUST NOT share one principal.
3. **Issuer and Consumer Separation**. The issuer (Vault, Keycloak, or cloud IAM) and the consumer MUST sit in different trust tiers. A consumer MUST NOT hold a grant that lets that consumer raise its own privilege.

---

## Section 9. Auditability

1. **Change Attributability**. Every infrastructure change MUST trace to one commit in version control. A change made through a human console, `kubectl edit`, or a manual `vault write` is an incident. The executing Agent MUST record that incident and MUST restore the change as code.
2. **Audit Path Must Not Be Controlled by the Audited Entity**. The destination of an audit log MUST NOT sit in the failure domain of the audited component. The identity of the audited component MUST NOT be able to delete that log.

---

## Section 10. Hook Operating Contract

The complete contract is `99-hook-contract.md` in this directory. The summary below MUST NOT weaken `99-hook-contract.md`.

When the current session will mutate `terraform/`, `ansible/`, `packer/`, or `planning/` under a repository whose name appears in `planning/architecture_<repo>*.md`, the executing Agent MUST first open `planning/decisions.md` and at least one matching `planning/architecture*.md` with the read-file tool. After those reads, the executing Agent MUST write the move check, the name check, the DAG check, and the in-scope check. A repository whose name does not appear in those architecture file names is outside this gate.

A mutation of `terraform/modules/` or `ansible/roles/utils_*` requires the owner phrase `leave generic module` in a prompt of the current session. After that phrase, the PreToolUse hook still denies a new environment alias, a tautological `vault = vault` map, and a product name inside the generic module.

A write to a `skill-module-*` path that bakes a collection UUID, an owner home path, the owner login, or a mapping table is denied. After that write, the Stop hook blocks the turn until the file is stateless.

The owner disables the hook by setting `ENGINEERING_PRINCIPLES_HOOK=0`.

---

## Routing Table (Summary)

| Work Touches                                              | Load                                   |
| --------------------------------------------------------- | -------------------------------------- |
| `terraform/`, `.tf`, `.tfvars`, state, provider           | `50-terraform.md`                      |
| `ansible/`, playbook, role, inventory                     | `51-ansible.md`                        |
| `packer/`, `vagrant/`, image building                     | `52-packer-vagrant.md`                 |
| Kubernetes manifest, Helm chart, kubeadm, MicroK8s, Talos | `60-kubernetes-and-helm.md`            |
| Podman, Docker, OCI, SELinux, Containerfile               | `61-container-runtime-and-selinux.md`  |
| Istio, Linkerd, Consul Connect, Gateway API               | `62-service-mesh-and-network.md`       |
| Vault, Consul ACL, Keycloak, OIDC, WIF, PKI               | `40-identity-and-secrets.md`           |
| GCP, GWS, GKE, AWS, Azure                                 | `70-cloud-providers.md`                |
| Libvirt, QEMU-KVM, vSphere, Nutanix                       | `71-virtualization-onprem.md`          |
| etcd, Patroni, Redis Sentinel, MinIO, Consul server       | `80-stateful-and-quorum.md`            |
| Argo CD, Flux, LGTM, Prometheus, OpenTelemetry            | `90-gitops-and-observability.md`       |

The column titled Load names the file that the executing Agent MUST open. The PreToolUse hook does not open those files.

The full routing table and the high-volatility list live in `00-loading-protocol.md` in this directory.

The citation list lives in `SOURCES.md` in this directory.
