# **HashiCorp Configuration Language (HCL) Specific Standards**

- **(a) Applicable Scope**：Includes `*.hcl`, `*.pkrvars.hcl`, `*.tf`, `*.tofu`, `*.tfvars`
- **(b) Naming and Variables**：
    - `snake_case` MUST be used
    - A variable MUST have `description` and `type` declarations. Passing `any` is strictly prohibited, unless official documentation requires it
    - Redundant resource naming (e.g. `resource "aws_vpc" "vpc"`) and meaningless serial numbers are prohibited. `main`, `this`, or a name according to function SHOULD be used
- **(c) Architecture and State**：Physical directories and state files MUST be split according to business logic and environment (Dev/QA/Prod). Repeated logic MUST be encapsulated as independent Modules and placed under version control
- **(d) Declarative Purity**：Remain Declarative. Overly complex dynamic logic or nested Anti-patterns are prohibited
- **(e) Version Locking**：A terraform block MUST be defined in the root module, with `required_version` and `required_providers` version ranges stated explicitly. Configuration without version locking is strictly prohibited
- **(f) Logic and Verification**：
    - A variable SHOULD have a `validation` block that checks factual format
    - When a resource array is handled, `for_each` MUST be used in preference to `count` (except a simple Boolean switch). Resource indexes MUST rest on a Key.
- **(g) Output and Dynamic Retrieval**：
    - Every `output` block MUST contain `description`. Output of unprocessed sensitive data is prohibited
    - Hard-coded IDs (e.g. writing `ami` or `arn` as a literal) are strictly prohibited. Data Sources MUST be used to retrieve live facts from the cloud or from a HashiCorp Vault environment
