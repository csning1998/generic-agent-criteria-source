"""Unit tests and boundary condition tests for Antigravity replace module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import replace


def test_validate_url_host_allowed() -> None:
    """Allowed Google hosts pass validation without exception."""
    for host in replace.OFFICIAL_HOSTS:
        replace.validate_url_host(f"https://{host}/some/archive.tar.gz")


def test_validate_url_host_rejected() -> None:
    """Unauthorized host raises ValueError."""
    with pytest.raises(ValueError, match="is not in official hosts"):
        replace.validate_url_host("https://malicious.example.com/bad.tar.gz")


def test_validate_url_host_subdomain_spoofing() -> None:
    """Subdomain spoofing targeting allowed host raises ValueError."""
    with pytest.raises(ValueError, match="is not in official hosts"):
        replace.validate_url_host(
            "https://storage.googleapis.com.evil.com/fake.tar.gz"
        )


def test_validate_url_host_case_insensitivity() -> None:
    """Mixed-case allowed hosts pass host validation."""
    replace.validate_url_host(
        "https://STORAGE.GOOGLEAPIS.COM/antigravity/archive.tar.gz"
    )


def test_validate_url_host_rejects_non_http_schemes() -> None:
    """File and non-http schemes raise ValueError."""
    with pytest.raises(ValueError, match="Scheme must be http or https"):
        replace.validate_url_host("file:///tmp/payload.tar.gz")


def test_load_payload_from_file_and_string(tmp_path: Path) -> None:
    """Verify load_payload parses raw JSON string or JSON file path."""
    data = {"op": "replace", "products": ["ide"]}
    raw_str = json.dumps(data)
    assert replace.load_payload(raw_str) == data

    target_file = tmp_path / "payload.json"
    target_file.write_text(raw_str, encoding="utf-8")
    assert replace.load_payload(str(target_file)) == data


def test_load_payload_invalid_inputs() -> None:
    """Malformed JSON string raises JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        replace.load_payload("{invalid-json}")


def test_replace_product_lifecycle(tmp_path: Path) -> None:
    """Verify replace_product stages, backs up old live root, and deploys."""
    install_root = tmp_path / "antigravity-ide"
    install_root.mkdir()
    (install_root / "antigravity-ide").write_text("bin", encoding="utf-8")

    def fake_subprocess_call(cmd: list[str]) -> None:
        if cmd[0] == "tar":
            extract_dir = Path(cmd[4])
            extract_dir.mkdir(parents=True, exist_ok=True)
            res_dir = extract_dir / "resources/app/resources/linux"
            res_dir.mkdir(parents=True, exist_ok=True)
            (res_dir / "code.png").write_bytes(b"icon_bytes")
            (extract_dir / "chrome-sandbox").write_bytes(b"sandbox")
            (extract_dir / "antigravity-ide").write_bytes(b"new_bin")

    with (
        patch("subprocess.check_call", side_effect=fake_subprocess_call),
        patch("replace.download_archive"),
        patch("replace.stop_main_pid"),
    ):
        bak = replace.replace_product(
            "ide",
            "https://storage.googleapis.com/test/ide.tar.gz",
            install_root,
            "1.0.0",
            False,
        )

    assert bak is not None
    assert Path(bak).name == "antigravity-ide.bak.1.0.0"
    assert (install_root / "antigravity-ide").read_text(
        encoding="utf-8"
    ) == "new_bin"
    icon = install_root / "resources/app/resources/linux/antigravity.png"
    assert icon.is_file()
    assert icon.read_bytes() == b"icon_bytes"


def test_replace_product_fresh_install_no_backup(tmp_path: Path) -> None:
    """Fresh install where root does not exist creates no backup."""
    install_root = tmp_path / "new-install"

    def fake_subprocess_call(cmd: list[str]) -> None:
        if cmd[0] == "tar":
            extract_dir = Path(cmd[4])
            extract_dir.mkdir(parents=True, exist_ok=True)
            (extract_dir / "antigravity").write_bytes(b"hub_bin")

    with (
        patch("subprocess.check_call", side_effect=fake_subprocess_call),
        patch("replace.download_archive"),
        patch("replace.stop_main_pid"),
    ):
        bak = replace.replace_product(
            "hub",
            "https://storage.googleapis.com/test/hub.tar.gz",
            install_root,
            "0.0.0",
            False,
        )

    assert bak is None
    assert (install_root / "antigravity").is_file()


