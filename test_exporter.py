import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import zipfile

import lz4.block
import msgpack

from capture import AccountCapture
from exporter import save_snapshot, verify_export
from protocol import inspect_snapshot


def packed(*values):
    return b"".join(msgpack.packb(x, use_bin_type=True) for x in values)


def fixture(uid=123):
    return [
        None,
        [[0, [uid, 10]], [4, [111, 110010, 5]], [11, [222, 220030, 2]], None],
        [],
        [],
        [],
    ]


def flow(
    path,
    method,
    request=b"",
    response=None,
    host="lb-api.wds-stellarium.com",
    token="session",
):
    return SimpleNamespace(
        request=SimpleNamespace(
            host=host,
            url="https://" + host + path,
            method=method,
            content=request,
            headers={"Authorization": "Bearer " + token, "X-Client-Version": "test"},
        ),
        response=SimpleNamespace(
            content=response if response is not None else packed(*fixture()),
            status_code=200,
        ),
    )


class ExportTests(unittest.TestCase):
    def test_roundtrip_and_allowlisted_archive(self):
        body = packed(*fixture())
        with tempfile.TemporaryDirectory() as root:
            path, manifest = save_snapshot(
                root, body, hashlib.sha256(b"login").hexdigest()
            )
            self.assertEqual(verify_export(path), manifest)
            self.assertEqual(manifest["summary"]["Character"], 1)
            with zipfile.ZipFile(path) as z:
                self.assertEqual(z.read("user-data.response.bin"), body)
                self.assertEqual(
                    set(z.namelist()),
                    {"manifest.json", "user-data.response.bin", "account-bridge.json"},
                )

    def test_both_compression_encodings(self):
        values = fixture()
        raw = packed(values[1])
        compressed = lz4.block.compress(raw, store_size=False)
        v99 = msgpack.ExtType(99, packed(len(raw)) + compressed)
        v98 = [msgpack.ExtType(98, packed(len(raw))), compressed]
        for value in (v99, v98):
            self.assertEqual(
                inspect_snapshot(packed(None, value, [], [], [])),
                inspect_snapshot(packed(*values)),
            )

    def test_reject_fault_truncation_and_malformed_account(self):
        cases = [
            packed(["error"], [], [], [], []),
            packed(None, [], [], [], []),
            packed(*fixture()) + b"\xd9",
            packed(None, [[0, [123]], [0, [456]]], [], [], []),
            packed(None, [msgpack.ExtType(98, packed(100, 200)), b"x"], [], [], []),
        ]
        for body in cases:
            with self.subTest(body=body), self.assertRaises(Exception):
                inspect_snapshot(body)

    def test_token_matching_and_no_secret_persistence(self):
        with tempfile.TemporaryDirectory() as root:
            logs = []
            capture = AccountCapture(root, logs.append)
            capture.response(
                flow(
                    "/api/Account/Authenticate",
                    "POST",
                    packed(["PRIVATE_LOGIN", 1, None, None, "test"]),
                    packed(None, ["PRIVATE_SESSION", 0, None], [], [], []),
                )
            )
            capture.response(flow("/api/data/user", "GET", token="PRIVATE_SESSION"))
            capture.response(flow("/api/data/user", "GET", token="PRIVATE_SESSION"))
            paths = list(Path(root).glob("*.zip"))
            self.assertEqual(len(paths), 1)
            self.assertTrue(verify_export(paths[0])["login_bridge_available"])
            with zipfile.ZipFile(paths[0]) as z:
                content = b"".join(z.read(n) for n in z.namelist())
                self.assertNotIn(b"PRIVATE_LOGIN", content)
                self.assertNotIn(b"PRIVATE_SESSION", content)
            self.assertNotIn("PRIVATE_LOGIN", "".join(logs))
            self.assertNotIn("PRIVATE_SESSION", "".join(logs))
            # A second account/session must not inherit the first login bridge.
            capture.response(
                flow(
                    "/api/data/user",
                    "GET",
                    response=packed(*fixture(456)),
                    token="other-session",
                )
            )
            manifests = [verify_export(p) for p in Path(root).glob("*.zip")]
            self.assertFalse(
                next(m for m in manifests if m["user_id"] == 456)[
                    "login_bridge_available"
                ]
            )

    def test_other_hosts_paths_and_failed_responses_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            capture = AccountCapture(root, lambda _: None)
            for item in [
                flow("/api/data/user", "GET", host="unrelated.example"),
                flow("/api/data/user", "POST"),
                flow("/api/Other", "GET"),
                flow(
                    "/api/data/user",
                    "GET",
                    host="lb-api.wds-stellarium.com.attacker.example",
                ),
            ]:
                capture.response(item)
            bad = flow("/api/data/user", "GET")
            bad.response.status_code = 500
            capture.response(bad)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_tamper_detection(self):
        with tempfile.TemporaryDirectory() as root:
            path, _ = save_snapshot(root, packed(*fixture()))
            with zipfile.ZipFile(path) as z:
                files = {n: z.read(n) for n in z.namelist()}
            files["user-data.response.bin"] = packed(*fixture(999))
            with zipfile.ZipFile(path, "w") as z:
                for name, body in files.items():
                    z.writestr(name, body)
            with self.assertRaises(ValueError):
                verify_export(path)


if __name__ == "__main__":
    unittest.main()
