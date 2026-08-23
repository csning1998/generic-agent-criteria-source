# README for The Repository

This repository's working tree maps directly to `~/.grok`. Grok installation populates `~/.grok` with runtime files, causing `git clone` against this non-empty directory to fail. The setup attaches a Git remote to the existing `~/.grok` directory and checks out `main`.

## Section 1. Clone Repository into Existing Grok Home

### Task A. Prerequisites

1. Grok is installed and initialized via at least one successful login, generating `~/.grok/auth.json`.
2. SSH connectivity to `gitlab.com` is established with read access to `csning1998-lab/personal/skills-xai-supergrok`.
3. Target remote URI is `git@gitlab.com:csning1998-lab/personal/skills-xai-supergrok.git`.
4. Local directory `~/.grok` is not an existing Git repository.

### Task B. Tracked and Untracked Path Behavior

`.gitignore` enforces an allow-list model. Checkout operations mutate only tracked repository paths.

- **Paths Overwritten or Created During Checkout:**
    - `skills/`
    - `docs/second-brain/`
    - `docs/.markdownlint.json`
    - `docs/.mdlrc`
    - `memory/`
    - `terraform/`
    - `.gitlab-ci.yml`
    - `.gitlab/CODEOWNERS`
    - `.gitignore`
    - `tutorial-git-clone.md`
    - `config.toml`. A pre-installed environment typically already contains this file. Conflict handling is Section 1 Task C.3.

- **Paths Preserved During Checkout:**
    - `auth.json`
    - `sessions/`
    - `bin/`
    - `bundled/`
    - `downloads/`
    - `vendor/`
    - `marketplace-cache/`
    - `docs/user-guide/`
    - `logs/`
    - `memtrace/`
    - `.lock` files, temporary caches, and `worktrees.db`

`git checkout -f` overwrites tracked local modifications. Untracked files that block working tree checkout remain.

### Task C. Execution Steps

1. **Verify Grok Directory Context**

    ```bash
    test -d "${HOME}/.grok"
    test -f "${HOME}/.grok/auth.json"
    ```

    Execute subsequent steps only if both commands return exit code `0`.

2. **Initialize Repository and Attach Remote**

    ```bash
    cd "${HOME}/.grok"
    git init --initial-branch=main
    git remote add origin git@gitlab.com:csning1998-lab/personal/skills-xai-supergrok.git
    git fetch origin
    ```

    If `git init` reports an existing repository, the state MUST be inspected via `git remote -v` and `git status` to verify repository identity before the `origin` remote URL is updated.

3. **Resolve `config.toml` Conflict**

    Existing installations contain an untracked `config.toml` that conflicts with the tracked repository file, causing `git checkout` to fail with `untracked working tree files would be overwritten`. Relocate local configuration to permit repository checkout:

    ```bash
    mv config.toml config.toml.local
    ```

    Machine-specific UI or model configurations MUST be merged manually from `config.toml.local` into `config.toml` after checkout. Authentication credentials reside in `auth.json`.

4. **Checkout Branch `main`**

    ```bash
    git checkout -B main origin/main
    git status -sb
    git config core.hooksPath .githooks
    ```

    The tracking state MUST indicate `main...origin/main`. The presence of `skills/`, `docs/second-brain/`, `memory/`, and `terraform/` MUST be confirmed. If untracked file conflicts persist, conflicting paths MUST be relocated before checkout is re-executed.

5. **Post-Checkout Verification**
    1. Execute `grok` to verify authentication validity.
    2. Terraform operations targeting GitLab projects MUST use local credentials: `~/.vault-token`, `~/.terraform.d/credentials.tfrc.json`, and `~/GitLab/meta-platform/vault/tls/ca.pem`. State is hosted on the GitLab HTTP backend (Project ID: `85419450`).
    3. `auth.json` MUST NOT be transferred across hosts.
    4. `git rev-parse --git-path hooks` MUST print `.githooks`. Tracked hooks are `pre-commit` (gitleaks) and `commit-msg` (commitlint). Both run via `podman run`.
    5. Harness adapters MUST be materialized according to Section 3.

6. **Prohibited Operations**
    1. Executing `git clone ... ~/.grok` directly against populated `~/.grok` MUST be prohibited.
    2. Overwriting `~/.grok` with a temporary clone directory containing `sessions/` or `auth.json` MUST be prohibited.
    3. Relying on `git checkout -f` to clear untracked `config.toml` files MUST be prohibited.

## Section 2. Terraform Operations

The Bastion Vault instance under `meta-platform` MUST be unsealed. Prior to executing Terraform commands, HTTP state backend credentials MUST be exported:

```bash
export TF_HTTP_USERNAME='gitlab-ci-token'
export TF_HTTP_PASSWORD=$(VAULT_ADDR='https://127.0.0.1:8200' VAULT_CACERT="$HOME/GitLab/meta-platform/vault/tls/ca.pem" VAULT_TOKEN=$(cat $HOME/.vault-token) vault kv get -field=token secret/meta-platform-credentials/state-backend)
```

