import os
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))

_vault_scripts = _repo_root / "demo-vault" / "Vault Files" / "Scripts"
os.chdir(_vault_scripts)

from core.shared.upgrade_vault import main

if __name__ == "__main__":
    raise SystemExit(main())
