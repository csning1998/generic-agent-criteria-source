
variable "github_owner" {
  description = "Specifies the GitHub account or organization login hosting the mirrored repository."
  type        = string
  default     = "csning1998"

  validation {
    condition     = can(regex("^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$", var.github_owner))
    error_message = "github_owner must be a GitHub login of 1 to 39 characters. A hyphen must not be the first or last character."
  }
}

variable "gitlab_url" {
  description = "Specifies the GitLab instance HTTPS URL exported by vault-proxy-env from the repository origin remote."
  type        = string

  validation {
    condition     = can(regex("^https://[^/]+$", var.gitlab_url))
    error_message = "gitlab_url must be https://<host> without a trailing path."
  }
}

variable "gitlab_top_level_group_path" {
  description = "Specifies the root GitLab group path exported by vault-proxy-env from the repository origin remote."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_.-]*$", var.gitlab_top_level_group_path))
    error_message = "gitlab_top_level_group_path must be one GitLab path segment."
  }
}

variable "gitlab_token_owner_code" {
  description = "Specifies the owner code whose state backend token authenticates the gitlab provider. The first creation of the project sets parent-group-governance under the credential-distributor identity, since a token limited to the project cannot exist before the project."
  type        = string
  default     = "generic-agent-criteria-source"

  validation {
    condition     = contains(["generic-agent-criteria-source", "parent-group-governance"], var.gitlab_token_owner_code)
    error_message = "gitlab_token_owner_code must be generic-agent-criteria-source, or parent-group-governance for the first creation of the project."
  }
}
