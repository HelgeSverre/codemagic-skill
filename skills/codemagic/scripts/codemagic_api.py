#!/usr/bin/env python3
"""Small, dependency-free client for the official Codemagic API."""

import argparse
import getpass
import json
import os
import re
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "1.1.0"
BASE = "https://codemagic.io/api/v3"
LEGACY = "https://api.codemagic.io"
TOKEN_ENV = ("CODEMAGIC_API_KEY", "CODEMAGIC_API_TOKEN", "CM_API_TOKEN")
STATUSES = ("queued", "building", "finished", "failed", "canceled", "timeout", "skipped")


class ClientError(Exception):
    pass


def credentials_path():
    return (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "codemagic-api" / "token"
    )


def token_source():
    for name in TOKEN_ENV:
        if os.environ.get(name, "").strip():
            return os.environ[name].strip(), name
    if os.name != "posix":
        raise ClientError(
            "Set CODEMAGIC_API_KEY in your environment; token-file login requires macOS/Linux."
        )
    path = credentials_path()
    try:
        with path.open() as stream:
            if stat.S_IMODE(os.fstat(stream.fileno()).st_mode) & 0o077:
                raise ClientError(f"Token file is readable by other users. Run: chmod 600 {path}")
            token = stream.read().strip()
    except FileNotFoundError:
        raise ClientError("Not logged in. Run codemagic-api auth login in your terminal.") from None
    if not token:
        raise ClientError("Stored token is empty. Run codemagic-api auth login.")
    return token, str(path)


def valid_token(token):
    if not token or any(c.isspace() for c in token) or not token.isascii():
        raise ClientError("API token must be a nonempty ASCII value without whitespace.")
    return token


def save_token(token):
    if os.name != "posix":
        raise ClientError(
            "Token-file login requires macOS/Linux. Set CODEMAGIC_API_KEY on Windows."
        )
    path = credentials_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".token-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(valid_token(token) + "\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return path


def redact(value, token=""):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if re.search(r"token|password|secret|authorization|private.?key", key, re.I):
                result[key] = "[redacted]"
            elif key in ("variables", "inputs", "build_inputs") and isinstance(item, dict):
                result[key] = {name: "[redacted]" for name in item}
            else:
                result[key] = redact(item, token)
        return result
    if isinstance(value, list):
        return [redact(item, token) for item in value]
    if isinstance(value, str) and token:
        return value.replace(token, "[redacted]")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ClientError("API redirect refused to avoid forwarding credentials.")


def api_url(path, legacy=False, query=None):
    parsed = urllib.parse.urlsplit(path)
    if (
        not path.startswith("/")
        or path.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or parsed.fragment
        or any(ord(c) < 32 for c in path)
        or "\\" in path
        or any(p in (".", "..") for p in urllib.parse.unquote(parsed.path).split("/"))
    ):
        raise ClientError(
            "Use a relative API path such as /user/teams; URLs and traversal are rejected."
        )
    url = (LEGACY if legacy else BASE) + path
    if query:
        encoded = urllib.parse.urlencode(
            {k: v for k, v in query.items() if v is not None}, doseq=True
        )
        if encoded:
            url += ("&" if "?" in url else "?") + encoded
    return url


def request(method, path, body=None, *, query=None, legacy=False, dry_run=False, token=None):
    url = api_url(path, legacy, query)
    if dry_run:
        return {"method": method, "url": url, "body": redact(body), "sent": False}
    token = valid_token(token if token is not None else token_source()[0])
    data = None if body is None else json.dumps(body, allow_nan=False).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "x-auth-token": token,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"codemagic-api-local/{VERSION}",
        },
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            if response.status == 208 and legacy and path.endswith("/cancel"):
                return {"status_code": 208, "already_finished": True}
            raw = response.read()
            if not raw:
                return {"status_code": response.status}
            try:
                return redact(json.loads(raw), token)
            except (ValueError, UnicodeError):
                raise ClientError(
                    "Expected JSON; use Codemagic's artifact download instructions for binary files."
                ) from None
    except urllib.error.HTTPError as exc:
        hints = {
            401: "Token missing or invalid; run codemagic-api auth login.",
            403: "Your Codemagic account lacks permission for this operation.",
            404: "Resource not found. A newly accepted build may take a moment to appear.",
            429: f"Rate limit reached; retry after {exc.headers.get('ratelimit-reset', 'the reset')} seconds.",
        }
        # Error bodies may echo submitted environment values; never dump them.
        hint = hints.get(
            exc.code, "Check the endpoint, IDs, and request payload against the API schema."
        )
        if method != "GET" and exc.code >= 500:
            hint += " Outcome may be unknown; inspect builds before retrying."
        raise ClientError(f"Codemagic HTTP {exc.code}. {hint}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        hint = (
            " Check connectivity and retry."
            if method == "GET"
            else " Outcome unknown; inspect builds before retrying."
        )
        raise ClientError(f"Codemagic network error ({type(exc).__name__}).{hint}") from None


