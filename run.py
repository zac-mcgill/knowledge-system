import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

# Detect the Python command users should type to invoke this script.
# On Windows, prefer the 'py' launcher when available (works in clean
# environments that expose only 'py', not 'python').  On other platforms
# fall back to the stem of sys.executable (e.g. 'python3').
def _detect_python_cmd() -> str:
    import shutil
    if sys.platform == "win32" and shutil.which("py"):
        return "py"
    stem = Path(sys.executable).stem
    return stem if stem else "python"


_PYTHON_CMD = _detect_python_cmd()

COMMANDS = {
    "validate": "core.shared.validate_vault",
    "report": "core.shared.generate_report",
    "analyse": "core.shared.analyse_vault",
    "improve": "core.shared.upgrade_vault",
}

USAGE = f"""\
Usage: {_PYTHON_CMD} run.py <command>

Commands:
  init <vault>   Create a new vault from the demo template
  bootstrap      Create a blank vault with a custom schema interactively
  validate       Check all notes against the vault schema
  analyse        Run seven structured analyses on vault metadata
  improve        Generate prioritised upgrade tasks
  report         Generate a markdown report
  bundle         Generate a context bundle and print JSON to stdout
  export         Export context bundle as portable package to dist/context-bundles/
                 Use --overwrite to replace an existing package
  feedback       Load and print vault feedback entries as JSON
  security       Scan default context bundle for security issues; prints JSON to stdout
                 Exit 0 on pass/warning, exit 1 on fail
                 Use --fail-on-warning to exit 1 for warning results
  templates      Generate canonical templates from vault schema
                 Use --dry-run to preview without writing
  app            Start local server and open browser UI
                 Reuses an already-running server automatically"""


