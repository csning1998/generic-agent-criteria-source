# Sub-doc 40. Identity, Credentials, and PKI (Vault / Consul ACL / Keycloak / OIDC / WIF)

Sections 1, 5, and 8 of `ENGINEERING_PRINCIPLES.md` are prerequisites for this file. The baseline date is 2026-08-18.

## Section 1. Vault Deployment and Lifecycle

1. **Storage and Secret Tier Alignment**. The Vault storage backend (Integrated Storage / Raft, or an external store) is a durable tier. Unseal material, recovery keys, and Raft data MUST share that tier. Section 1 Item A of `ENGINEERING_PRINCIPLES.md` applies. Unseal material MUST NOT live in a layer that disappears when the Vault cluster is rebuilt.

2. **Auto-unseal Dependency Direction**. When a cloud KMS or an HSM performs auto-unseal, that KMS or HSM is upstream of Vault. The access credential for that KMS or HSM MUST NOT be stored inside Vault. That reverse edge violates Section 1 Item B of `ENGINEERING_PRINCIPLES.md`.

3. **Raft Membership**. The node count of Integrated Storage follows Section 1 Item C of `ENGINEERING_PRINCIPLES.md`. The count MUST be odd. Members MUST span failure domains. A membership change MUST move one node per step.

## Section 2. Vault Authentication Methods

### Item A. Selection Order

Inside Kubernetes the executing Agent MUST prefer the Kubernetes auth method or JWT/OIDC auth, and MUST exchange a ServiceAccount token for a Vault token.

On a cloud virtual machine the executing Agent MUST prefer the instance identity of that cloud (AWS IAM auth, GCP IAM auth, or Azure MSI auth).

AppRole is allowed only when both of the previous methods are unavailable.

### Item B. AppRole Constraints

When AppRole is in use, `role_id` MAY be treated as a non-secret identifier. `secret_id` is a secret. `secret_id` MUST have a short TTL. `secret_id_num_uses` MUST be capped. Delivery MUST use response wrapping. An unwrapped `secret_id` MUST NOT be written into a config file, a CI variable, or an image.

A `secret_id` that a human stores for a long period violates Section 8 Item A of `ENGINEERING_PRINCIPLES.md`.

1. **User Identity**. A human MUST authenticate through the OIDC auth method against Keycloak or against a cloud identity provider. A long-lived token for a human is forbidden. A shared root token is forbidden. A root token MAY be created only during initialization or disaster recovery, and MUST be revoked immediately after that use.

## Section 3. Vault and Kubernetes Integration

### Item A. Choosing Among the Three Integration Methods

The choice among Vault Secrets Operator (VSO), Vault Agent Injector (sidecar), and the Vault CSI provider MUST be written in `planning/decisions.md`. The same cluster MUST NOT run more than one of those methods without a recorded reason.

Known bounds are as follows. The VSO CSI driver supports KV and AppRole secret IDs only. Agent Injector supports every Vault auto-auth method and renders files into a shared memory volume. The CSI provider opens one connection per Pod and places the highest load on Vault.

Official source URL is <https://developer.hashicorp.com/vault/docs/deploy/kubernetes/comparisons>

1. **Sidecar PKI**. When a sidecar fetches and rotates a certificate, that certificate MUST be written to an `emptyDir` whose `medium` is `Memory`. That certificate MUST NOT be written to a persistent volume. The application MUST reload the certificate without a process restart. A restart that exists only because rotation rewrote a file is a defect.

2. **Certificate Validity Period**. A service certificate MUST expire before the longest allowed node lifetime. The rotation period MUST be shorter than half of that validity. An intermediate CA MUST outlive the longest leaf that the intermediate CA signs. An expiry alert MUST exist for that intermediate CA.

## Section 4. PKI

1. **Root CA Offline**. A root CA private key MUST NOT exist on any online service. Online issuance MUST use an intermediate CA.

2. **Single Issuer**. One trust domain MAY have one issuing intermediate CA. Section 5 Item A of `ENGINEERING_PRINCIPLES.md` applies. Two Vault mounts MUST NOT issue into the same SAN namespace at the same time.

3. **Revocation Path**. The publication point of a CRL or of OCSP MUST sit outside the failure domain of the issued service. Section 9 Item B of `ENGINEERING_PRINCIPLES.md` applies.

## Section 5. Consul ACL

1. **Default Deny**. `acl.default_policy` MUST be `deny`. After ACL is enabled, the anonymous token MUST have no write grant.

2. **Token Binding**. An agent token, a service token, and a replication token MUST be separate objects. A bootstrap token MUST NOT be a runtime identity.

3. **Service Registration Source**. Service registration data MUST come from one source. That source is either the config file or the API. Section 5 Item A of `ENGINEERING_PRINCIPLES.md` applies.

## Section 6. Keycloak and OIDC

1. **Realm Boundary**. A realm boundary MUST match a trust boundary. Clients of different trust tiers MUST NOT share one realm and then separate themselves by role.

2. **Client Configuration**. The secret of a confidential client MUST live in Vault or in a cloud secret manager. That secret MUST NOT be written into an IaC variable file. A public client MUST enable PKCE.

3. **Explicit Claim Mapping**. The mapping from a role to a claim MUST be readable in code. Section 5 Item B of `ENGINEERING_PRINCIPLES.md` applies. An implicit default mapper in Keycloak MUST NOT be the only record of that mapping.

4. **Token Lifecycle**. An access-token lifetime MUST be shorter than the authorization cache of every downstream service. Otherwise a revocation does not take effect.

## Section 7. Workload Identity Federation

1. **Two Mechanisms Must Not Be Conflated**. Workload Identity Federation for GKE is one mechanism. Workload Identity Federation for external workloads is a second mechanism. The Terraform resources `google_iam_workload_identity_pool` and `google_iam_workload_identity_pool_provider` belong to the second mechanism. Those resources authenticate GitHub Actions, AWS, Azure, and on-premises OIDC workloads. Those resources do not configure a Pod identity inside GKE.

    Official source URL is <https://docs.cloud.google.com/kubernetes-engine/docs/concepts/workload-identity>

2. **Principal Mapping Must Be Stable and Narrow**. An attribute mapping from an external issuer MUST bind to a field that the requester cannot forge, such as a repository ID. A repository name is not that field. An attribute condition MUST exist. A pool that accepts every principal is forbidden.

3. **One Application, One Principal**. Two applications MUST NOT share one federated service account. Section 8 Item B of `ENGINEERING_PRINCIPLES.md` applies.

4. **Key File Prohibition**. A service-account JSON key file MUST NOT be created. The organization policy MUST block key creation. An exception MUST be a named entry in `planning/decisions.md` and MUST carry an end date.
