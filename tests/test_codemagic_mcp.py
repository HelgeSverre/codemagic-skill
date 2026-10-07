"""Exercise MCP schemas, transport, and shared HTTP behavior without live mutations."""

import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import codemagic_api as api
from codemagic_mcp import create_server
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from test_codemagic_api import APP, BUILD, TEAM, Response
from test_distribution import builder


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_and_annotations(self):
        async with Client(create_server()) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        self.assertEqual(len(tools), 11)
        self.assertEqual(set(tools["get_build"].input_schema["required"]), {"build_id"})
        for name, tool in tools.items():
            writes = name in {"start_build", "cancel_build"}
            self.assertEqual(tool.annotations.read_only_hint, not writes)
            if writes:
                self.assertTrue(tool.annotations.destructive_hint)
                self.assertFalse(tool.annotations.idempotent_hint)
            self.assertNotIn("token", tool.input_schema["properties"])
            self.assertFalse(tool.input_schema["additionalProperties"])
            self.assertIsNotNone(tool.output_schema)
        self.assertFalse(tools["preview_build"].annotations.open_world_hint)

    async def test_preview_matches_cli_and_redacts_without_auth_or_network(self):
        with (
            patch.object(api, "token_source", side_effect=AssertionError("credentials read")),
            patch.object(api.urllib.request, "build_opener", side_effect=AssertionError("network")),
        ):
            async with Client(create_server()) as client:
                result = await client.call_tool(
                    "preview_build", {"app_id": APP, "workflow_id": "ios", "tag": "v1"}
                )
                secret = await client.call_tool(
                    "preview_build",
                    {
                        "app_id": APP,
                        "workflow_id": "ios",
                        "branch": "main",
                        "inputs": {"release": True, "value": "synthetic-input"},
                        "environment": {
                            "variables": {"VALUE": "synthetic-secret"},
                            "groups": ["signing"],
                        },
                    },
                )
            cli = api.run(
                api.parser().parse_args(
                    [
                        "start",
                        "--app",
                        APP,
                        "--workflow",
                        "ios",
                        "--tag",
                        "v1",
                        "--dry-run",
                    ]
                )
            )
        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content, cli)
        self.assertFalse(secret.is_error)
        self.assertNotIn("synthetic-secret", secret.model_dump_json())
        self.assertNotIn("synthetic-input", secret.model_dump_json())
        self.assertEqual(secret.structured_content["body"]["environment"]["groups"], ["signing"])

    async def test_invalid_requests_never_contact_api(self):
        base = {"app_id": APP, "workflow_id": "ios", "branch": "main"}
        cases = [
            ("get_build", {"build_id": "../user/teams"}),
            ("list_teams", {"page_size": 101}),
            ("list_teams", {"page": 0}),
            ("list_builds", {"team_id": TEAM, "status": "bogus"}),
            ("start_build", {"app_id": APP, "workflow_id": "ios"}),
            ("start_build", {**base, "tag": "v1"}),
            ("start_build", {**base, "dry_run": True}),
            ("cancel_build", {"build_id": BUILD, "dry_run": True}),
            ("start_build", {**base, "branch": "   "}),
            ("start_build", {**base, "inputs": {"bad-name": "x"}}),
            ("start_build", {**base, "inputs": {"nested": {"a": "b"}}}),
            ("start_build", {**base, "environment": {"wrong": "x"}}),
            ("start_build", {**base, "environment": {"variables": {"VALUE": 123}}}),
            ("start_build", {**base, "environment": {"groups": [""]}}),
        ]
        with patch.object(api, "request", side_effect=AssertionError("API called")):
            async with Client(create_server()) as client:
                for name, args in cases:
                    with self.subTest(name=name, args=args):
                        result = await client.call_tool(name, args)
                        self.assertTrue(result.is_error)

    async def test_read_endpoints_and_pagination(self):
        # Test at the HTTP boundary so authentication, URL encoding, and redaction run too.
        cases = [
            ("list_teams", {"page": 2}, "/user/teams?page=2&page_size=30"),
            ("list_apps", {}, "/user/apps?page=1&page_size=30"),
            (
                "list_apps",
                {"team_id": TEAM, "name": "my app"},
                f"/teams/{TEAM}/apps?name=my+app&page=1&page_size=30",
            ),
            ("list_workflows", {"app_id": APP}, f"/apps/{APP}/workflows"),
            (
                "list_builds",
                {"team_id": TEAM, "app_id": APP, "branch": "feature/a", "cursor": BUILD},
                f"/teams/{TEAM}/builds?app_id={APP}&branch=feature%2Fa&cursor={BUILD}&page_size=30",
            ),
            ("get_build", {"build_id": BUILD}, f"/builds/{BUILD}"),
            (
                "get_build_actions",
                {"build_id": BUILD, "page_size": 10},
                f"/builds/{BUILD}/actions?page=1&page_size=10",
            ),
        ]
        with (
            patch.dict(os.environ, {"CODEMAGIC_API_KEY": "synthetic-token"}, clear=True),
            patch.object(api.urllib.request, "build_opener") as opener,
        ):
            opener.return_value.open.return_value = Response(
                json.dumps(
                    {
                        "data": [],
                        "next_cursor": BUILD,
                        "echo": "synthetic-token",
                    }
                ).encode()
            )
            async with Client(create_server()) as client:
                for name, args, suffix in cases:
                    with self.subTest(name=name):
                        result = await client.call_tool(name, args)
                        self.assertFalse(result.is_error)
                        self.assertEqual(result.structured_content["next_cursor"], BUILD)
                        self.assertNotIn("synthetic-token", result.model_dump_json())
                        request = opener.return_value.open.call_args.args[0]
                        self.assertEqual(request.full_url, api.BASE + suffix)
                        self.assertEqual(request.method, "GET")
                        self.assertEqual(request.get_header("X-auth-token"), "synthetic-token")
                opener.return_value.open.return_value = Response(b'{"data":{"artifacts":[]}}')
                result = await client.call_tool("get_build_artifacts", {"build_id": BUILD})
                self.assertEqual(result.structured_content, {"data": []})
                result = await client.call_tool("auth_status", {})
                self.assertEqual(
                    result.structured_content,
                    {
                        "authenticated": True,
                        "source": "CODEMAGIC_API_KEY",
                    },
                )

    async def test_mutations_send_exactly_once_and_keep_input_types(self):
        with (
            patch.dict(os.environ, {"CODEMAGIC_API_KEY": "synthetic-token"}, clear=True),
            patch.object(api.urllib.request, "build_opener") as opener,
        ):
            opener.return_value.open.return_value = Response(b'{"data":{"id":"build"}}')
            async with Client(create_server()) as client:
                result = await client.call_tool(
                    "start_build",
                    {
                        "app_id": APP,
                        "workflow_id": "ios",
                        "branch": "feature/a",
                        "inputs": {"flag": True, "count": 3},
                        "labels": ["test"],
                        "environment": {"groups": ["signing"]},
                        "instance_type": "mac_mini_m2",
                    },
                )
                self.assertFalse(result.is_error)
                opener.return_value.open.assert_called_once()
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(request.method, "POST")
                self.assertEqual(request.full_url, f"{api.BASE}/apps/{APP}/builds")
                self.assertEqual(
                    json.loads(request.data),
                    {
                        "workflow_id": "ios",
                        "branch": "feature/a",
                        "inputs": {"flag": True, "count": 3},
                        "labels": ["test"],
                        "environment": {"groups": ["signing"]},
                        "instance_type": "mac_mini_m2",
                    },
                )
                opener.reset_mock()
                result = await client.call_tool("cancel_build", {"build_id": BUILD})
                self.assertFalse(result.is_error)
                opener.return_value.open.assert_called_once()
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(request.full_url, f"{api.LEGACY}/builds/{BUILD}/cancel")
                self.assertEqual(request.method, "POST")

    async def test_safe_errors_and_uncertain_mutations_are_not_retried(self):
        with patch.object(api, "token_source", side_effect=api.ClientError("Not logged in.")):
            async with Client(create_server()) as client:
                result = await client.call_tool("list_teams", {})
                self.assertTrue(result.is_error)
                self.assertIn("Not logged in", result.content[0].text)
        with (
            patch.dict(os.environ, {"CODEMAGIC_API_KEY": "synthetic-token"}, clear=True),
            patch.object(api.urllib.request, "build_opener") as opener,
        ):
            opener.return_value.open.side_effect = urllib.error.URLError("synthetic-token")
            async with Client(create_server()) as client:
                result = await client.call_tool(
                    "start_build",
                    {
                        "app_id": APP,
                        "workflow_id": "ios",
                        "branch": "main",
                    },
                )
            self.assertTrue(result.is_error)
            self.assertIn("Outcome unknown", result.content[0].text)
            self.assertNotIn("synthetic-token", result.model_dump_json())
            opener.return_value.open.assert_called_once()

    async def test_extracted_plugin_stdio_supports_current_and_legacy_clients(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extracted = root / "plugin with spaces"
            with ZipFile(builder.build(root)) as archive:
                archive.extractall(extracted)
            script = extracted / "skills/codemagic/scripts/codemagic_mcp.py"
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(script)],
                cwd=root,
                env={"XDG_CONFIG_HOME": str(root / "empty-config")},
            )
            for mode in ("auto", "legacy"):
                async with Client(params, mode=mode, read_timeout_seconds=15) as client:
                    self.assertEqual(len((await client.list_tools()).tools), 11)
                    result = await client.call_tool(
                        "preview_build",
                        {
                            "app_id": APP,
                            "workflow_id": "ios",
                            "branch": "main",
                        },
                    )
                    self.assertFalse(result.is_error)
                    self.assertFalse(result.structured_content["sent"])
                    result = await client.call_tool("auth_status", {})
                    self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
