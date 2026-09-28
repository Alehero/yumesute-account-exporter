"""Write immutable, self-contained snapshots; never save authentication tokens."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import uuid
import zipfile

from protocol import inspect_snapshot

FORMAT = "yumesute-account-export"
VERSION = 1


def save_snapshot(root, body, login_hash=None, client_version=None):
    summary = inspect_snapshot(body)
    now = datetime.now(timezone.utc)
    manifest = {
        "format": FORMAT,
        "format_version": VERSION,
        "exporter_version": "0.1.0",
        "captured_at": now.isoformat(),
        "source": "official-api-passive-capture",
        "endpoint": "GET /api/data/user",
        "client_version": client_version,
        "snapshot_sha256": sha256(body).hexdigest(),
        "login_bridge_available": login_hash is not None,
        **summary,
    }
    if login_hash is not None and (
        len(login_hash) != 64 or any(c not in "0123456789abcdef" for c in login_hash)
    ):
        raise ValueError("Invalid login token hash")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    dest = (
        root
        / f"yumesute-{summary['user_id']}-{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}.zip"
    )
    temp = dest.with_suffix(".tmp")
    try:
        with temp.open("xb") as handle:
            with zipfile.ZipFile(
                handle, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.writestr(
                    "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2)
                )
                archive.writestr("user-data.response.bin", body)
                if login_hash:
                    archive.writestr(
                        "account-bridge.json",
                        json.dumps(
                            {"user_id": summary["user_id"], "token_sha256": login_hash}
                        ),
                    )
        temp.chmod(0o600)
        verify_export(temp)
        temp.replace(dest)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return dest, manifest


def verify_export(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        allowed = {"manifest.json", "user-data.response.bin", "account-bridge.json"}
        if (
            len(names) != len(set(names))
            or not set(names) <= allowed
            or not {"manifest.json", "user-data.response.bin"} <= set(names)
        ):
            raise ValueError("Unexpected export contents")
        if any(i.file_size > 64 * 1024 * 1024 for i in archive.infolist()):
            raise ValueError("Oversized export entry")
        manifest = json.loads(archive.read("manifest.json"))
        body = archive.read("user-data.response.bin")
        if (
            manifest.get("format") != FORMAT
            or manifest.get("format_version") != VERSION
        ):
            raise ValueError("Unsupported export format")
        if sha256(body).hexdigest() != manifest["snapshot_sha256"]:
            raise ValueError("Snapshot checksum mismatch")
        summary = inspect_snapshot(body)
        if any(manifest.get(k) != v for k, v in summary.items()):
            raise ValueError("Snapshot summary mismatch")
        if manifest.get("login_bridge_available") != ("account-bridge.json" in names):
            raise ValueError("Bridge declaration mismatch")
        if "account-bridge.json" in names:
            bridge = json.loads(archive.read("account-bridge.json"))
            digest = bridge.get("token_sha256", "")
            if (
                bridge.get("user_id") != summary["user_id"]
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
            ):
                raise ValueError("Invalid account bridge")
        return manifest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify an account export without contacting any server."
    )
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    result = verify_export(args.archive)
    print(
        "Verified:",
        result["entries"],
        "records;",
        result["summary"]["Character"],
        "actors;",
        result["summary"]["Poster"],
        "posters",
    )