def test_replace_product_cleans_existing_backup(tmp_path: Path) -> None:
    """Existing backup directory is purged before creating new backup."""
    install_root = tmp_path / "antigravity-ide"
    install_root.mkdir()
    (install_root / "antigravity-ide").write_text("current", encoding="utf-8")

    old_bak = tmp_path / "antigravity-ide.bak.1.0.0"
    old_bak.mkdir()
    (old_bak / "stale.txt").write_text("old", encoding="utf-8")

    def fake_subprocess_call(cmd: list[str]) -> None:
        if cmd[0] == "tar":
            extract_dir = Path(cmd[4])
            extract_dir.mkdir(parents=True, exist_ok=True)
            (extract_dir / "antigravity-ide").write_bytes(b"updated")

    with (
        patch("subprocess.check_call", side_effect=fake_subprocess_call),
        patch("replace.download_archive"),
        patch("replace.stop_main_pid"),
    ):
        bak = replace.replace_product(
            "ide",
            "https://storage.googleapis.com/test/ide.tar.gz",
            install_root,
            "1.0.0",
            False,
        )

    assert bak == str(old_bak)
    assert not (old_bak / "stale.txt").exists()
    assert (old_bak / "antigravity-ide").read_text(
        encoding="utf-8"
    ) == "current"


def test_replace_product_sandbox_chmod_fallback(tmp_path: Path) -> None:
    """PermissionError during chmod 4755 falls back to 0755."""
    install_root = tmp_path / "antigravity-ide"

    def fake_subprocess_call(cmd: list[str]) -> None:
        if cmd[0] == "tar":
            extract_dir = Path(cmd[4])
            extract_dir.mkdir(parents=True, exist_ok=True)
            (extract_dir / "chrome-sandbox").write_bytes(b"sandbox")

    def fake_chmod(path: Path, mode: int) -> None:
        if mode == 0o4755:
            raise PermissionError("Operation not permitted")

    with (
        patch("subprocess.check_call", side_effect=fake_subprocess_call),
        patch("replace.download_archive"),
        patch("replace.stop_main_pid"),
        patch("os.chmod", side_effect=fake_chmod) as mock_chmod,
    ):
        replace.replace_product(
            "ide",
            "https://storage.googleapis.com/test/ide.tar.gz",
            install_root,
            "1.0.0",
            False,
        )

    assert mock_chmod.call_count == 2
    assert mock_chmod.call_args_list[0][0][1] == 0o4755
    assert mock_chmod.call_args_list[1][0][1] == 0o755


def test_stop_main_pid_cold_start() -> None:
    """Non-existent process pattern exits cleanly without error."""
    with patch(
        "subprocess.check_output",
        return_value="  1   0 init\n  2   0 kthreadd\n",
    ):
        replace.stop_main_pid("/non/existent/path")


def test_stop_main_pid_handles_sigterm_and_cleanup() -> None:
    """Process tree roots receive SIGTERM and wait for termination."""
    ps_output = (
        " 100    1 /opt/app/bin/antigravity\n"
        " 101  100 /opt/app/bin/antigravity --type=zygote\n"
    )
    mock_kill = MagicMock()
    with (
        patch("subprocess.check_output", return_value=ps_output),
        patch("os.kill", mock_kill),
        patch("time.sleep"),
    ):
        replace.stop_main_pid("/opt/app/bin/antigravity")

    mock_kill.assert_any_call(100, 15)


def test_extract_asar_icon_missing_or_corrupt(tmp_path: Path) -> None:
    """Missing icon or corrupt asar returns False without raising exception."""
    corrupt_file = tmp_path / "corrupt.asar"
    corrupt_file.write_bytes(b"\x00" * 20)
    dest_png = tmp_path / "icon.png"

    assert replace.extract_asar_icon(corrupt_file, dest_png) is False


def test_main_emits_antigravity_result_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify main prints valid AntigravityResult JSON structure."""
    payload = {
        "op": "replace",
        "products": [],
    }
    with patch(
        "sys.argv",
        ["replace.py", "--payload", json.dumps(payload)],
    ):
        exit_code = replace.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["ok"] is True
    assert res["op"] == "replace"
    assert isinstance(res["backups"], list)


def test_main_handles_exception_and_emits_error_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Runtime failure emits ok: false and exit code 1."""
    payload = {
        "op": "replace",
        "products": ["ide"],
        "ide_url": "https://unauthorized.domain.org/hack.tar.gz",
        "ide_root": "/tmp/test-ide",
    }
    with patch(
        "sys.argv",
        ["replace.py", "--payload", json.dumps(payload)],
    ):
        exit_code = replace.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["ok"] is False
    assert "not in official hosts" in res["error"]
