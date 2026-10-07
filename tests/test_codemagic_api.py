#!/usr/bin/env python3
"""Offline contract and credential tests; never starts a real build."""

import contextlib
import io
import json
import os
import stat
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import codemagic_api as cm

APP = "a" * 24
BUILD = "b" * 24
TEAM = "c" * 24


class Response:
    status = 200

    def __init__(self, value):
        self.raw = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self.raw


class Tests(unittest.TestCase):
    def args(self, *args):
        return cm.parser().parse_args(args)

    def test_start_is_current_v3_contract(self):
        args = self.args(
            "start", "--app", APP, "--workflow", "ios", "--branch", "feature/a", "--label", "test"
        )
        with patch.object(cm, "request") as call:
            cm.run(args)
        call.assert_called_once_with(
            "POST",
            f"/apps/{APP}/builds",
            {"workflow_id": "ios", "branch": "feature/a", "labels": ["test"]},
            dry_run=False,
        )

    def test_start_requires_one_ref(self):
        for refs in ([], ["--branch", "main", "--tag", "v1"]):
            with (
                self.subTest(refs=refs),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                self.args("start", "--app", APP, "--workflow", "ios", *refs)

    def test_dry_run_needs_no_token_or_network(self):
        with (
            patch.object(cm, "token_source", side_effect=AssertionError("read token")),
            patch.object(cm.urllib.request, "build_opener", side_effect=AssertionError("network")),
        ):
            result = cm.run(
                self.args("start", "--app", APP, "--workflow", "ios", "--tag", "v1", "--dry-run")
            )
        self.assertFalse(result["sent"])
        self.assertEqual(result["body"], {"workflow_id": "ios", "tag": "v1"})
        self.assertEqual(result["url"], f"https://codemagic.io/api/v3/apps/{APP}/builds")

    def test_cancel_uses_documented_legacy_endpoint(self):
        result = cm.run(self.args("cancel", BUILD, "--dry-run"))
        self.assertEqual(result["url"], f"https://api.codemagic.io/builds/{BUILD}/cancel")
        self.assertEqual(result["method"], "POST")

    def test_personal_and_team_apps_are_distinct(self):
        for args, path in (
            (["apps"], "/user/apps"),
            (["apps", "--team", TEAM, "--page", "2"], f"/teams/{TEAM}/apps"),
        ):
            with patch.object(cm, "request") as call:
                cm.run(self.args(*args))
                self.assertEqual(call.call_args.args[1], path)

    def test_build_pagination_and_filters(self):
        with patch.object(cm, "request") as call:
            cm.run(
                self.args(
                    "builds",
                    "--team",
                    TEAM,
                    "--app",
                    APP,
                    "--branch",
                    "feature/a",
                    "--cursor",
                    BUILD,
                )
            )
        query = call.call_args.kwargs["query"]
        self.assertEqual(query["app_id"], APP)
        self.assertEqual(query["cursor"], BUILD)
        self.assertIn("branch=feature%2Fa", cm.api_url("/builds", query=query))

    def test_reject_arbitrary_hosts_and_traversal(self):
        for path in (
            "https://example.com/",
            "//example.com/",
            "/../",
            "/%2e%2e/",
            "/user/teams#x",
            "/x\ny",
        ):
            with self.subTest(path=path), self.assertRaises(cm.ClientError):
                cm.request("GET", path, dry_run=True)

    def test_redirect_refused(self):
        with self.assertRaises(cm.ClientError):
            cm.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")

    @unittest.skipUnless(os.name == "posix", "POSIX token-file permissions")
    def test_credential_storage_and_env_precedence(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}, clear=True),
        ):
            path = cm.save_token("test-token")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(cm.token_source(), ("test-token", str(path)))
            with patch.dict(
                os.environ,
                {
                    "CM_API_TOKEN": "third",
                    "CODEMAGIC_API_TOKEN": "second",
                    "CODEMAGIC_API_KEY": "first",
                },
            ):
                self.assertEqual(cm.token_source(), ("first", "CODEMAGIC_API_KEY"))
            path.chmod(0o644)
            with self.assertRaises(cm.ClientError):
                cm.token_source()

    @unittest.skipUnless(os.name == "posix", "POSIX token-file storage")
    def test_login_validates_before_replacing_credentials(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}, clear=True),
        ):
            path = cm.save_token("existing-token")
            with (
                patch.object(cm.sys, "stdin", io.StringIO("invalid-token")),
                patch.object(cm, "request", side_effect=cm.ClientError("401")),
                self.assertRaises(cm.ClientError),
            ):
                cm.run(self.args("auth", "login", "--stdin"))
            self.assertEqual(path.read_text().strip(), "existing-token")

    def test_headers_and_response_redaction(self):
        payload = {
            "data": {
                "id": BUILD,
                "secret": "hidden",
                "variables": {"CUSTOM_NAME": "value"},
                "text": "echo test-token",
            }
        }
        with patch.object(cm.urllib.request, "build_opener") as build:
            build.return_value.open.return_value = Response(json.dumps(payload).encode())
            result = cm.request("GET", f"/builds/{BUILD}", token="test-token")
            req = build.return_value.open.call_args.args[0]
        self.assertEqual(req.get_header("X-auth-token"), "test-token")
        self.assertNotIn("test-token", json.dumps(result))
        self.assertEqual(result["data"]["variables"]["CUSTOM_NAME"], "[redacted]")

    def test_mutation_network_failure_is_never_retried(self):
        with patch.object(cm.urllib.request, "build_opener") as build:
            build.return_value.open.side_effect = urllib.error.URLError("offline")
            with self.assertRaisesRegex(cm.ClientError, "Outcome unknown"):
                cm.request("POST", f"/apps/{APP}/builds", {}, token="test-token")
            self.assertEqual(build.return_value.open.call_count, 1)

    def test_rate_limit_and_error_body_secrets_are_not_dumped(self):
        error = urllib.error.HTTPError(
            cm.BASE,
            429,
            "limited",
            {"ratelimit-reset": "120"},
            io.BytesIO(b'{"detail":"sensitive-value"}'),
        )
        with patch.object(cm.urllib.request, "build_opener") as build:
            build.return_value.open.side_effect = error
            with self.assertRaisesRegex(cm.ClientError, "120 seconds") as result:
                cm.request("GET", "/user/teams", token="test-token")
        self.assertNotIn("sensitive-value", str(result.exception))

    def test_208_cancel_response_need_not_be_json(self):
        response = Response(b"Already reported")
        response.status = 208
        with patch.object(cm.urllib.request, "build_opener") as build:
            build.return_value.open.return_value = response
            result = cm.request("POST", f"/builds/{BUILD}/cancel", legacy=True, token="test-token")
        self.assertEqual(result, {"status_code": 208, "already_finished": True})

    def test_environment_values_are_redacted_in_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "env.json"
            path.write_text(
                json.dumps({"variables": {"CUSTOM_NAME": "sensitive-value"}, "groups": ["staging"]})
            )
            result = cm.run(
                self.args(
                    "start",
                    "--app",
                    APP,
                    "--workflow",
                    "ios",
                    "--branch",
                    "main",
                    "--environment-file",
                    str(path),
                    "--dry-run",
                )
            )
        self.assertEqual(result["body"]["environment"]["groups"], ["staging"])
        self.assertNotIn("sensitive-value", json.dumps(result))

    def test_bad_environment_and_ids_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.args("build", "../unsafe")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"softwareVersions": {"flutter": "stable"}}')
            with self.assertRaises(cm.ClientError):
                cm.run(
                    self.args(
                        "start",
                        "--app",
                        APP,
                        "--workflow",
                        "ios",
                        "--branch",
                        "main",
                        "--environment-file",
                        str(path),
                        "--dry-run",
                    )
                )


if __name__ == "__main__":
    unittest.main()
