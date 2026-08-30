import sys
import tempfile
from pathlib import Path
sys.path.insert(0, "src")
from addressable_information_layer.verifiers import MAX_COMMAND_TIMEOUT_SECONDS, _bounded_timeout, _resolve_safe_cwd, _safe_relative_path

assert _safe_relative_path("pkg/module.py").as_posix() == "pkg/module.py"
assert _safe_relative_path("../escape.py") is None
assert _safe_relative_path("/absolute.py") is None
assert _safe_relative_path("") is None
assert _bounded_timeout(0) == 1
assert _bounded_timeout(20) == 20
assert _bounded_timeout(MAX_COMMAND_TIMEOUT_SECONDS + 99) == MAX_COMMAND_TIMEOUT_SECONDS
assert _bounded_timeout("invalid") == 20
with tempfile.TemporaryDirectory() as raw:
    workspace = Path(raw)
    assert _resolve_safe_cwd(workspace, "sub/dir").is_relative_to(workspace.resolve())
    assert _resolve_safe_cwd(workspace, "../escape") is None
print("public passed")

assert _safe_relative_path("nested\\module.py").as_posix() == "nested/module.py"
assert _bounded_timeout(-100) == 1
assert _bounded_timeout(10**9) == MAX_COMMAND_TIMEOUT_SECONDS
print("hidden passed")
