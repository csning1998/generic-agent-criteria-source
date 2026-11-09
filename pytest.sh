#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Execution PATH MUST include ~/.local/bin to discover user-installed toolchains.
export PATH="${HOME}/.local/bin:${PATH}"

# The SonarQube project key is the GitLab project path with slashes replaced by hyphens.
# The analysis token path is the frozen CI bot in parent-group-governance.
origin_url="$(git remote get-url origin)"
sonar_project_key="$(printf '%s\n' "$origin_url" | sed -E 's#^(git@[^:]+:|https?://[^/]+/)##')"
sonar_project_key="${sonar_project_key%.git}"
sonar_project_key="${sonar_project_key//\//-}"
readonly sonar_project_key
readonly sonar_token_path="parent-group-governance/sonarqube/ci-analysis-bot"
readonly sonar_token_field="sonarqube_ci_token"
readonly scanner_image="docker.io/sonarsource/sonar-scanner-cli:12.1.0.3225_8.0.1"
readonly sonar_host_url="${SONAR_HOST_URL:-http://127.0.0.1:9000}"

uv run ruff check .

# relative_files keeps coverage paths aligned with the scanner mount at /usr/src.
coverage_rc=$(mktemp)
trap 'rm -f "$coverage_rc"' EXIT
printf '[run]\nrelative_files = True\n' >"$coverage_rc"
PYTHONDONTWRITEBYTECODE=1 COVERAGE_FILE="${coverage_rc}.data" uv run --with pytest-cov \
    pytest -q -p no:cacheprovider \
    --cov=hooks --cov=skills \
    --cov-config="$coverage_rc" --cov-report=xml:coverage.xml
rm -f "${coverage_rc}.data"

# The analysis MUST be skipped when SonarQube does not report UP, since the Bastion Vault and the token may not exist yet.
if ! curl -fsS --max-time 5 "${sonar_host_url}/api/system/status" 2>/dev/null | grep -q '"status":"UP"'; then
    echo "skipped: SonarQube at ${sonar_host_url} is not UP" >&2
# The analysis MUST be skipped on uncommitted sources, since a file without git blame counts entirely as new code.
elif [[ -n "$(git status --porcelain -- hooks skills tests terraform)" ]]; then
    echo "skipped: hooks, skills, tests, or terraform holds uncommitted changes, commit them before the SonarQube analysis" >&2
else
    # Token resolution MUST isolate proxy environment evaluation to prevent variable leaks and capture execution failures.
    if [[ -z "${SONAR_TOKEN:-}" ]]; then
        if ! command -v vault-proxy-env >/dev/null; then
            echo "vault-proxy-env is missing, run the first menu item of ./governance in parent-group-governance" >&2
            exit 1
        fi
        proxy_env=$(vault-proxy-env credential-distributor-generic-agent-criteria-source)
        sonar_token=$(eval "${proxy_env}" && vault kv get -mount=secret -field="${sonar_token_field}" "${sonar_token_path}")
        unset proxy_env
    else
        sonar_token="${SONAR_TOKEN}"
    fi

    # Ingesting sources via podman cp assigns container SELinux labels without host bind mounts.
    # Exit traps purge stored container state holding SONAR_TOKEN.
    scanner=""
    remove_scanner() { if [ -n "${scanner}" ]; then podman rm -f "${scanner}" >/dev/null 2>&1 || true; scanner=""; fi; }
    trap 'rm -f "$coverage_rc"; remove_scanner' EXIT
    trap 'remove_scanner; exit 130' INT TERM
    scanner=$(SONAR_TOKEN="${sonar_token}" podman create --network host \
        -e SONAR_HOST_URL="${sonar_host_url}" \
        -e SONAR_TOKEN \
        -e SONAR_SCANNER_OPTS="-Dsonar.projectKey=${sonar_project_key} -Dsonar.projectName=${sonar_project_key} -Dsonar.projectBaseDir=/usr/src -Dsonar.qualitygate.wait=true -Dsonar.sources=hooks,skills,terraform -Dsonar.exclusions=**/.terraform/**,**/__pycache__/**,**/.pytest_cache/**,**/.ruff_cache/**,coverage.xml -Dsonar.tests=tests -Dsonar.test.inclusions=tests/test_*.py -Dsonar.python.coverage.reportPaths=coverage.xml -Dsonar.python.version=3.11,3.12,3.13,3.14" \
        "${scanner_image}")
    {
        git ls-files -z --cached --others --exclude-standard -- hooks skills tests terraform sonar-project.properties .gitignore
        printf '%s\0' .git
        if [ -e coverage.xml ]; then printf '%s\0' coverage.xml; fi
    } | tar -c --null --ignore-failed-read -T - | podman cp - "${scanner}:/usr/src" \
        || { podman rm -f "${scanner}" >/dev/null; exit 1; }
    scan_status=0
    podman start --attach "${scanner}" || scan_status=$?
    podman rm "${scanner}" >/dev/null
    [ "${scan_status}" -eq 0 ] || exit "${scan_status}"

    echo "sonar: ${sonar_project_key}"
fi