def identifier(value):
    if not re.fullmatch(r"[0-9a-fA-F]{24}", value):
        raise argparse.ArgumentTypeError("Expected a 24-character Codemagic ID.")
    return value


def nonempty(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("Value must not be blank.")
    return value


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be at least 1.")
    return number


def json_object(path):
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        raise ClientError(f"Cannot read a JSON object from {path}.") from None
    if not isinstance(value, dict):
        raise ClientError(f"Expected a JSON object in {path}.")
    return value


def build_payload(
    workflow_id,
    *,
    branch=None,
    tag=None,
    inputs=None,
    environment=None,
    labels=None,
    instance_type=None,
):
    """Validate a v3 build request without authentication or network access."""
    if (branch is None) == (tag is None):
        raise ClientError("Specify exactly one of branch or tag.")
    for value in (workflow_id, branch, tag, instance_type):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ClientError("Workflow, branch, tag, and instance type must be nonempty strings.")
    if inputs is not None and not isinstance(inputs, dict):
        raise ClientError("Inputs must be an object.")
    if environment is not None and not isinstance(environment, dict):
        raise ClientError("Environment must be an object.")
    if labels is not None and (
        not isinstance(labels, list)
        or not all(isinstance(value, str) and value.strip() for value in labels)
    ):
        raise ClientError("Labels must be a list of nonempty strings.")
    body = {"workflow_id": workflow_id}
    body.update(
        {
            key: value
            for key, value in (("branch", branch), ("tag", tag), ("instance_type", instance_type))
            if value is not None
        }
    )
    if labels:
        body["labels"] = labels
    if inputs is not None:
        body["inputs"] = inputs
        if any(
            not re.fullmatch(r"[a-zA-Z]\w*", k, flags=re.ASCII)
            or type(v) not in (str, bool, int, float)
            for k, v in body["inputs"].items()
        ):
            raise ClientError("Inputs must have valid names and string, boolean, or number values.")
    if environment is not None:
        body["environment"] = environment
        env = body["environment"]
        if set(env) - {"variables", "groups", "software_versions"}:
            raise ClientError(
                "Environment keys must be variables, groups, or software_versions (v3 names)."
            )
        for key in ("variables", "software_versions"):
            if key in env and (
                not isinstance(env[key], dict)
                or not all(isinstance(v, str) for v in env[key].values())
            ):
                raise ClientError(f"environment.{key} must be an object with string values.")
        if "groups" in env and (
            not isinstance(env["groups"], list)
            or not all(isinstance(v, str) and v.strip() for v in env["groups"])
        ):
            raise ClientError("environment.groups must be a list of nonempty strings.")
    try:
        json.dumps(body, allow_nan=False)
    except (ValueError, TypeError):
        raise ClientError("Build values must be valid JSON with finite numbers.") from None
    return body


def parser():
    p = argparse.ArgumentParser(
        prog="codemagic-api",
        description="Operate Codemagic through its official API. Results are JSON; diagnostics go to stderr.",
    )
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="command", required=True)
    auth = sub.add_parser("auth", help="Log in, check authentication, or remove the local token")
    auth_sub = auth.add_subparsers(dest="action", required=True)
    login = auth_sub.add_parser(
        "login", help="Validate and save a token using hidden terminal input"
    )
    login.add_argument(
        "--stdin",
        action="store_true",
        help="Read a token from stdin, for a password-manager pipeline",
    )
    auth_sub.add_parser("status", help="Verify authentication without printing the token")
    auth_sub.add_parser("logout", help="Remove only this tool's stored token")

    def page(q, cursor=False):
        q.add_argument("--page-size", type=int, choices=range(1, 101), metavar="1..100", default=30)
        if cursor:
            q.add_argument("--cursor")
        else:
            q.add_argument("--page", type=positive, default=1)

    page(sub.add_parser("teams", help="List your teams (paginated)"))
    apps = sub.add_parser("apps", help="List personal apps, or team apps with --team")
    apps.add_argument("--team", type=identifier)
    apps.add_argument("--name")
    page(apps)
    workflows = sub.add_parser("workflows", help="List known workflows for an app")
    workflows.add_argument("app_id", type=identifier)
    builds = sub.add_parser("builds", help="List a team's builds, with optional filters")
    builds.add_argument("--team", type=identifier, required=True)
    builds.add_argument("--app", type=identifier)
    builds.add_argument("--workflow")
    builds.add_argument("--branch")
    builds.add_argument("--tag")
    builds.add_argument("--status", choices=STATUSES)
    page(builds, cursor=True)
    for name, description in (
        ("build", "Get build status, commit, and details"),
        ("actions", "Get build step statuses and scripts"),
        ("artifacts", "List build artifacts and their URLs"),
    ):
        q = sub.add_parser(name, help=description)
        q.add_argument("build_id", type=identifier)
        if name == "actions":
            page(q)
    start = sub.add_parser("start", help="Queue a build; the selected workflow may also publish it")
    start.add_argument("--app", required=True, type=identifier)
    start.add_argument("--workflow", required=True, type=nonempty)
    ref = start.add_mutually_exclusive_group(required=True)
    ref.add_argument("--branch", type=nonempty)
    ref.add_argument("--tag", type=nonempty)
    start.add_argument("--inputs-file", help="JSON object of workflow input values")
    start.add_argument(
        "--environment-file", help="JSON object with variables, groups, or software_versions"
    )
    start.add_argument("--label", action="append", type=nonempty)
    start.add_argument("--instance-type", type=nonempty)
    start.add_argument(
        "--dry-run", action="store_true", help="Preview the redacted request without sending it"
    )
    cancel = sub.add_parser("cancel", help="Cancel a build using the documented legacy endpoint")
    cancel.add_argument("build_id", type=identifier)
    cancel.add_argument("--dry-run", action="store_true")
    api = sub.add_parser(
        "api", help="Call another documented JSON endpoint; paths are relative to /api/v3"
    )
    api.add_argument("method", choices=("GET", "POST", "PUT", "PATCH", "DELETE"))
    api.add_argument("path")
    api.add_argument(
        "--data-file", help="JSON request object; use a file to keep secrets out of arguments"
    )
    api.add_argument(
        "--legacy", action="store_true", help="Use https://api.codemagic.io instead of v3"
    )
    api.add_argument("--dry-run", action="store_true")
    completion = sub.add_parser("completion", help="Print shell completion setup")
    completion.add_argument("shell", choices=("bash", "zsh", "fish"))
    return p


