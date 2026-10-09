#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

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

# The governance Vault Proxy reads the analysis token. Each separate assignment stops the run on a failure.
# A nested eval would hide that failure. The subshell keeps the Proxy environment off every other command.
if ! command -v vault-proxy-env >/dev/null; then
    echo "vault-proxy-env is missing, run the first menu item of ./governance in parent-group-governance" >&2
    exit 1
fi
proxy_env=$(vault-proxy-env governance)
sonar_token=$(eval "${proxy_env}" && vault kv get -mount=secret -field="${sonar_token_field}" "${sonar_token_path}")
unset proxy_env

# The scanner mounts only the analyzed trees read-only, since the Python indexer walks the whole base directory.
# The root .gitignore drives the SCM exclusion.
SONAR_TOKEN="${sonar_token}" podman run --rm --network host \
    --security-opt label=type:spc_t \
    -e SONAR_HOST_URL="${sonar_host_url}" \
    -e SONAR_TOKEN \
    -e SONAR_SCANNER_OPTS="-Dsonar.projectKey=${sonar_project_key} -Dsonar.projectBaseDir=/usr/src -Dsonar.qualitygate.wait=true -Dsonar.sources=hooks,skills,terraform -Dsonar.exclusions=**/.terraform/**,**/__pycache__/** -Dsonar.tests=tests -Dsonar.test.inclusions=tests/test_*.py -Dsonar.python.coverage.reportPaths=coverage.xml" \
    -v "$PWD/coverage.xml:/usr/src/coverage.xml:ro" \
    -v "$PWD/hooks:/usr/src/hooks:ro" \
    -v "$PWD/skills:/usr/src/skills:ro" \
    -v "$PWD/tests:/usr/src/tests:ro" \
    -v "$PWD/terraform:/usr/src/terraform:ro" \
    -v "$PWD/.git:/usr/src/.git:ro" \
    -v "$PWD/.gitignore:/usr/src/.gitignore:ro" \
    "${scanner_image}"

echo "sonar: ${sonar_project_key}"
