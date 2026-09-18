"""Unit tests for merge request label computation."""

import pytest
from labels import compute_labels
from labels import label_names
from labels import project_path
from labels import validate_tables


def _cfg() -> dict:
    return {
        "allowlist": [
            "type::feature",
            "type::adhoc",
            "type::fix",
            "area::CI",
            "area::infrastructure",
            "security",
        ],
        "type_from_conv": {
            "feat": "type::feature",
            "ci": "type::adhoc",
            "fix": "type::fix",
        },
        "repo_area": {
            "csning1998-lab/personal/generic-agent-criteria-source": "area::CI"
        },
        "area_patterns": [
            {
                "pattern": "terraform|hook|selinux",
                "label": "area::infrastructure",
            }
        ],
        "title_contains": [{"needle": "selinux", "add": "security"}],
        "keep_exact": ["security"],
        "keep_prefixes": [],
        "rename": {},
        "bang_adds": "breaking-change",
    }


def test_feat_hooks_is_infrastructure_and_feature() -> None:
    """feat(hooks) maps type from title and area from the hook pattern."""
    labels = compute_labels(
        "feat(hooks): add IaC collaboration gate",
        ["security"],
        "csning1998-lab/personal/generic-agent-criteria-source",
        _cfg(),
    )
    assert labels == [
        "area::infrastructure",
        "security",
        "type::feature",
    ]


def test_ci_title_without_terraform_uses_repo_area() -> None:
    """ci: titles without an area pattern fall back to repo_area."""
    labels = compute_labels(
        "ci: add markdownlint job",
        [],
        "csning1998-lab/personal/generic-agent-criteria-source",
        _cfg(),
    )
    assert "type::adhoc" in labels
    assert "area::CI" in labels


def test_selinux_adds_security() -> None:
    """A selinux needle adds the orthogonal security label."""
    labels = compute_labels(
        "fix(hypervisor): resolve SELinux AVC",
        [],
        "csning1998-lab/personal/on-premise-gitlab-deployment",
        _cfg(),
    )
    assert "type::fix" in labels
    assert "security" in labels
    assert "area::infrastructure" in labels


def test_rename_target_outside_allowlist_raises() -> None:
    """A rename target missing from allowlist is a table error."""
    cfg = _cfg()
    cfg["rename"] = {"pending": "status::pending"}
    with pytest.raises(ValueError, match="rename target not in allowlist"):
        compute_labels(
            "fix: x",
            ["pending"],
            "group/repo",
            cfg,
        )


def test_validate_tables_rejects_bad_regex() -> None:
    """Invalid area_patterns regex fails before any merge request."""
    cfg = _cfg()
    cfg["area_patterns"] = [{"pattern": "(", "label": "area::CI"}]
    assert validate_tables(cfg) is not None
    assert validate_tables(_cfg()) is None
    assert validate_tables({}) == "tables.allowlist missing"


def test_label_names_and_project_path() -> None:
    """GitLab API shapes map onto name strings and a group/repo path."""
    assert label_names([{"name": "type::fix"}]) == ["type::fix"]
    assert label_names(["area::CI"]) == ["area::CI"]
    assert (
        project_path({"web_url": ("https://gitlab.com/g/r/-/merge_requests/1")})
        == "g/r"
    )
