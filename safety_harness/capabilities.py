"""Capability token system for permission enforcement.

This module implements the capability token system that enforces permissions
throughout Kiwi MCP. Key concepts:

- CapabilityToken: A signed token declaring what a thread can do
- Token minting: Create and sign tokens from directive permissions
- Token attenuation: Restrict child thread tokens (set intersection)
- Verification: Tools validate tokens before executing
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import base64

# Use cryptography library for Ed25519 signatures
try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.exceptions import InvalidSignature
except ImportError:
    raise ImportError(
        "cryptography library required. Install: pip install cryptography"
    )


@dataclass
class CapabilityToken:
    """Cryptographically signed capability token.

    A token represents what a thread is allowed to do. It contains:
    - caps: List of granted capabilities (e.g., ["fs.read", "fs.write"])
    - aud: Audience (prevents cross-service replay)
    - exp: Expiry time (datetime in UTC)
    - parent_id: Parent token ID (for delegation chains)
    - directive_id: Which directive this was minted from
    - thread_id: Which thread this token belongs to
    - signature: Ed25519 signature (base64-encoded)
    """

    caps: List[str]
    aud: str
    exp: datetime
    directive_id: str
    thread_id: str
    parent_id: Optional[str] = None
    signature: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(timezone.utc) >= self.exp

    def has_capability(self, cap: str) -> bool:
        """Check if token includes a capability.

        Args:
            cap: Capability ID (e.g., "fs.read")

        Returns:
            True if capability is in this token
        """
        return cap in self.caps

    def to_dict(self) -> Dict:
        """Convert token to dictionary for serialization."""
        return {
            "caps": self.caps,
            "aud": self.aud,
            "exp": self.exp.isoformat(),
            "directive_id": self.directive_id,
            "thread_id": self.thread_id,
            "parent_id": self.parent_id,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CapabilityToken":
        """Create token from dictionary."""
        exp = data["exp"]
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp)
        return cls(
            caps=data["caps"],
            aud=data["aud"],
            exp=exp,
            directive_id=data["directive_id"],
            thread_id=data["thread_id"],
            parent_id=data.get("parent_id"),
            signature=data.get("signature"),
        )


class TokenSigner:
    """Handles Ed25519 token signing and verification."""

    def __init__(self, private_key_path: Optional[str] = None, public_key_path: Optional[str] = None):
        """Initialize signer with key paths.

        Args:
            private_key_path: Path to private key (for signing). Defaults to ~/.kiwi/keys/private_key.pem
            public_key_path: Path to public key (for verification). Defaults to ~/.kiwi/keys/public_key.pem
        """
        self.private_key_path = private_key_path or os.path.expanduser(
            "~/.kiwi/keys/private_key.pem"
        )
        self.public_key_path = public_key_path or os.path.expanduser(
            "~/.kiwi/keys/public_key.pem"
        )
        self._private_key = None
        self._public_key = None

    def _ensure_keys_exist(self) -> None:
        """Ensure key files exist, generate if not."""
        os.makedirs(os.path.dirname(self.private_key_path), exist_ok=True)

        if not os.path.exists(self.private_key_path):
            # Generate new key pair
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            # Save private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            with open(self.private_key_path, "wb") as f:
                f.write(private_pem)
            os.chmod(self.private_key_path, 0o600)

            # Save public key
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            with open(self.public_key_path, "wb") as f:
                f.write(public_pem)

    def _load_private_key(self) -> ed25519.Ed25519PrivateKey:
        """Load private key from file."""
        if self._private_key is None:
            self._ensure_keys_exist()
            with open(self.private_key_path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(
                    f.read(), password=None
                )
        return self._private_key

    def _load_public_key(self) -> ed25519.Ed25519PublicKey:
        """Load public key from file."""
        if self._public_key is None:
            self._ensure_keys_exist()
            with open(self.public_key_path, "rb") as f:
                self._public_key = serialization.load_pem_public_key(f.read())
        return self._public_key

    def sign_token(self, token: CapabilityToken) -> str:
        """Sign a token and return signed token string.

        Args:
            token: CapabilityToken to sign

        Returns:
            Signed token string (base64-encoded)
        """
        # Create copy without signature for signing
        token_dict = token.to_dict()
        # Remove signature field before signing
        if "signature" in token_dict:
            del token_dict["signature"]

        # Serialize to JSON with sorted keys (important for verification)
        payload = json.dumps(token_dict, sort_keys=True).encode()

        # Sign with private key
        private_key = self._load_private_key()
        signature = private_key.sign(payload)
        signature_b64 = base64.b64encode(signature).decode()

        # Add signature and return signed token string
        token_dict["signature"] = signature_b64
        return base64.b64encode(json.dumps(token_dict).encode()).decode()

    def verify_token(self, token_str: str) -> Optional[CapabilityToken]:
        """Verify and deserialize a signed token string.

        Args:
            token_str: Signed token string

        Returns:
            CapabilityToken if valid, None if invalid or expired
        """
        try:
            # Deserialize
            token_dict = json.loads(base64.b64decode(token_str).decode())
            signature_b64 = token_dict.pop("signature")

            # Prepare payload for verification (must match signing exactly)
            payload = json.dumps(token_dict, sort_keys=True).encode()
            signature = base64.b64decode(signature_b64)

            # Verify signature
            public_key = self._load_public_key()
            try:
                public_key.verify(signature, payload)
            except InvalidSignature:
                # Invalid signature
                return None

            # Create token object
            token = CapabilityToken.from_dict(token_dict)

            # Check expiry
            if token.is_expired():
                return None

            # Restore signature
            token.signature = signature_b64

            return token
        except (ValueError, KeyError, json.JSONDecodeError, Exception) as e:
            # Catch all other errors (including base64 decode errors)
            return None


# Global token signer instance
_token_signer = TokenSigner()


def sign_token(token: CapabilityToken) -> str:
    """Sign a token using global signer.

    Args:
        token: CapabilityToken to sign

    Returns:
        Signed token string
    """
    return _token_signer.sign_token(token)


def verify_token(token_str: str) -> Optional[CapabilityToken]:
    """Verify a signed token using global signer.

    Args:
        token_str: Signed token string

    Returns:
        CapabilityToken if valid, None otherwise
    """
    return _token_signer.verify_token(token_str)


def permissions_to_caps(permissions: List[Dict]) -> List[str]:
    """Convert directive permissions to capability list.

    Args:
        permissions: List of permission dicts from directive

    Returns:
        List of capability IDs (e.g., ["fs.read", "fs.write"])

    Examples:
        >>> perms = [
        ...     {"tag": "read", "attrs": {"resource": "filesystem"}},
        ...     {"tag": "write", "attrs": {"resource": "filesystem"}},
        ... ]
        >>> permissions_to_caps(perms)
        ["fs.read", "fs.write"]
    """
    caps = set()

    for perm in permissions:
        tag = perm.get("tag")
        attrs = perm.get("attrs", {})

        if tag == "read":
            caps.add("fs.read")
        elif tag == "write":
            caps.add("fs.write")
        elif tag == "execute":
            resource = attrs.get("resource")
            action = attrs.get("action")
            tool_id = attrs.get("id")

            if resource == "tool" and tool_id:
                caps.add(f"tool.{tool_id}")
            elif resource == "spawn" and action == "thread":
                caps.add("spawn.thread")
            elif resource == "registry" and action == "write":
                caps.add("registry.write")
            elif resource == "kiwi-mcp" and action == "execute":
                caps.add("kiwi-mcp.execute")
            elif resource == "kiwi-mcp" and action == "read":
                caps.add("kiwi-mcp.read")
            elif resource == "kiwi-mcp" and action == "write":
                caps.add("kiwi-mcp.write")

    return sorted(list(caps))


def mint_token(
    caps: List[str],
    directive_id: str,
    thread_id: str,
    parent_id: Optional[str] = None,
    exp_hours: int = 1,
) -> CapabilityToken:
    """Mint a new capability token.

    Args:
        caps: List of capabilities to grant
        directive_id: Directive ID (e.g., "deploy_staging")
        thread_id: Thread ID (e.g., "thread-abc123")
        parent_id: Optional parent token ID (for delegation chains)
        exp_hours: Expiry time in hours (default 1 hour)

    Returns:
        Newly minted CapabilityToken (unsigned)
    """
    token = CapabilityToken(
        caps=sorted(caps),
        aud="kiwi-mcp",
        exp=datetime.now(timezone.utc) + timedelta(hours=exp_hours),
        directive_id=directive_id,
        thread_id=thread_id,
        parent_id=parent_id,
    )
    return token


def attenuate_token(
    parent_token: CapabilityToken, child_declared_caps: List[str]
) -> CapabilityToken:
    """Create an attenuated child token via set intersection.

    When a thread spawns a child thread, the child's token is the intersection
    of the parent's capabilities and what the child declares. This ensures
    the child cannot escalate privileges.

    Args:
        parent_token: Parent thread's capability token
        child_declared_caps: Capabilities child declares it needs

    Returns:
        New CapabilityToken with attenuated capabilities

    Example:
        >>> parent_caps = ["fs.read", "fs.write", "spawn.thread"]
        >>> child_declared = ["fs.write", "tool.bash"]
        >>> parent = mint_token(parent_caps, "parent", "thread-1")
        >>> child = attenuate_token(parent, child_declared)
        >>> child.caps
        ["fs.write"]  # bash is not in parent, spawn.thread not in child
    """
    # Intersection: what child gets is what both parent has AND child declares
    attenuated_caps = sorted(
        list(set(parent_token.caps) & set(child_declared_caps))
    )

    child_token = CapabilityToken(
        caps=attenuated_caps,
        aud=parent_token.aud,
        exp=parent_token.exp,
        directive_id="<child>",
        thread_id="<child>",
        parent_id=parent_token.directive_id,
    )

    return child_token


__all__ = [
    "CapabilityToken",
    "TokenSigner",
    "sign_token",
    "verify_token",
    "permissions_to_caps",
    "mint_token",
    "attenuate_token",
]