def _init_vault(repo_root: Path) -> None:
    if len(sys.argv) != 3 or not sys.argv[2].strip():
        print(USAGE)
        raise SystemExit(1)

    vault_name = sys.argv[2]

    if not re.match(r'^[A-Za-z0-9_\-][A-Za-z0-9_\- .]*$', vault_name):
        print(f"Error: invalid vault name: {vault_name}")
        raise SystemExit(1)

    target = repo_root / vault_name
    source = repo_root / "demo-vault"
    config_path = repo_root / "config" / "config.yaml"

    if target.exists():
        print(f"Error: directory already exists: {vault_name}")
        raise SystemExit(1)

    if not source.is_dir():
        print("Error: demo-vault not found")
        raise SystemExit(1)

    if not config_path.is_file():
        print("Error: config/config.yaml not found")
        raise SystemExit(1)

    # Deep copy demo-vault
    shutil.copytree(source, target)

    # Remove generated report if present
    report = target / "Vault Files" / "Vault Report.md"
    if report.is_file():
        report.unlink()

    # Atomic config update
    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    updated = re.sub(
        r'^(vault_root:\s*).*$',
        rf'\g<1>./{vault_name}',
        content,
        flags=re.MULTILINE,
    )

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=config_path.parent, suffix=".yaml"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
            tmp.write(updated)
        Path(tmp_path).replace(config_path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    print(f"Vault created: {vault_name}")
    print(f"Config updated: config/config.yaml")
    print(f"Ready to run: {_PYTHON_CMD} run.py validate")


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        raise SystemExit(1)

    command = sys.argv[1]

    repo_root = Path(__file__).resolve().parent

    if command == "help":
        print(USAGE)
        return

    if command == "init":
        _init_vault(repo_root)
        return

    if command == "templates":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from core.generate_templates import main as templates_main
        raise SystemExit(templates_main())

    if command == "bootstrap":
        from core.bootstrap_vault import main as bootstrap_main
        raise SystemExit(bootstrap_main(repo_root))

    if command == "app":
        from core.app_launcher import main as app_main
        raise SystemExit(app_main(repo_root))

    if command == "bundle":
        import json
        sys.path.insert(0, str(repo_root))
        try:
            from mcp.core.vault_registry import list_vaults
            from mcp.core.note_index import build_index, get_index
            from core.shared.context_bundle import generate_bundle

            vault_name = list_vaults()[0]
            build_index(vault_name)
            index = get_index(vault_name)

            # Use status=complete filter when complete notes exist;
            # fall back to allow_partial with a warning when none exist.
            has_complete = any(
                n["fields"].get("status") == "complete" for n in index
            )
            bundle_filters: dict = {"status": "complete"} if has_complete else {}
            allow_partial = not has_complete

            bundle = generate_bundle(
                vault_name=vault_name,
                filters=bundle_filters,
                include_sections=["Key Principles", "How It Works", "Trade-offs"],
                include_related=False,
                include_body=True,
                max_notes=10,
                max_chars=20000,
                allow_partial=allow_partial,
            )

            if not has_complete:
                bundle["warnings"].insert(
                    0,
                    "No complete notes found in vault; including partial notes",
                )

            print(json.dumps(bundle, indent=2, ensure_ascii=False))
            raise SystemExit(0)
        except SystemExit:
            raise
        except Exception as exc:
            error_output = {
                "status": "error",
                "error": {"code": "BUNDLE_FAILED", "message": str(exc)},
            }
            print(json.dumps(error_output, indent=2, ensure_ascii=False))
            raise SystemExit(1)

    if command == "export":
        import json as _json
        overwrite = "--overwrite" in sys.argv[2:]
        sys.path.insert(0, str(repo_root))
        try:
            from mcp.core.vault_registry import list_vaults
            from mcp.core.note_index import build_index, get_index
            from core.shared.context_bundle import generate_bundle
            from core.shared.context_package import export_context_package

            vault_name = list_vaults()[0]
            build_index(vault_name)
            index = get_index(vault_name)

            has_complete = any(
                n["fields"].get("status") == "complete" for n in index
            )
            bundle_filters: dict = {"status": "complete"} if has_complete else {}
            allow_partial = not has_complete

            bundle = generate_bundle(
                vault_name=vault_name,
                filters=bundle_filters,
                include_sections=["Key Principles", "How It Works", "Trade-offs"],
                include_related=False,
                include_body=True,
                max_notes=10,
                max_chars=20000,
                allow_partial=allow_partial,
            )

            if not has_complete:
                bundle["warnings"].insert(
                    0,
                    "No complete notes found in vault; including partial notes",
                )

            result = export_context_package(bundle, overwrite=overwrite)
            print(_json.dumps(result, indent=2, ensure_ascii=False))
            raise SystemExit(0 if result["status"] == "ok" else 1)
        except SystemExit:
            raise
        except Exception as exc:
            error_output = {
                "status": "error",
                "error": {"code": "EXPORT_FAILED", "message": str(exc)},
            }
            print(_json.dumps(error_output, indent=2, ensure_ascii=False))
            raise SystemExit(1)

    if command == "feedback":
        import json
        sys.path.insert(0, str(repo_root))
        try:
            from mcp.core.vault_registry import list_vaults, get_vault_path
            from core.shared.feedback import load_feedback

            vault_name = list_vaults()[0]
            vault_path = get_vault_path(vault_name)
            result = load_feedback(vault_path)

            output = {
                "status": result["status"],
                "vault": vault_name,
                "entries": result["entries"],
                "warnings": result["warnings"],
                "errors": result["errors"],
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
            raise SystemExit(0 if result["status"] == "ok" else 1)
        except SystemExit:
            raise
        except Exception as exc:
            error_output = {
                "status": "error",
                "error": {"code": "FEEDBACK_FAILED", "message": str(exc)},
            }
            print(json.dumps(error_output, indent=2, ensure_ascii=False))
            raise SystemExit(1)

    if command == "security":
        import json
        fail_on_warning = "--fail-on-warning" in sys.argv[2:]
        sys.path.insert(0, str(repo_root))
        try:
            from mcp.core.vault_registry import list_vaults
            from mcp.core.note_index import build_index
            from core.shared.context_security import scan_vault_context

            vault_name = list_vaults()[0]
            build_index(vault_name)

            # Vault-level security scan: include all content notes by default.
            # Partial notes are included because they can still contain secrets,
            # prompt-injection phrases, or unsafe links.
            # Generated/system files under Vault Files/ are excluded by the
            # vault index (discover_files) and are never passed to the scanner.
            result = scan_vault_context(
                vault_name=vault_name,
                filters={},
                include_sections=["Key Principles", "How It Works", "Trade-offs"],
                include_body=True,
                max_notes=1000,
                max_chars=10_000_000,
                allow_partial=True,
            )

            print(json.dumps(result, indent=2, ensure_ascii=False))

            if result.get("status") == "fail":
                raise SystemExit(1)
            if fail_on_warning and result.get("status") == "warning":
                raise SystemExit(1)
            raise SystemExit(0)
        except SystemExit:
            raise
        except Exception as exc:
            error_output = {
                "status": "error",
                "error": {"code": "SECURITY_SCAN_FAILED", "message": str(exc)},
            }
            print(json.dumps(error_output, indent=2, ensure_ascii=False))
            raise SystemExit(1)

    if command not in COMMANDS:
        print(f"Error: unknown command '{command}'")
        print(USAGE)
        raise SystemExit(1)

    config_path = repo_root / "config" / "config.yaml"
    if not config_path.is_file():
        print("Error: config/config.yaml not found")
        raise SystemExit(1)

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"Error: invalid config/config.yaml: {exc}")
        raise SystemExit(1)

    vault_rel = config.get("vault_root") if config else None
    if not vault_rel:
        print("Error: config/config.yaml missing 'vault_root' key")
        raise SystemExit(1)

    vault_root = (repo_root / vault_rel).resolve()
    if not vault_root.is_dir():
        print(f"Error: vault directory not found: {vault_root}")
        raise SystemExit(1)

    scripts_dir = vault_root / "Vault Files" / "Scripts"
    if not scripts_dir.is_dir():
        print(f"Error: vault scripts directory not found: {scripts_dir}")
        raise SystemExit(1)

    sys.path.insert(0, str(repo_root))

    sys.argv = sys.argv[:1]

    module = __import__(COMMANDS[command], fromlist=["main"])
    try:
        raise SystemExit(module.main(vault_root))
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)
    except Exception as exc:
        print(f"Error: unexpected failure in {command}: {exc}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
