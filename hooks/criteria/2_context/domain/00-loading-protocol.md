# Sub-doc 00. Loading Protocol and High-Volatility List

The executing Agent MUST open this file before opening any other file in this directory. The baseline date is 2026-08-18.

Grok does not load this file at session start. The SessionStart hook does not inject this file. The UserPromptSubmit hook does not inject this file.

## Section 1. Routing Rules

### Item A. Determine by Path Pattern

| Path Pattern                                                                           | Sub-doc to Load                       |
| -------------------------------------------------------------------------------------- | ------------------------------------- |
| `terraform/**`, `*.tf`, `*.tfvars`, `*.tfstate`, `.terraform.lock.hcl`                 | `50-terraform.md`                     |
| `ansible/**`, `*.yml` including `hosts:`/`tasks:`, `inventory/**`, `group_vars/**`     | `51-ansible.md`                       |
| `packer/**`, `*.pkr.hcl`, `Vagrantfile`, `vagrant/**`                                  | `52-packer-vagrant.md`                |
| `charts/**`, `Chart.yaml`, `kustomization.yaml`, `manifests/**`, `talos/**`            | `60-kubernetes-and-helm.md`           |
| `Containerfile`, `Dockerfile`, `*.container` (Quadlet), `*.te`/`*.fc` (SELinux policy) | `61-container-runtime-and-selinux.md` |
| `istio/**`, `Gateway`/`HTTPRoute`/`VirtualService` resources, `consul-connect/**`      | `62-service-mesh-and-network.md`      |
| `vault/**`, `policies/**`, `keycloak/**`, `*.hcl` including `path "..."`               | `40-identity-and-secrets.md`          |
| when provider is `google`/`google-workspace`/`aws`/`azurerm`/`azuread`                 | `70-cloud-providers.md`               |
| when provider is `libvirt`/`vsphere`/`nutanix`, or `*.xml` domain def                  | `71-virtualization-onprem.md`         |
| `etcd/**`, `patroni/**`, `redis/**`, `minio/**`, `consul/**` on server side            | `80-stateful-and-quorum.md`           |
| `argocd/**`, `flux/**`, `Application`/`Kustomization` CR, `grafana/**`, `otel*/**`     | `90-gitops-and-observability.md`      |

The column titled Sub-doc to Load names the file that the executing Agent MUST open. The PreToolUse hook does not open those files.

1. **Determine by Keyword**. When the owner's prompt contains any of the following terms, the executing Agent MUST open the matching sibling file even if no matching path has been opened yet. The terms are state locking, drift, quorum, split-brain, mTLS, SPIFFE, rootless, Workload Identity, erasure coding, DCS, failover, sealed, and unseal. The UserPromptSubmit hook does not classify work from those terms.

2. **Load Only What the Task Hits**. The executing Agent MUST open only the sibling files that the current task hits. The executing Agent MUST NOT preload a stack that the current task does not touch. When the current task hits several sibling files, the executing Agent MAY open those files in the same session. A file-count cap MUST NOT split the current task.

## Section 2. High-Volatility Items (Verification Required Before Stating)

The items below changed during 2025 and 2026 in ways that alter an operational conclusion. Before the executing Agent states a behavior for any item below, the executing Agent MUST verify that behavior against the official source named in `SOURCES.md`. Training data MUST NOT substitute for that verification.

1. **Helm Major Version**. Helm 4.0.0 shipped on 2025-11-12. Server-Side Apply became the default. The flag `--atomic` was renamed `--rollback-on-failure`. The flag `--force` was renamed `--force-replace`. A post-renderer argument is now a plugin name, not an executable path. Helm 3 feature releases end on 2026-09-09. Helm 3 security patches end on 2027-02-10. Official source URL is <https://helm.sh/blog>.

2. **Kubernetes Version**. Kubernetes v1.36 Haru shipped on 2026-04-22. Kubernetes v1.37 is scheduled for 2026-08-26. Kubernetes v1.36 removed kube-proxy IPVS mode and the gitRepo volume plugin. User Namespaces, MutatingAdmissionPolicy, Fine-grained Kubelet API Authorization, and SELinux mount context are GA. Official source URL is <https://kubernetes.io/releases>.

3. **Ingress-NGINX**. SIG Network and the Security Response Committee retired Ingress-NGINX on 2026-03-24. After that date there is no new release and no security patch. Official source URL is <https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/>

4. **Terraform / OpenTofu**. Terraform 1.15.x is current on the baseline date (1.15.2 on 2026-05-06, 1.15.8 seen in 2026-07). Terraform uses BUSL 1.1 from 1.6 onward. OpenTofu 1.12.x is current (1.12.0 on 2026-05-14) and uses MPL 2.0. IBM completed the HashiCorp acquisition in 2025-02. Official source URLs are <https://developer.hashicorp.com> and <https://opentofu.org>.

5. **Terraform S3 Backend Locking**. The current lock mechanism is `use_lockfile`. The argument `dynamodb_table` is deprecated and will be removed in a future minor release. Official source URL is <https://developer.hashicorp.com/terraform/language/backend/s3>.

6. **ansible-core**. ansible-core 2.19 introduced Data Tagging and strict templating. That change is breaking. ansible-core 2.20 (Ansible 13) deprecated `INJECT_FACTS_AS_VARS` and requires Python 3.12 or newer on the controller. ansible-core 2.21.2 was seen in 2026-07. Official source URLs are the Ansible porting guides on <https://docs.ansible.com>.

7. **etcd**. etcd 3.6.0 removed `--enable-v2`. v3store is the only membership source of truth. Official source URL is <https://etcd.io/blog/2025/announcing-etcd-3.6>.

8. **Patroni**. A Patroni process that talks to etcd 3.6 or newer MUST use the `etcd3` configuration section. The `etcd` section uses the v2 API and fails. Official source URLs are <https://patroni.readthedocs.io> and <https://github.com/patroni/patroni/issues/3382>.

9. **MinIO**. The community edition lost its admin UI in 2025. The public repository was archived read-only on 2026-04-25. There is no official community binary after that date. The license remains AGPLv3. Official source URL is <https://github.com/minio/minio>.

10. **Istio**. Ambient mode is GA from 1.24. ztunnel handles L4. A waypoint handles L7. Official source URL is <https://istio.io/latest/docs/overview/dataplane-modes>.

11. **Podman**. Quadlet is the documented unit format. `podman generate systemd` is deprecated. Quadlet requires cgroup v2. Official source URL is <https://docs.podman.io>.

12. **Grafana LGTM**. Grafana, Loki, and Tempo have used AGPLv3 since 2021-04. Mimir 3.0 shipped in 2025-11 and split the read path from the write path. Official source URL is <https://grafana.com>.

13. **GKE Identity**. Workload Identity Federation for GKE is one mechanism. Workload Identity Federation for external workloads is a second mechanism. The Terraform resource `google_iam_workload_identity_pool` belongs to the second mechanism and does not configure a GKE Pod identity. Official source URL is <https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity>.

## Section 3. Behavior When Verification Fails

When verification still cannot confirm a claim, the executing Agent MUST emit all three of the following items.

1. The sentence `目前缺乏足夠的最新資訊`.
2. The sources that the executing Agent already opened.
3. A stop on the unverified claim. The executing Agent MUST NOT offer a substitute guess.

Phrases such as `generally`, `usually`, and `in most cases` MUST NOT carry a versioned fact.
