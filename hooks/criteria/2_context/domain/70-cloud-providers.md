# Sub-doc 70. Public Cloud (GCP / Google Workspace / GKE / AWS / Azure)

Sections 1, 5, 8, and 9 of `ENGINEERING_PRINCIPLES.md` are prerequisites for this file. The baseline date is 2026-08-18.

## Section 1. Cross-Cloud Common Rules

1. **Organization Level Is Upstream**. Organization policy, tenant settings, and the cloud identity directory are upstream. A workload is downstream. Section 1 Item B of `ENGINEERING_PRINCIPLES.md` applies. A workload MUST NOT change an organization-level setting.

2. **Account and Project Boundary**. An account, a project, and a subscription MUST match a trust boundary and a failure-domain boundary, and MUST match the Terraform state split. See Section 2 Item C of `50-terraform.md`.

3. **Static Key Prohibition**. A long-lived cloud access key, service-account key file, or application secret is forbidden. Section 8 Item A of `ENGINEERING_PRINCIPLES.md` applies. CI access to a cloud MUST use OIDC federation.

4. **Explicit Region and Zone**. Region and availability zone MUST be explicit inputs. A provider default or a CLI default is forbidden. Section 5 Item B of `ENGINEERING_PRINCIPLES.md` applies.

## Section 2. Google Cloud

### Item A. Two Workload Identity Mechanisms Must Not Be Conflated

Workload Identity Federation for GKE authenticates a Pod inside GKE to Google APIs. GKE manages that identity pool. An Autopilot cluster has that mechanism enabled at all times.

Workload Identity Federation authenticates a workload outside GKE (GitHub Actions, AWS, Azure, or on-premises OIDC). The Terraform resources `google_iam_workload_identity_pool` and `google_iam_workload_identity_pool_provider` belong to that second mechanism.

A document or a module MUST NOT cite one mechanism in place of the other.

Official source URL is <https://docs.cloud.google.com/kubernetes-engine/docs/concepts/workload-identity>

1. **Node Service Account**. A node pool MUST NOT use the Compute Engine default service account. That account is shared by every workload on the node and violates Section 8 Item B of `ENGINEERING_PRINCIPLES.md`. A node pool MUST name a dedicated service account with least privilege.

2. **Direct Principal vs. Impersonation**. Workload Identity Federation for GKE MAY authorize a direct principal (`principal://`) or MAY impersonate a service account. Direct principal is the preferred form. When impersonation is required, each binding MUST be one to one. A project-wide impersonation grant is forbidden.

3. **Organization Policy**. `iam.disableServiceAccountKeyCreation` MUST be enabled. An exception MUST be a named entry in `planning/decisions.md` and MUST carry an end date.

4. **GKE Cluster Configuration**. Autopilot versus Standard is an architecture decision. A Standard cluster MUST set the release channel, node auto-upgrade, Shielded Node, Workload Identity Federation for GKE, and private nodes. Those fields MUST NOT rely on defaults.

### Item F. Google Workspace

Google Workspace directory settings and Google Cloud IAM are different management planes. When Terraform manages Workspace through the `googleworkspace` provider, a change affects every user. Section 7 Item C of `ENGINEERING_PRINCIPLES.md` applies. That change MUST be planned alone and MUST be applied alone. A Workspace change MUST NOT share an apply with a cloud-resource change.

When a Workspace group is also an IAM principal, membership of that group is a privilege source. A membership change MUST receive the same review strength as an IAM change.

## Section 3. AWS

1. **Workload Identity**. EC2 MUST use an instance profile and MUST require IMDSv2 (`http_tokens = "required"`). EKS MUST use Pod Identity or IRSA. The repository MUST choose one of those two and MUST record the choice. Lambda and ECS MUST use the task role of that service. An access key MUST NOT be placed in any compute environment.

2. **Role Trust Policy**. A role trust policy MUST carry a condition. An OIDC trust policy MUST match both `aud` and `sub`. `sub` MUST be limited to a concrete repository and a branch or an environment. A wildcard that covers the whole organization is forbidden.

3. **Service Control Policy**. An SCP is organization-level upstream. Terraform in a workload account MUST NOT manage an SCP.

4. **Data Retention**. An S3 bucket MUST set versioning, encryption, public-access block, and lifecycle rules. A Terraform state bucket also follows Section 2 of `50-terraform.md`.

## Section 4. Azure

1. **Workload Identity**. Authentication MUST use Managed Identity or Workload Identity (OIDC federation on AKS). A service principal that holds a long-lived client secret MUST NOT be a standing identity.

2. **Two Management Planes**. Microsoft Entra ID (`azuread` provider) and Azure resources (`azurerm` provider) are different management planes. Section 1 Item B of `ENGINEERING_PRINCIPLES.md` applies. A directory object is upstream. A resource is downstream.

3. **Subscription and Management Group**. A management group and a policy assignment are upstream. Terraform inside a workload subscription MUST NOT change those objects.

4. **Resource Lock and Deletion**. A resource that holds durable data MUST set a delete lock or an equivalent protection. Section 7 Item B of `ENGINEERING_PRINCIPLES.md` applies.

## Section 5. Cross-Cloud Prohibited Actions

1. **Abstraction Must Not Mask Differences**. A single module that claims to support three clouds is forbidden. Each cloud has a different resource model. That abstraction fills the interface with fields that have no meaning and violates Section 4 Item B of `ENGINEERING_PRINCIPLES.md`. Each cloud MUST have its own module. The shared contract is names and tags only.

2. **Provider Default Values**. An implicit provider default is forbidden. Every field that affects security, availability, or cost MUST be declared.