def run(args):
    command = args.command
    if command == "auth":
        if args.action == "logout":
            credentials_path().unlink(missing_ok=True)
            return {"local_token_removed": True, "environment_tokens_unaffected": True}
        if args.action == "login":
            if os.name != "posix":
                raise ClientError(
                    "Set CODEMAGIC_API_KEY on Windows; token-file login requires macOS/Linux."
                )
            if not args.stdin and not sys.stdin.isatty():
                raise ClientError("Run auth login in an interactive terminal, or pass --stdin.")
            token = valid_token(
                sys.stdin.read().strip()
                if args.stdin
                else getpass.getpass("Codemagic API token: ").strip()
            )
            request("GET", "/user/teams", query={"page_size": 1}, token=token)
            path = save_token(token)
            return {
                "authenticated": True,
                "storage": str(path),
                "permissions": "0600",
                "environment_override_present": any(os.environ.get(k) for k in TOKEN_ENV),
            }
        token, source = token_source()
        request("GET", "/user/teams", query={"page_size": 1}, token=token)
        return {"authenticated": True, "source": source}
    if command == "teams":
        return request("GET", "/user/teams", query={"page": args.page, "page_size": args.page_size})
    if command == "apps":
        path = f"/teams/{args.team}/apps" if args.team else "/user/apps"
        return request(
            "GET", path, query={"name": args.name, "page": args.page, "page_size": args.page_size}
        )
    if command == "workflows":
        return request("GET", f"/apps/{args.app_id}/workflows")
    if command == "builds":
        return request(
            "GET",
            f"/teams/{args.team}/builds",
            query={
                "app_id": args.app,
                "workflow_id": args.workflow,
                "branch": args.branch,
                "tag": args.tag,
                "status": args.status,
                "cursor": args.cursor,
                "page_size": args.page_size,
            },
        )
    if command in ("build", "artifacts", "actions"):
        path = f"/builds/{args.build_id}"
        if command == "actions":
            return request(
                "GET", path + "/actions", query={"page": args.page, "page_size": args.page_size}
            )
        result = request("GET", path)
        return {"data": result["data"]["artifacts"]} if command == "artifacts" else result
    if command == "start":
        body = build_payload(
            args.workflow,
            branch=args.branch,
            tag=args.tag,
            labels=args.label,
            instance_type=args.instance_type,
            inputs=json_object(args.inputs_file) if args.inputs_file else None,
            environment=json_object(args.environment_file) if args.environment_file else None,
        )
        return request("POST", f"/apps/{args.app}/builds", body, dry_run=args.dry_run)
    if command == "cancel":
        return request("POST", f"/builds/{args.build_id}/cancel", legacy=True, dry_run=args.dry_run)
    if command == "api":
        if args.method == "GET" and args.data_file:
            raise ClientError(
                "GET requests do not accept --data-file; use query parameters in the path."
            )
        body = json_object(args.data_file) if args.data_file else None
        return request(args.method, args.path, body, legacy=args.legacy, dry_run=args.dry_run)


def completions(shell):
    words = "auth teams apps workflows builds build actions artifacts start cancel api completion"
    if shell == "bash":
        return f"complete -W '{words} --help --version' codemagic-api"
    if shell == "zsh":
        return f'# Run after compinit\ncompdef \'_arguments "1:command:({words})" "*:argument:_files"\' codemagic-api'
    return f"complete -c codemagic-api -n '__fish_use_subcommand' -a '{words}'"


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "completion":
            print(completions(args.shell))
        else:
            print(json.dumps(run(args), indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except EOFError:
        print("codemagic-api: no token entered", file=sys.stderr)
        return 1
    except (ClientError, OSError, ValueError) as exc:
        print(f"codemagic-api: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("codemagic-api: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
