"""Security boundary tests for the Antigravity replace module."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
import replace


@pytest.mark.parametrize(
    "version",
    ["../evil", "1.0/../../x", "a/b", "", "..", "-rf", "1.0 0"],
)
def test_validate_version_rejects_traversal(version: str) -> None:
    """Version strings capable of escaping the backup directory fail."""
    with pytest.raises(ValueError, match="Invalid version string"):
        replace.validate_version(version)


@pytest.mark.parametrize("version", ["1.0.0", "unknown", "2.3.4-rc1+build5"])
def test_validate_version_accepts_normal(version: str) -> None:
    """Ordinary version strings pass unchanged."""
    assert replace.validate_version(version) == version


def test_validate_install_root_rejects_outside_locations() -> None:
    """Roots outside home and /opt raise ValueError."""
    for raw in ("/", "/etc", "/usr/local/x", "/tmp/x", None, ""):
        with pytest.raises(ValueError):
            replace.validate_install_root(raw)


def test_validate_install_root_rejects_shallow_home_paths() -> None:
    """Home itself and direct home children are rejected."""
    with pytest.raises(ValueError):
        replace.validate_install_root("~")
    with pytest.raises(ValueError):
        replace.validate_install_root("~/Documents")


def test_validate_install_root_accepts_expected_roots() -> None:
    """Typical IDE and Hub roots pass."""
    ide = replace.validate_install_root("~/.local/share/antigravity-ide")
    assert ide.name == "antigravity-ide"
    hub = replace.validate_install_root("/opt/antigravity/Antigravity-x64")
    assert str(hub) == "/opt/antigravity/Antigravity-x64"


def test_validate_install_root_rejects_symlink_escape(tmp_path: Path) -> None:
    """A symlink under home resolving outside allowed bases is rejected."""
    home = tmp_path / "home"
    (home / ".local/share").mkdir(parents=True)
    link = home / ".local/share/escape"
    link.symlink_to("/etc")
    with patch("pathlib.Path.home", return_value=home):
        with pytest.raises(ValueError):
            replace.validate_install_root(str(link))


def _build_curl_mock(*responses: str):
    iterator = iter(responses)

    def fake(cmd: list[str], text: bool = True) -> str:
        assert "--proto" in cmd and "=https" in cmd
        assert "--max-redirs" in cmd
        return next(iterator)

    return fake


def test_download_archive_success(tmp_path: Path) -> None:
    """A 200 response completes without further hops."""
    with patch(
        "subprocess.check_output", side_effect=_build_curl_mock("200 ")
    ) as mock_out:
        replace.download_archive(
            "https://dl.google.com/a.tar.gz", tmp_path / "a.tar.gz"
        )
    assert mock_out.call_count == 1


def test_download_archive_rejects_redirect_to_foreign_host(
    tmp_path: Path,
) -> None:
    """Redirect to a non-official host is rejected before the next fetch."""
    responses = _build_curl_mock("302 https://evil.example.com/x.tar.gz")
    with patch("subprocess.check_output", side_effect=responses) as mock_out:
        with pytest.raises(ValueError, match="is not in official hosts"):
            replace.download_archive(
                "https://dl.google.com/a.tar.gz", tmp_path / "a.tar.gz"
            )
    assert mock_out.call_count == 1


def test_download_archive_follows_official_redirect(tmp_path: Path) -> None:
    """Redirect between official hosts is followed."""
    responses = _build_curl_mock(
        "302 https://edgedl.me.gvt1.com/b.tar.gz", "200 "
    )
    with patch("subprocess.check_output", side_effect=responses) as mock_out:
        replace.download_archive(
            "https://dl.google.com/a.tar.gz", tmp_path / "a.tar.gz"
        )
    assert mock_out.call_count == 2


def test_download_archive_redirect_loop_is_bounded(tmp_path: Path) -> None:
    """Endless official redirects terminate with RuntimeError."""
    loop = "302 https://dl.google.com/a.tar.gz"
    responses = _build_curl_mock(*([loop] * (replace.MAX_REDIRECTS + 2)))
    with patch("subprocess.check_output", side_effect=responses):
        with pytest.raises(RuntimeError, match="Too many redirects"):
            replace.download_archive(
                "https://dl.google.com/a.tar.gz", tmp_path / "a.tar.gz"
            )


def test_download_archive_http_error(tmp_path: Path) -> None:
    """Non-2xx non-redirect status raises RuntimeError."""
    with patch("subprocess.check_output", side_effect=_build_curl_mock("404 ")):
        with pytest.raises(RuntimeError, match="HTTP 404"):
            replace.download_archive(
                "https://dl.google.com/a.tar.gz", tmp_path / "a.tar.gz"
            )


def test_verify_sha256_match_and_mismatch(tmp_path: Path) -> None:
    """Matching digest passes and mismatching digest raises."""
    target = tmp_path / "f.bin"
    target.write_bytes(b"payload")
    good = hashlib.sha256(b"payload").hexdigest()
    replace.verify_sha256(target, good.upper())
    with pytest.raises(ValueError, match="sha256 mismatch"):
        replace.verify_sha256(target, "0" * 64)
    with pytest.raises(ValueError, match="64 hex"):
        replace.verify_sha256(target, "abc")


def test_stop_main_pid_ignores_substring_matches() -> None:
    """A process merely mentioning the path in an argument is not killed."""
    ps_output = (
        " 200    1 vim /opt/app/bin/antigravity\n"
        " 201    1 /opt/app/bin/antigravity-other\n"
    )
    with (
        patch("subprocess.check_output", return_value=ps_output),
        patch("os.kill") as mock_kill,
    ):
        replace.stop_main_pid("/opt/app/bin/antigravity")
    mock_kill.assert_not_called()


def test_commit_product_rejects_traversal_version(tmp_path: Path) -> None:
    """commit_product refuses a version that would escape the parent."""
    root = tmp_path / "antigravity-ide"
    root.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    staging = tmp_path / ".staging"
    (staging / "tree").mkdir(parents=True)
    with patch("replace.stop_main_pid"):
        with pytest.raises(ValueError, match="Invalid version string"):
            replace.commit_product("ide", staging, root, "../victim", False)
    assert victim.is_dir()
    assert root.is_dir()


def test_sandbox_symlink_is_not_chmodded(tmp_path: Path) -> None:
    """A chrome-sandbox symlink in the archive never reaches os.chmod."""
    root = tmp_path / "antigravity-ide"
    staging = tmp_path / ".staging"
    tree = staging / "tree"
    tree.mkdir(parents=True)
    target = tmp_path / "outside"
    target.write_bytes(b"x")
    (tree / "chrome-sandbox").symlink_to(target)
    with (
        patch("replace.stop_main_pid"),
        patch("os.chmod") as mock_chmod,
    ):
        replace.commit_product("ide", staging, root, "1.0.0", False)
    mock_chmod.assert_not_called()
