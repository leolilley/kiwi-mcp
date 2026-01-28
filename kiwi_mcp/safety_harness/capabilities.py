"""
Capability Token System

Provides capability tokens for permission enforcement in the safety harness.
Tokens are signed using Ed25519 for cryptographic verification.
"""

import base64
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Try to import cryptography for Ed25519 signing
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


# Default key paths
DEFAULT_KEY_DIR = Path.home() / ".kiwi" / "keys"
PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"


@dataclass
class CapabilityToken:
    """
    Capability token for permission enforcement.
    
    Attributes:
        caps: List of granted capabilities (e.g., ["fs.read", "tool.bash"])
        aud: Audience identifier (prevents cross-service replay)
        exp: Expiry time (UTC)
        parent_id: Parent token ID for delegation chains
        directive_id: Source directive that minted this token
        thread_id: Thread this token belongs to
        signature: Ed25519 signature (set after signing)
        token_id: Unique token identifier
    """
    
    caps: List[str]
    aud: str
    exp: datetime
    directive_id: str
    thread_id: str
    parent_id: Optional[str] = None
    signature: Optional[str] = None
    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary for serialization."""
        return {
            "token_id": self.token_id,
            "caps": self.caps,
            "aud": self.aud,
            "exp": self.exp.isoformat(),
            "parent_id": self.parent_id,
            "directive_id": self.directive_id,
            "thread_id": self.thread_id,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityToken":
        """Create token from dictionary."""
        exp = data["exp"]
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp)
        
        return cls(
            token_id=data.get("token_id", str(uuid.uuid4())),
            caps=data["caps"],
            aud=data["aud"],
            exp=exp,
            parent_id=data.get("parent_id"),
            directive_id=data["directive_id"],
            thread_id=data["thread_id"],
            signature=data.get("signature"),
        )
    
    def to_jwt(self) -> str:
        """Serialize token to JWT-like base64 string."""
        data = self.to_dict()
        json_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(json_bytes).decode("ascii")
    
    @classmethod
    def from_jwt(cls, token_str: str) -> "CapabilityToken":
        """Deserialize token from JWT-like base64 string."""
        json_bytes = base64.urlsafe_b64decode(token_str.encode("ascii"))
        data = json.loads(json_bytes.decode("utf-8"))
        return cls.from_dict(data)
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        now = datetime.now(timezone.utc)
        # Handle naive datetimes by assuming UTC
        exp = self.exp
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp
    
    def has_capability(self, capability: str) -> bool:
        """Check if token grants a specific capability.
        
        Uses capability hierarchy - if token has 'kiwi-mcp.execute',
        it implicitly has 'kiwi-mcp.search', 'kiwi-mcp.load', etc.
        """
        # Lazy import to avoid circular dependency
        from kiwi_mcp.safety_harness.capabilities import expand_capabilities
        expanded = expand_capabilities(self.caps)
        return capability in expanded
    
    def has_any_capability(self, capabilities: List[str]) -> bool:
        """Check if token grants any of the specified capabilities."""
        from kiwi_mcp.safety_harness.capabilities import expand_capabilities
        expanded = expand_capabilities(self.caps)
        return bool(expanded & set(capabilities))
    
    def has_all_capabilities(self, capabilities: List[str]) -> bool:
        """Check if token grants all of the specified capabilities."""
        from kiwi_mcp.safety_harness.capabilities import expand_capabilities
        expanded = expand_capabilities(self.caps)
        return set(capabilities).issubset(expanded)
    
    def get_expanded_capabilities(self) -> List[str]:
        """Get all capabilities including implied ones from hierarchy."""
        from kiwi_mcp.safety_harness.capabilities import expand_capabilities
        return sorted(expand_capabilities(self.caps))
    
    def get_payload_for_signing(self) -> bytes:
        """Get the token payload for signing (excludes signature)."""
        data = {
            "token_id": self.token_id,
            "caps": sorted(self.caps),  # Sort for deterministic output
            "aud": self.aud,
            "exp": self.exp.isoformat(),
            "parent_id": self.parent_id,
            "directive_id": self.directive_id,
            "thread_id": self.thread_id,
        }
        return json.dumps(data, sort_keys=True).encode("utf-8")


def _get_key_path(key_type: str = "private") -> Path:
    """Get path to key file."""
    filename = PRIVATE_KEY_FILE if key_type == "private" else PUBLIC_KEY_FILE
    return DEFAULT_KEY_DIR / filename


def _ensure_key_directory() -> None:
    """Ensure key directory exists with proper permissions."""
    DEFAULT_KEY_DIR.mkdir(parents=True, exist_ok=True)
    # Set directory permissions to 700 (owner only)
    os.chmod(DEFAULT_KEY_DIR, 0o700)


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate a new Ed25519 keypair.
    
    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("cryptography library required for key generation")
    
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    
    return private_pem, public_pem


def save_keypair(private_key: bytes, public_key: bytes) -> None:
    """Save keypair to default location."""
    _ensure_key_directory()
    
    private_path = _get_key_path("private")
    public_path = _get_key_path("public")
    
    private_path.write_bytes(private_key)
    os.chmod(private_path, 0o600)  # Owner read/write only
    
    public_path.write_bytes(public_key)
    os.chmod(public_path, 0o644)  # Owner read/write, others read


def load_private_key() -> bytes:
    """Load private key from default location."""
    key_path = _get_key_path("private")
    if not key_path.exists():
        raise FileNotFoundError(f"Private key not found at {key_path}")
    return key_path.read_bytes()


def load_public_key() -> bytes:
    """Load public key from default location."""
    key_path = _get_key_path("public")
    if not key_path.exists():
        raise FileNotFoundError(f"Public key not found at {key_path}")
    return key_path.read_bytes()


def ensure_keypair() -> tuple[bytes, bytes]:
    """Ensure a keypair exists, generating one if needed.
    
    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    try:
        private_key = load_private_key()
        public_key = load_public_key()
        return private_key, public_key
    except FileNotFoundError:
        private_key, public_key = generate_keypair()
        save_keypair(private_key, public_key)
        return private_key, public_key


