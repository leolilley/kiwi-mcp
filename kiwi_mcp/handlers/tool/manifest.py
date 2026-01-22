from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
import yaml
import ast
import inspect


@dataclass
class ToolManifest:
    """Manifest describing a tool's metadata and execution requirements."""

    tool_id: str
    tool_type: str  # python | bash | api | docker | mcp
    version: str
    description: str
    executor_config: Dict[str, Any] = field(default_factory=dict)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    mutates_state: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> "ToolManifest":
        """Load manifest from tool.yaml file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls(
            tool_id=data["tool_id"],
            tool_type=data["tool_type"],
            version=data["version"],
            description=data["description"],
            executor_config=data.get("executor_config", {}),
            parameters=data.get("parameters", []),
            mutates_state=data.get("mutates_state", False),
        )

    @classmethod
    def virtual_from_script(cls, script_path: Path) -> "ToolManifest":
        """Generate virtual manifest for legacy .py script."""
        script_name = script_path.stem

        # Try to extract docstring and parameters from script
        description = "Legacy Python script"
        parameters = []

        try:
            with open(script_path, "r") as f:
                content = f.read()

            # Parse the AST to extract information
            tree = ast.parse(content)

            # Get module docstring
            if (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            ):
                description = tree.body[0].value.value.strip()

            # Look for main function parameters
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name in ["main", "run", "execute"]:
                    # Extract parameter info from function signature
                    for arg in node.args.args:
                        if arg.arg != "self":
                            parameters.append(
                                {
                                    "name": arg.arg,
                                    "type": "string",  # Default type
                                    "required": True,
                                    "description": f"Parameter {arg.arg}",
                                }
                            )
                    break

        except Exception:
            # If parsing fails, use defaults
            pass

        return cls(
            tool_id=script_name,
            tool_type="python",
            version="1.0.0",
            description=description,
            executor_config={},
            parameters=parameters,
            mutates_state=True,  # Conservative default for legacy scripts
        )
