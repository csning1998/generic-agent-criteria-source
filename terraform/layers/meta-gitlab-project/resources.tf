
module "contexts_local_credential" {
  source  = "gitlab.com/csning1998-lab/contexts-local-credential/gitlab"
  version = "0.3.1"
}

ephemeral "vault_kv_secret_v2" "state_backend" {
  mount = "secret"
  name  = "parent-group-governance/terraform/state-backend"
}

ephemeral "vault_kv_secret_v2" "github_publication" {
  mount = "secret"
  name  = "parent-group-governance/github/publication"
}

data "gitlab_group" "personal" {
  full_path = "csning1998-lab/platform-engineering-lab"
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

module "code_reviewer" {
  source  = "gitlab.com/csning1998-lab/provisioner-code-reviewer/gitlab"
  version = "~> 1.7.1"

  gitlab_project_id    = gitlab_project.this.id
  legacy_alias_enabled = true
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