def sign_token(token: CapabilityToken, private_key: bytes) -> str:
    """Sign a capability token using Ed25519.
    
    Args:
        token: The token to sign
        private_key: Ed25519 private key in PEM format
        
    Returns:
        Base64-encoded signature string
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("cryptography library required for token signing")
    
    key = serialization.load_pem_private_key(private_key, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Private key must be Ed25519")
    
    payload = token.get_payload_for_signing()
    signature = key.sign(payload)
    
    signature_b64 = base64.urlsafe_b64encode(signature).decode("ascii")
    token.signature = signature_b64
    
    return signature_b64


def verify_token(token_str: str, public_key: bytes) -> Optional[CapabilityToken]:
    """Verify and deserialize a signed token.
    
    Args:
        token_str: JWT-like base64 token string
        public_key: Ed25519 public key in PEM format
        
    Returns:
        CapabilityToken if valid, None if invalid/expired
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("cryptography library required for token verification")
    
    try:
        token = CapabilityToken.from_jwt(token_str)
        
        # Check expiry first
        if token.is_expired():
            return None
        
        # Verify signature
        if not token.signature:
            return None
        
        key = serialization.load_pem_public_key(public_key)
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("Public key must be Ed25519")
        
        payload = token.get_payload_for_signing()
        signature = base64.urlsafe_b64decode(token.signature.encode("ascii"))
        
        try:
            key.verify(signature, payload)
            return token
        except Exception:
            return None
            
    except Exception:
        return None


