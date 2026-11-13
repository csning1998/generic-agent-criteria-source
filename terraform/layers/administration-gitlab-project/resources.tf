
data "gitlab_group" "personal" {
  full_path = "${var.gitlab_top_level_group_path}/platform-engineering-lab"
}

resource "gitlab_project" "this" {
  name             = "generic-agent-criteria-source"
  path             = "generic-agent-criteria-source"
  description      = "AI skills for Gemini, Grok, Cursor, Claude with Second Brain documentation and harness policy."
  visibility_level = "public"
  namespace_id     = tonumber(data.gitlab_group.personal.id)

  merge_method                             = "ff"
  squash_option                            = "always"
  squash_commit_template                   = "%%{title}"
  only_allow_merge_if_pipeline_succeeds    = true
  remove_source_branch_after_merge         = true
  ci_push_repository_for_job_token_allowed = true
  initialize_with_readme                   = false
  shared_runners_enabled                   = false
  issues_access_level                      = "enabled"
  wiki_access_level                        = "disabled"
}

resource "gitlab_branch_protection" "main" {
  project = gitlab_project.this.id
  branch  = "main"

  allowed_to_push  = [{ access_level = "no one" }]
  allowed_to_merge = [{ access_level = "maintainer" }]

  allow_force_push = false
}

module "workload_identity_federation" {
  source  = "gitlab.com/csning1998-lab/provisioner-workload-identity-federation/gitlab"
  version = "0.7.0"

  gitlab_url = var.gitlab_url

  gitlab_project = {
    id   = gitlab_project.this.id
    path = gitlab_project.this.path_with_namespace
    code = "generic-agent-criteria-source"
  }

  anthropic_federation = {
    issuer_id       = local.ai_provider["anthropic"].issuer_id
    organization_id = local.ai_provider["anthropic"].organization_id
  }

  google_federation = {
    project_id     = local.ai_provider["google-cloud"].project_id
    project_number = local.ai_provider["google-cloud"].project_number
    pool_id        = local.ai_provider["google-cloud"].pool_id
    provider_id    = local.ai_provider["google-cloud"].provider_id
  }

  azure_federation = {
    tenant_id            = local.ai_provider["azure"].tenant_id
    subscription_id      = local.ai_provider["azure"].subscription_id
    cognitive_account_id = local.ai_provider["azure"].cognitive_account_id
    openai_endpoint      = local.ai_provider["azure"].openai_endpoint
    subjects = [
      "project_path:${gitlab_project.this.path_with_namespace}:ref_type:branch:ref:main",
      "project_path:${gitlab_project.this.path_with_namespace}:ref_type:branch:ref:chore/update-dependencies",
    ]
  }
}

# ./governance of parent-group-governance writes the reviewer CI variables. Terraform forgets the variables without deletion.
removed {
  from = module.code_reviewer

  lifecycle {
    destroy = false
  }
}

module "github_mirror" {
  source  = "gitlab.com/csning1998-lab/provisioner-github-mirror/gitlab"
  version = "0.3.1"

  gitlab_project_id = gitlab_project.this.id

  github_repository = {
    name  = gitlab_project.this.name
    owner = var.github_owner
  }
}

import {
  to = module.github_mirror.github_repository.this
  id = "generic-agent-criteria-source"
}

import {
  to = module.github_mirror.gitlab_project_push_mirror.this
  id = "85419450:4102493"
}

import {
  to = module.github_mirror.github_repository_deploy_key.this
  id = "generic-agent-criteria-source:160794534"
}