## Section 3. Harness Adapter Installer

`~/.claude`, `~/.agents`, and `~/.gemini` are product homes. Those directories MUST NOT enter this repository. Distill, cross-harness skill bodies, and the Claude thin shell have their source of truth in this tree. `hooks/bin/install-adapters.py` materializes the runtime copies.

The installer is written in Python. It MUST NOT call `cp`, `ln`, `rsync`, or `subprocess`. The default verb is `check`. The `apply` verb writes destinations and constitutes a local execute act under §301.

### Item A. Source of truth

Grok reads `rules/AGENT_CRITERIA.md` directly. That path is not an installer destination.

Tracked sources the installer reads:

- Distill: `rules/AGENT_CRITERIA.md`
- Claude thin shell: `hooks/adapters/claude/CLAUDE.md`
- Skill bodies: `hooks/adapters/skills/`
- Language L2: `hooks/criteria/references/lang-*.md`

`config.example.toml` keeps `[skills] paths = ["~/.agents/skills"]`. After `apply`, that path is a symlink to `hooks/adapters/skills`.

### Item B. Commands

Run from `${HOME}/.grok`:

1. Environment checks MUST be performed first using the following command:

    ```bash
    uv run python hooks/bin/install-adapters.py check
    ```

    The `check` command reads adapter states and prints `OK` or `DRIFT` without mutating state. The `apply` command prints `APPLY`, `SKIP`, or `ABORT` and materializes files as needed. Optional `--home` and `--grok-root` flags are provided for testing. Production invocations MUST omit testing flags and MUST use `${HOME}`.

2. The installer MUST be executed once the environment is confirmed healthy:

    ```bash
    uv run python hooks/bin/install-adapters.py apply
    ```

3. Python unit tests MAY be executed using the following command:

    ```bash
    uv run pytest tests/test_install_adapters.py
    ```

### Item C. Allow-listed destinations

| Source                                    | Dest                      | Mode    |
| ----------------------------------------- | ------------------------- | ------- |
| `rules/AGENT_CRITERIA.md`                 | `~/.agents/AGENTS.md`     | symlink |
| `rules/AGENT_CRITERIA.md`                 | `~/.gemini/GEMINI.md`     | symlink |
| `hooks/adapters/claude/CLAUDE.md`         | `~/.claude/CLAUDE.md`     | copy    |
| `hooks/adapters/skills`                   | `~/.agents/skills`        | symlink |
| `hooks/criteria/references/lang-md.md`    | `~/.claude/lang_md.md`    | symlink |
| `hooks/criteria/references/lang-hcl.md`   | `~/.claude/lang_hcl.md`   | symlink |
| `hooks/criteria/references/lang-ts.md`    | `~/.claude/lang_ts.md`    | symlink |
| `hooks/criteria/references/lang-ipynb.md` | `~/.claude/lang_ipynb.md` | symlink |
| `hooks/criteria/references/lang-md.md`    | `~/.gemini/lang_md.md`    | symlink |
| `hooks/criteria/references/lang-hcl.md`   | `~/.gemini/lang_hcl.md`   | symlink |
| `hooks/criteria/references/lang-ts.md`    | `~/.gemini/lang_ts.md`    | symlink |
| `hooks/criteria/references/lang-ipynb.md` | `~/.gemini/lang_ipynb.md` | symlink |

The Claude destination is copy mode because that file MUST keep `@~/.agents/AGENTS.md` plus §403 and §205(f). Destinations outside this table MUST be rejected. The installer MUST NOT write `settings.json`, `settings.local.json`, `oauth_creds.json`, `auth.json`, `control.key`, `daemon/`, `sessions/`, or `file-history/`. It MUST NOT replace `~/.claude`, `~/.agents`, or `~/.gemini` as a whole.

### Item D. Drift tokens and abort

`check` reports one token per destination:

- `missing`: dest is absent
- `regular-same`: dest is a regular file or directory whose bytes match the source. `apply` replaces it with a symlink
- `regular-differs`: dest bytes do not match the source. `apply` prints `ABORT` for that run and writes no destination
- `wrong-symlink` / `broken-symlink`: dest is a symlink whose target is not the source. `apply` recreates the symlink
- `copy-differs`: Claude thin shell bytes differ. `apply` overwrites from the tracked source

A destination whose relative path contains `..`, or that would escape `--home`, MUST be rejected before any write.

### Item E. Outside this installer

The following adapters are not materialized here:

- Claude Code `.claude/rules/*.md` with `paths:` globs
- Cursor `.mdc` files with `globs`
- Grok PreToolUse language gate

Until those exist, the executing Agent opens the matching scenario file under `hooks/criteria/` and the files listed in its `load:`.