def mint_token(
    caps: List[str],
    directive_id: str,
    thread_id: str,
    parent_id: Optional[str] = None,
    exp_hours: int = 1,
    aud: str = "kiwi-mcp",
) -> CapabilityToken:
    """Mint a new capability token.
    
    Args:
        caps: List of capabilities to grant
        directive_id: ID of the directive minting this token
        thread_id: ID of the thread this token is for
        parent_id: Optional parent token ID for delegation chains
        exp_hours: Token validity in hours (default 1)
        aud: Audience identifier (default "kiwi-mcp")
        
    Returns:
        Unsigned CapabilityToken (call sign_token to sign)
    """
    exp = datetime.now(timezone.utc) + timedelta(hours=exp_hours)
    
    return CapabilityToken(
        caps=list(caps),
        aud=aud,
        exp=exp,
        parent_id=parent_id,
        directive_id=directive_id,
        thread_id=thread_id,
    )


def attenuate_token(
    parent_token: CapabilityToken,
    child_declared_caps: List[str],
) -> CapabilityToken:
    """Attenuate a parent token for a child thread.
    
    Implements capability intersection: child only gets capabilities
    that BOTH the parent has AND the child declares it needs.
    
    Args:
        parent_token: The parent thread's token
        child_declared_caps: Capabilities the child directive declares
        
    Returns:
        New token with attenuated capabilities
    """
    # Intersection: child gets only what parent has AND child declares
    parent_caps = set(parent_token.caps)
    child_caps = set(child_declared_caps)
    attenuated_caps = list(parent_caps & child_caps)
    
    # Create new token with attenuated caps
    return CapabilityToken(
        caps=sorted(attenuated_caps),  # Sort for consistency
        aud=parent_token.aud,
        exp=parent_token.exp,  # Inherit expiry from parent
        parent_id=parent_token.token_id,
        directive_id=parent_token.directive_id,
        thread_id=parent_token.thread_id,
    )


# Permission XML to capability conversion table
PERMISSION_TO_CAPABILITY: Dict[tuple, str] = {
    # (tag, resource, action) -> capability
    
    # Filesystem
    ("read", "filesystem", None): "fs.read",
    ("write", "filesystem", None): "fs.write",
    ("execute", "filesystem", None): "fs.exec",
    
    # Thread spawning
    ("execute", "spawn", "thread"): "spawn.thread",
    
    # Thread registry
    ("execute", "registry", "write"): "registry.write",
    ("execute", "registry", "read"): "registry.read",
    
    # Kiwi MCP - granular capabilities
    ("execute", "kiwi-mcp", "execute"): "kiwi-mcp.execute",  # Run directives/tools
    ("execute", "kiwi-mcp", "search"): "kiwi-mcp.search",    # Search for items
    ("execute", "kiwi-mcp", "load"): "kiwi-mcp.load",        # Load/inspect items
    ("execute", "kiwi-mcp", "sign"): "kiwi-mcp.sign",        # Sign items (privileged)
    ("execute", "kiwi-mcp", "help"): "kiwi-mcp.help",        # Get help (low privilege)
    ("execute", "kiwi-mcp", "*"): "kiwi-mcp.all",            # All MCP operations
    
    # Shell/process
    ("execute", "shell", "*"): "process.exec",
    ("execute", "shell", None): "process.exec",
}

# Capability hierarchy - if you have a higher cap, you implicitly have lower ones
CAPABILITY_HIERARCHY: Dict[str, List[str]] = {
    # kiwi-mcp.all grants all kiwi-mcp capabilities
    "kiwi-mcp.all": [
        "kiwi-mcp.execute",
        "kiwi-mcp.search",
        "kiwi-mcp.load",
        "kiwi-mcp.sign",
        "kiwi-mcp.help",
    ],
    # kiwi-mcp.execute implies search/load/help (need to find things to execute)
    "kiwi-mcp.execute": [
        "kiwi-mcp.search",
        "kiwi-mcp.load",
        "kiwi-mcp.help",
    ],
    # fs.write implies fs.read
    "fs.write": ["fs.read"],
}


