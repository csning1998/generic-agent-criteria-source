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

# The credential-distributor Vault Proxy of the repository owner reads the analysis token.
# The subshell keeps the Proxy environment off every other command.
if ! command -v vault-proxy-env >/dev/null; then
    echo "vault-proxy-env is missing, run the first menu item of ./governance in parent-group-governance" >&2
    exit 1
fi
proxy_env=$(vault-proxy-env credential-distributor-generic-agent-criteria-source)
sonar_token=$(eval "${proxy_env}" && vault kv get -mount=secret -field="${sonar_token_field}" "${sonar_token_path}")
unset proxy_env

# The scanner receives copies of the analyzed trees alone through podman cp, since the Python indexer walks the
# whole base directory. The copies carry the labels of the container, and the root .gitignore drives the SCM
# exclusion.
scanner=$(SONAR_TOKEN="${sonar_token}" podman create --network host \
    -e SONAR_HOST_URL="${sonar_host_url}" \
    -e SONAR_TOKEN \
    -e SONAR_SCANNER_OPTS="-Dsonar.projectKey=${sonar_project_key} -Dsonar.projectBaseDir=/usr/src -Dsonar.qualitygate.wait=true -Dsonar.sources=hooks,skills,terraform -Dsonar.exclusions=**/.terraform/**,**/__pycache__/** -Dsonar.tests=tests -Dsonar.test.inclusions=tests/test_*.py -Dsonar.python.coverage.reportPaths=coverage.xml -Dsonar.python.version=3.11,3.12,3.13,3.14" \
    "${scanner_image}")
tar -c --exclude=node_modules -- coverage.xml hooks skills tests terraform .git .gitignore | podman cp - "${scanner}:/usr/src" \
    || { podman rm -f "${scanner}" >/dev/null; exit 1; }
scan_status=0
podman start --attach "${scanner}" || scan_status=$?
podman rm "${scanner}" >/dev/null
[ "${scan_status}" -eq 0 ] || exit "${scan_status}"

echo "sonar: ${sonar_project_key}"
