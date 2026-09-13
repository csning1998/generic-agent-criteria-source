# Sub-doc 50. Terraform / OpenTofu

Sections 1 through 9 of `ENGINEERING_PRINCIPLES.md` apply to this file. This file adds Terraform and OpenTofu rules. The baseline date is 2026-08-18.

## Section 1. Engine and Version

1. **Engine Must Be Pinned in Code**. `required_version` MUST exist and MUST be a bounded range such as `~> 1.15.0`. An empty constraint is forbidden. An unbounded `>=` constraint is forbidden. Terraform uses BUSL 1.1 from 1.6 onward. OpenTofu uses MPL 2.0 and is governed by the Linux Foundation. Which engine the repository uses is an architecture decision. The same codebase MUST NOT accept divergent syntax from both engines.

2. **Provider Version and Lock File**. `required_providers` MUST pin a version range. `.terraform.lock.hcl` MUST be in version control and MUST contain hashes for every target platform (`terraform providers lock -platform=...`). A missing platform hash causes CI to fail at init. The PreToolUse hook does not block an edit to the lock file.

## Section 2. State

1. **State Is the Authoritative State**. A state file follows Section 1 Item D of `ENGINEERING_PRINCIPLES.md`. The backend MUST enable versioning and encryption. A backup of that backend MUST remain restorable after the described resources are gone.

### Item B. Locking Mechanism

An S3 backend MUST set `use_lockfile = true`. The argument `dynamodb_table` is deprecated and will be removed in a future minor release. `dynamodb_table` MAY coexist with `use_lockfile` only during a migration, and that migration MUST have an end date.

Official source URL is <https://developer.hashicorp.com/terraform/language/backend/s3>

After `use_lockfile` is enabled, the IAM policy MUST also grant `s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject` on the lock object.

1. **State Partitioning**. A state-split boundary MUST match a failure-domain boundary and MUST match a change-frequency boundary. Control-plane resources and application workloads MUST NOT share one state. Two environments MUST NOT share one state, including a workspace that pretends to separate those environments.

2. **Manual Editing Prohibited**. A human MUST NOT edit a state file by hand. A resource-address change MUST use a `moved` block. A resource that leaves management MUST use a `removed` block. `terraform state rm` and `terraform import` are allowed only inside a recorded remediation, and the same commit MUST restore the code that matches the resulting state.

## Section 3. Modules

1. **Generic Module Boundary**. Every path under `terraform/modules/` follows all of Section 3 of `ENGINEERING_PRINCIPLES.md`. A generic module MUST NOT contain a `provider` block with concrete credentials. A generic module MUST NOT run a `data` lookup against an environment-specific resource. A generic module MUST NOT branch `count` or `for_each` on an environment alias.

2. **Provider Passthrough**. A generic module MAY declare `configuration_aliases`. The caller MUST pass the mapping through `providers = { ... }`. The generic module MUST NOT create its own provider configuration. A one-environment-to-one-alias identity map is forbidden.

3. **Interface**. Module inputs and outputs follow Section 4 of `ENGINEERING_PRINCIPLES.md`. An input MUST use `object({...})` with a complete type. An output MUST be a named map whose keys match the architecture decisions. A scalar such as `variable "service_name"` is forbidden.

## Section 4. Prohibited Actions

1. **Runtime Patching**. A `local-exec` provisioner is forbidden. A `remote-exec` provisioner is forbidden. A `null_resource` or `terraform_data` that runs a script to fill a field the provider does not manage is forbidden. When the provider lacks a field, the executing Agent MUST file an upstream issue and MUST record a deferral in `planning/decisions.md`.

2. **Implicit Defaults**. A `variable` MUST NOT carry a `default` that changes resource topology. A default is allowed only on a parameter that does not change topology, such as a tag or a description.

3. **Dynamic Identifier Concatenation**. Deriving another layer's ARN, `self_link`, or resource ID by string concatenation is forbidden. A cross-layer read MUST use `terraform_remote_state` or a named data source from the provider.

## Section 5. Execution

1. **Plan Artifact Is the Review Object**. CI MUST write a binary plan with `terraform plan -out=tfplan`. The apply stage MUST apply that same plan file. The apply stage MUST NOT plan again.

2. **Destructive Changes**. When a plan contains `destroy` or `must be replaced`, Section 7 Item B of `ENGINEERING_PRINCIPLES.md` applies. The executing Agent MUST ask the owner for a separate confirmation. A resource that holds durable data MUST default `prevent_destroy` to true. Turning that flag off MUST be explained in the commit message.

3. **Targeting**. `-target` is allowed only during incident remediation. A regular pipeline MUST NOT pass `-target`. After a targeted run, the same body of work MUST complete one full plan without `-target` and MUST confirm zero changes.

## Section 6. Sensitive Values

1. **No Plaintext Persistence**. A sensitive output MUST set `sensitive = true`. Terraform state still stores the value in plaintext. Backend encryption and backend access control are therefore required.

2. **Origin of Generation**. Terraform MUST NOT remain the long-term owner of a secret. Section 5 Item A of `ENGINEERING_PRINCIPLES.md` applies. A `random_password` resource MAY exist only in a mint layer during bootstrap. After bootstrap, Vault or the cloud secret manager MUST own rotation. A consumer layer MUST NOT declare `random_password` and MUST NOT call a mint module.
