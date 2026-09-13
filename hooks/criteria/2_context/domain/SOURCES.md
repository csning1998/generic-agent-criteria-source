# Source

Every link in this file was verified on 2026-08-18. Before the executing Agent cites a versioned claim from this directory, the executing Agent MUST verify that claim again against the official source.

## Terraform / OpenTofu

- S3 backend (`use_lockfile`, deprecation of `dynamodb_table`). <https://developer.hashicorp.com/terraform/language/backend/s3>
- AWS Prescriptive Guidance, backend practices. <https://docs.aws.amazon.com/prescriptive-guidance/latest/terraform-aws-provider-best-practices/backend.html>
- CDKTF issue that records the deprecation warning. <https://github.com/hashicorp/terraform-cdk/issues/3834>
- Terraform 1.15 release coverage. <https://www.infoq.com/news/2026/06/terraform-1-15/>
- OpenTofu 1.12 release coverage. <https://www.infoq.com/news/2026/05/opentofu-release-terraform/>
- OpenTofu project. <https://opentofu.org/>

## Ansible

- ansible-core 2.19 porting guide (Data Tagging and breaking templating). <https://docs.ansible.com/projects/ansible-core/devel/porting_guides/porting_guide_core_2.19.html>
- Ansible 12 porting guide. <https://docs.ansible.com/projects/ansible/latest/porting_guides/porting_guide_12.html>
- ansible-core 2.20 roadmap. <https://docs.ansible.com/projects/ansible/latest/roadmap/ROADMAP_2_20.html>
- Releases and maintenance. <https://docs.ansible.com/projects/ansible/latest/reference_appendices/release_and_maintenance.html>

## Kubernetes / Helm

- Kubernetes releases. <https://kubernetes.io/releases/>
- Kubernetes v1.36 release notes (Ingress-NGINX retirement, SELinux mount context GA). <https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/>
- Kubernetes v1.36 sneak peek (removed items). <https://kubernetes.io/blog/2026/03/30/kubernetes-v1-36-sneak-peek/>
- Kubernetes v1.37 release information. <https://www.kubernetes.dev/resources/release/>
- Helm 4 release notes. <https://helm.sh/blog/helm-4-released/>
- Helm 3 end of life. <https://helm.sh/blog/helm-v3-end-of-life/>
- Helm releases. <https://github.com/helm/helm/releases>

## Talos

- Talos Linux documentation. <https://www.talos.dev/latest/>

## Vault / HashiCorp

- Vault Kubernetes integration comparison (VSO / Agent Injector / CSI). <https://developer.hashicorp.com/vault/docs/deploy/kubernetes/comparisons>
- Vault Agent Injector and CSI provider comparison. <https://developer.hashicorp.com/vault/docs/deploy/kubernetes/injector-csi>

## Google Cloud

- About Workload Identity Federation for GKE. <https://docs.cloud.google.com/kubernetes-engine/docs/concepts/workload-identity>
- Practices for Workload Identity Federation. <https://docs.cloud.google.com/iam/docs/best-practices-for-using-workload-identity-federation>

## etcd / Patroni

- Announcing etcd v3.6.0 (removal of `--enable-v2`, v3store as the only membership source, peer endpoints no longer serving clients). <https://etcd.io/blog/2025/announcing-etcd-3.6/>
- Patroni documentation. <https://patroni.readthedocs.io/en/latest/>
- Patroni issue 3382 (etcd 3.6 compatibility). <https://github.com/patroni/patroni/issues/3382>
- Patroni discussion 3461. <https://github.com/patroni/patroni/discussions/3461>

## MinIO

- MinIO repository status. <https://github.com/minio/minio>

## Istio

- Sidecar or ambient (data-plane modes). <https://istio.io/latest/docs/overview/dataplane-modes/>

## Podman

- podman-systemd.unit(5) (Quadlet). <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html>
- podman generate systemd (deprecation). <https://docs.podman.io/en/latest/markdown/podman-generate-systemd.1.html>
- podman auto-update. <https://docs.podman.io/en/latest/markdown/podman-auto-update.1.html>
- Red Hat Quadlet notes. <https://www.redhat.com/en/blog/quadlet-podman>

## Grafana LGTM

- Grafana / Loki / Tempo relicensed to AGPLv3. <https://grafana.com/blog/grafana-loki-tempo-relicensing-to-agplv3/>
- Grafana Tempo. <https://grafana.com/oss/tempo/>
- Grafana documentation. <https://grafana.com/docs/>

## 尚缺足夠最新資訊的項目

The items below receive only a principle in this directory. This directory does not pin a version or a license detail, because verification on the baseline date was not enough to confirm the current state.

- VMware vSphere licensing and packaging under Broadcom. See Section 3 Item A of `71-virtualization-onprem.md`.
- Recommended pairing of the Nutanix Prism API and the `nutanix` Terraform provider. See Section 4 Item B of `71-virtualization-onprem.md`.
- The current MicroK8s addon list and the maintenance status of each addon.
- The current Keycloak major version and the breaking-change history of the Keycloak admin API.
