"""Path classification rules for the non-IaC mutating SQL guard."""

from __future__ import annotations


DOC_AND_DATA_SUFFIXES = frozenset(
    {
        ".md",
        ".markdown",
        ".mdx",
        ".rst",
        ".adoc",
        ".txt",
        ".json",
        ".jsonl",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".csv",
        ".tsv",
        ".svg",
        ".xml",
        ".html",
        ".htm",
        ".lock",
        ".sum",
        ".mod",
        ".hcl",
        ".env",
        ".envrc",
    }
)
SCRIPT_AND_SQL_SUFFIXES = frozenset(
    {
        ".sh",
        ".bash",
        ".zsh",
        ".ksh",
        ".fish",
        ".ps1",
        ".sql",
        ".mk",
    }
)
BUILD_AND_CI_NAMES = frozenset(
    {
        "makefile",
        "gnumakefile",
        "justfile",
        "jenkinsfile",
        "dockerfile",
        "containerfile",
        "taskfile.yml",
        "taskfile.yaml",
        "compose.yml",
        "compose.yaml",
    }
)
BUILD_AND_CI_PREFIXES = (
    "makefile.",
    "dockerfile.",
    "containerfile.",
    ".gitlab-ci.",
    "azure-pipelines.",
    "bitbucket-pipelines.",
    "docker-compose.",
)
EXECUTABLE_AND_CI_DIRS = frozenset(
    {
        "scripts",
        "script",
        "bin",
        ".githooks",
        ".circleci",
        ".buildkite",
        "ci",
        ".ci",
    }
)
CI_DIR_PAIRS = frozenset(
    {
        (".github", "workflows"),
        (".gitlab", "ci"),
    }
)