def expand_capabilities(caps: List[str]) -> Set[str]:
    """Expand capabilities using the hierarchy.
    
    If a token has 'kiwi-mcp.execute', it implicitly has
    'kiwi-mcp.search', 'kiwi-mcp.load', 'kiwi-mcp.help'.
    
    Args:
        caps: List of capability strings
        
    Returns:
        Set of all capabilities (original + implied)
    """
    expanded: Set[str] = set(caps)
    
    # Keep expanding until no new caps are added
    changed = True
    while changed:
        changed = False
        for cap in list(expanded):
            if cap in CAPABILITY_HIERARCHY:
                implied = set(CAPABILITY_HIERARCHY[cap])
                new_caps = implied - expanded
                if new_caps:
                    expanded.update(new_caps)
                    changed = True
    
    return expanded


def check_capability(granted_caps: List[str], required_cap: str) -> bool:
    """Check if granted capabilities satisfy a required capability.
    
    Uses hierarchy expansion - if you have kiwi-mcp.execute,
    you implicitly have kiwi-mcp.search, kiwi-mcp.load, etc.
    
    Args:
        granted_caps: List of granted capability strings
        required_cap: Required capability to check
        
    Returns:
        True if required capability is satisfied
    """
    expanded = expand_capabilities(granted_caps)
    return required_cap in expanded


def check_all_capabilities(granted_caps: List[str], required_caps: List[str]) -> tuple[bool, List[str]]:
    """Check if all required capabilities are satisfied.
    
    Args:
        granted_caps: List of granted capability strings
        required_caps: List of required capabilities
        
    Returns:
        Tuple of (all_satisfied, missing_caps)
    """
    expanded = expand_capabilities(granted_caps)
    missing = [cap for cap in required_caps if cap not in expanded]
    return (len(missing) == 0, missing)


def permissions_to_caps(permissions: List[Dict[str, Any]]) -> List[str]:
    """Convert directive permissions to capability list.
    
    Conversion rules:
    - read resource="filesystem" → fs.read
    - write resource="filesystem" → fs.write
    - execute resource="tool" id="X" → tool.X
    - execute resource="spawn" action="thread" → spawn.thread
    - execute resource="registry" action="write" → registry.write
    - execute resource="kiwi-mcp" action="execute" → kiwi-mcp.execute
    - execute resource="kiwi-mcp" action="search" → kiwi-mcp.search
    - execute resource="kiwi-mcp" action="load" → kiwi-mcp.load
    - execute resource="kiwi-mcp" action="sign" → kiwi-mcp.sign
    - execute resource="kiwi-mcp" action="help" → kiwi-mcp.help
    
    Args:
        permissions: List of permission dicts with 'tag' and 'attrs' keys
        
    Returns:
        List of capability strings
    """
    caps: Set[str] = set()
    
    for perm in permissions:
        tag = perm.get("tag", "")
        attrs = perm.get("attrs", {})
        resource = attrs.get("resource", "")
        action = attrs.get("action")
        
        # Try exact match first
        key = (tag, resource, action)
        if key in PERMISSION_TO_CAPABILITY:
            caps.add(PERMISSION_TO_CAPABILITY[key])
            continue
        
        # Try without action
        key_no_action = (tag, resource, None)
        if key_no_action in PERMISSION_TO_CAPABILITY:
            caps.add(PERMISSION_TO_CAPABILITY[key_no_action])
            continue
        
        # Handle tool-specific permissions: execute resource="tool" id="X" → tool.X
        if tag == "execute" and resource == "tool":
            tool_id = attrs.get("id")
            if tool_id:
                caps.add(f"tool.{tool_id}")
            continue
        
        # Handle generic resource permissions
        if tag == "read" and resource:
            caps.add(f"{resource}.read")
        elif tag == "write" and resource:
            caps.add(f"{resource}.write")
        elif tag == "execute" and resource:
            if action:
                caps.add(f"{resource}.{action}")
            else:
                caps.add(f"{resource}.execute")
    
    return sorted(caps)
