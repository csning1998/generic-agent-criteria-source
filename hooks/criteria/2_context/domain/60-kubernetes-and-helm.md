# Sub-doc 60. Kubernetes and Helm (kubeadm / MicroK8s / Talos)

Sections 1 through 9 of `ENGINEERING_PRINCIPLES.md` apply to this file. The baseline date is 2026-08-18.

## Section 1. Version and Compatibility

1. **Support Window**. Kubernetes maintains release branches for the latest three minor versions. Before the executing Agent writes or edits a cluster setting, the executing Agent MUST confirm that the target version is still in support. On the baseline date, v1.36 shipped on 2026-04-22 and v1.37 is scheduled for 2026-08-26.

    Official source URL is <https://kubernetes.io/releases/>

2. **Removed Items**. Kubernetes v1.36 removed kube-proxy IPVS mode and the gitRepo volume plugin. A manifest or a cluster setting MUST NOT reference a removed item. Before the executing Agent uses an API version, the executing Agent MUST verify the status of that API version on the target cluster.

3. **Ingress-NGINX**. Ingress-NGINX was retired on 2026-03-24. After that date there is no new release and no security patch. An existing deploy MAY keep running. Ingress-NGINX MUST NOT be an option in a new design. The replacement MUST be written in `planning/decisions.md`.

    Official source URL is <https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/>

## Section 2. Cluster Topology

1. **Control Plane Quorum**. Control-plane nodes and embedded etcd follow Section 1 Item C of `ENGINEERING_PRINCIPLES.md`. etcd-specific rules live in `80-stateful-and-quorum.md`.

2. **Nodes Are Not State Containers**. A node follows Section 6 of `ENGINEERING_PRINCIPLES.md`. State that must survive MUST live on a PersistentVolume or outside the cluster. A node MUST be destroyable and rebuildable without a data move.

### Item C. Distribution Differences

kubeadm. Cluster settings MUST be declared in `ClusterConfiguration` and `KubeletConfiguration` files, and those files MUST be in version control. A `kubeadm init` command-line flag MUST NOT be the only source of a setting.

MicroK8s. The enablement state of an addon MUST be declared. The history of `microk8s enable` MUST NOT be the source of a setting.

Talos. Every setting comes from one machine-config document. Talos has no SSH, no shell, and no package manager. Management MUST use talosctl and the gRPC API with mTLS. The STATE partition stores the machine config and TLS material. The EPHEMERAL partition is rebuildable. A Talos node therefore already satisfies Item B. A procedure that tries to obtain a shell on Talos is forbidden.

Official source URL is <https://www.talos.dev/latest/>

## Section 3. Manifests and Resource Declarations

1. **Namespace Boundary**. A namespace boundary MUST match a tenant boundary or a trust boundary. A cross-namespace reference MUST be explicit (ServiceAccount, NetworkPolicy, or RBAC). A default that allows every namespace is forbidden.

2. **Resource Requests**. Every container MUST declare CPU and memory requests. Memory MUST also declare a limit. Whether CPU limits are used MUST be an architecture decision. Each workload MUST NOT decide that question alone.

3. **Probes**. A liveness probe and a readiness probe MUST have different meanings. Readiness answers whether the process may receive traffic. Liveness answers whether the process must restart. One endpoint that serves both probes is a defect and causes a restart cascade when a downstream dependency fails.

4. **Pod Security**. Pod Security Admission labels MUST be set on the namespace. A privileged container, `hostNetwork`, or `hostPID` MUST be a named entry in `planning/decisions.md`.

5. **Image Reference**. A production manifest MUST pin an image digest. Section 6 Item B of `ENGINEERING_PRINCIPLES.md` applies. The PreToolUse hook does not enforce that digest. `imagePullPolicy: Always` paired with a moving tag MUST NOT be the update method.

## Section 4. Helm

### Item A. Version Breaking Changes

Helm 4.0.0 shipped on 2025-11-12. Differences from Helm 3 include the following. Server-Side Apply replaced client-side three-way merge as the default. `--atomic` was renamed `--rollback-on-failure`. `--force` was renamed `--force-replace`. A post-renderer argument is now a plugin name, not an executable path. `helm registry login` accepts a domain name only. Helm 3 feature releases end on 2026-09-09. Helm 3 security patches end on 2027-02-10.

Official source URLs are <https://helm.sh/blog/helm-4-released/> and <https://helm.sh/blog/helm-v3-end-of-life/>

Before the executing Agent writes a chart or a pipeline, the executing Agent MUST confirm the target Helm major version. Flag names from Helm 3 and Helm 4 MUST NOT be mixed.

1. **Charts Contain No Business Logic**. A chart template follows Section 3 of `ENGINEERING_PRINCIPLES.md`. A branch on an environment name such as `{{ if eq .Values.env "prod" }}` is forbidden. A difference MUST be expressed in values. The template MUST declare structure only.

2. **Values Contract**. `values.yaml` follows Section 4 of `ENGINEERING_PRINCIPLES.md`. The file MUST use structured objects, complete types, and backward-compatible additions. `values.schema.json` MUST exist and MUST be validated in CI.

3. **Dependencies**. `Chart.lock` MUST be in version control. A subchart source SHOULD be an OCI registry and SHOULD be referenced by digest.

4. **Deployment Method**. Either `helm template` is applied by a GitOps controller, or `helm upgrade --install` is run by a pipeline. The repository MUST choose one method and MUST write that choice as an architecture decision. A `kubectl patch` or `kubectl edit` after apply is forbidden. Section 2 Item B of `ENGINEERING_PRINCIPLES.md` applies.

5. **SSA Conflicts**. Under the Helm 4 Server-Side Apply default, a field-ownership conflict is a visible error. The executing Agent MUST fix field ownership. A force-takeover flag MUST NOT hide that error.

## Section 5. Operators and CRDs

1. **CRD Lifecycle Separation**. Installation and deletion of a CRD MUST be managed apart from the workload that uses that CRD. Deleting a CRD deletes every CR and is a destructive operation under Section 7 Item B of `ENGINEERING_PRINCIPLES.md`.

2. **Operators Are Not a Bypass Around Declaration**. Operator behavior is part of the system. Operator configuration follows Section 5 Item B of `ENGINEERING_PRINCIPLES.md`. An Operator auto-repair MUST NOT hide an error in the declared source.

## Section 6. Upgrades

1. **Sequential Minor Version Upgrades**. A minor upgrade MUST step one minor version at a time. A skipped minor version is forbidden. Before the upgrade, the executing Agent MUST confirm the kubelet and control-plane skew policy.

2. **Pre-upgrade Checks**. Before an upgrade the executing Agent MUST finish a deprecated-API scan, a CRD compatibility check, a version matrix for CNI and CSI components, and an etcd backup with a restore drill. Section 7 Item D of `ENGINEERING_PRINCIPLES.md` applies.

3. **Node Replacement**. A node upgrade MUST replace the node. An in-place upgrade is forbidden. Section 6 of `ENGINEERING_PRINCIPLES.md` applies. A Talos upgrade replaces the installer image and rolls back to the previous BOOT image on failure.
