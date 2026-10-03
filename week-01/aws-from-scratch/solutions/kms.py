"""
KMS — envelope encryption. Complete Solution.

DESIGN DECISION — encrypt data with the master key, or with a data key?
  Encrypting directly with the KMS key means every byte crosses the network to
  a service that caps payloads at 4KB, and rotating the key means re-encrypting
  everything you own.
  CHOSEN: ENVELOPE encryption. KMS generates a random data key, hands you it
  twice — plaintext and encrypted-under-the-master-key — and forgets it. You
  encrypt locally with the plaintext copy, throw it away, and store the
  encrypted copy next to the ciphertext.
  The consequences are the whole lesson: unlimited data size, one network call
  per object rather than per byte, and key rotation that re-encrypts KEYS
  rather than DATA.

DESIGN DECISION — what is "rotation"?
  The intuitive answer is "make a new key and re-encrypt everything".
  CHOSEN: model what actually happens — a new key VERSION is created for new
  encryptions, and old versions are retained so old ciphertext still decrypts.
  Rotation that broke old data would not be rotation, it would be an outage.

The cipher here is XOR. It is NOT encryption and the file says so loudly. The
structure — data keys, wrapping, context, rotation — is the lesson; substitute
AES-GCM and nothing about the shape changes.
"""

import hashlib
import os
import secrets
from typing import Any, Dict, List, NamedTuple, Optional, Tuple


class KMSError(Exception):
    pass


def _xor(data: bytes, key: bytes) -> bytes:
    """A stand-in cipher, NOT encryption.

    XOR with a repeating key is trivially broken and is used here only so the
    file has no dependencies and every step stays inspectable. Everything
    around it — envelope structure, wrapping, encryption context, rotation — is
    exactly what you would build with AES-GCM. Do not ship this.
    """
    stretched = (key * (len(data) // len(key) + 1))[:len(data)]
    return bytes(a ^ b for a, b in zip(data, stretched))


class KeyVersion(NamedTuple):
    version: int
    material: bytes


class MasterKey:
    """A CMK never leaves the service. You cannot export its material."""

    def __init__(self, key_id: str, description: str = ""):
        self.key_id = key_id
        self.description = description
        self.versions: List[KeyVersion] = [KeyVersion(1, secrets.token_bytes(32))]
        self.policy_principals: List[str] = []
        self.grants: Dict[str, Dict[str, Any]] = {}
        self.stats = {"encrypts": 0, "decrypts": 0, "data_keys": 0, "rotations": 0}

    @property
    def current(self) -> KeyVersion:
        return self.versions[-1]

    def rotate(self) -> int:
        """New material for NEW encryptions. Old versions are retained.

        This is why rotation is cheap: it re-encrypts nothing. Every existing
        ciphertext still names the version it was wrapped under, and that
        version still exists.
        """
        self.versions.append(KeyVersion(len(self.versions) + 1,
                                        secrets.token_bytes(32)))
        self.stats["rotations"] += 1
        return self.current.version

    def _version(self, number: int) -> KeyVersion:
        for version in self.versions:
            if version.version == number:
                return version
        raise KMSError(f"key version {number} no longer exists — any ciphertext "
                       "wrapped under it is now permanently unreadable")


class EncryptedDataKey(NamedTuple):
    key_id: str
    version: int
    wrapped: bytes
    context: Dict[str, str]


class DataKey(NamedTuple):
    plaintext: bytes                  # use it, then forget it
    encrypted: EncryptedDataKey       # store this next to the ciphertext


class KMS:
    def __init__(self):
        self.keys: Dict[str, MasterKey] = {}

    def create_key(self, key_id: str, description: str = "") -> MasterKey:
        key = MasterKey(key_id, description)
        self.keys[key_id] = key
        return key

    def _key(self, key_id: str) -> MasterKey:
        if key_id not in self.keys:
            raise KMSError(f"no such key {key_id!r}")
        return self.keys[key_id]

    @staticmethod
    def _context_bytes(context: Dict[str, str]) -> bytes:
        """Encryption context is AAD: not secret, but authenticated.

        It is bound into the wrap, so decrypting requires supplying exactly the
        same context. That turns "who may use this key" into "who may use this
        key FOR THIS PURPOSE", and it is what lets an IAM condition say
        kms:EncryptionContext:tenant = ${aws:PrincipalTag/tenant}.
        """
        canonical = "&".join(f"{k}={v}" for k, v in sorted(context.items()))
        return hashlib.sha256(canonical.encode()).digest()

    def generate_data_key(self, key_id: str,
                          context: Optional[Dict[str, str]] = None) -> DataKey:
        """The heart of envelope encryption: one key, returned twice."""
        key = self._key(key_id)
        context = context or {}
        key.stats["data_keys"] += 1

        plaintext = secrets.token_bytes(32)
        wrapping = _xor(key.current.material,
                        self._context_bytes(context))
        return DataKey(plaintext,
                       EncryptedDataKey(key_id, key.current.version,
                                        _xor(plaintext, wrapping), dict(context)))

    def decrypt_data_key(self, encrypted: EncryptedDataKey,
                         context: Optional[Dict[str, str]] = None) -> bytes:
        """Unwrap. The context must match exactly, or this fails."""
        key = self._key(encrypted.key_id)
        context = context if context is not None else {}
        key.stats["decrypts"] += 1

        if context != encrypted.context:
            raise KMSError(
                f"encryption context mismatch: wrapped with {encrypted.context}, "
                f"decrypt attempted with {context}. The context is authenticated "
                "additional data — it is not secret, but it must match.")

        version = key._version(encrypted.version)
        wrapping = _xor(version.material, self._context_bytes(encrypted.context))
        return _xor(encrypted.wrapped, wrapping)


class EnvelopeCipher:
    """The pattern you would actually use, built on the primitives above."""

    def __init__(self, kms: KMS, key_id: str):
        self.kms = kms
        self.key_id = key_id

    def encrypt(self, plaintext: bytes,
                context: Optional[Dict[str, str]] = None
                ) -> Tuple[bytes, EncryptedDataKey]:
        """One KMS call per OBJECT, not per byte. The data never leaves you."""
        data_key = self.kms.generate_data_key(self.key_id, context)
        ciphertext = _xor(plaintext, data_key.plaintext)
        # The plaintext data key goes out of scope here, which is the whole
        # discipline: hold it for the length of one encryption and no longer.
        return ciphertext, data_key.encrypted

    def decrypt(self, ciphertext: bytes, encrypted_key: EncryptedDataKey,
                context: Optional[Dict[str, str]] = None) -> bytes:
        plaintext_key = self.kms.decrypt_data_key(encrypted_key, context)
        return _xor(ciphertext, plaintext_key)


def _demo() -> None:
    kms = KMS()
    kms.create_key("alias/app-data", "application data")
    cipher = EnvelopeCipher(kms, "alias/app-data")

    print("=== Envelope encryption: the data never reaches KMS ===")
    document = b"quarterly revenue: 42,000,000" * 100
    ciphertext, wrapped = cipher.encrypt(document)
    print(f"  plaintext:      {len(document):>6} bytes")
    print(f"  ciphertext:     {len(ciphertext):>6} bytes (stays with you)")
    print(f"  wrapped key:    {len(wrapped.wrapped):>6} bytes (stored alongside)")
    print(f"  sent to KMS:    {0:>6} bytes of your data")
    print(f"  round-trips:    1 per object, regardless of size")
    recovered = cipher.decrypt(ciphertext, wrapped)
    print(f"  decrypt correct: {recovered == document}")
    print("\n  KMS caps payloads at 4KB. This 2,900-byte document would fit —")
    print("  a 2GB one would not, and the envelope pattern does not care.")

    print("\n=== Encryption context is authenticated ===")
    ciphertext, wrapped = cipher.encrypt(b"tenant A's secret",
                                         {"tenant": "A", "purpose": "billing"})
    print(f"  correct context:   "
          f"{cipher.decrypt(ciphertext, wrapped, {'tenant': 'A', 'purpose': 'billing'})!r}")
    for wrong, label in [({"tenant": "B", "purpose": "billing"}, "wrong tenant"),
                         ({"tenant": "A"}, "missing key"),
                         (None, "no context at all")]:
        try:
            cipher.decrypt(ciphertext, wrapped, wrong)
            print(f"  {label}: DECRYPTED — that is a bug")
        except KMSError as exc:
            print(f"  {label:<18} rejected: {str(exc)[:52]}...")
    print("  This is what lets an IAM policy grant use of a key only for a")
    print("  particular tenant: the condition tests the context, not the key.")

    print("\n=== Rotation re-encrypts KEYS, never DATA ===")
    key = kms.keys["alias/app-data"]
    old_cipher, old_wrapped = cipher.encrypt(b"written before rotation")
    print(f"  encrypted under version {old_wrapped.version}")

    new_version = key.rotate()
    print(f"  rotated -> current version is now {new_version}")

    new_cipher, new_wrapped = cipher.encrypt(b"written after rotation")
    print(f"  new writes use version {new_wrapped.version}")
    print(f"  old ciphertext still decrypts: "
          f"{cipher.decrypt(old_cipher, old_wrapped)!r}")
    print(f"  new ciphertext decrypts:       "
          f"{cipher.decrypt(new_cipher, new_wrapped)!r}")
    print(f"  bytes of data re-encrypted by the rotation: 0")
    print("  Rotation that broke old ciphertext would not be rotation, it would")
    print("  be an outage. Old versions are retained precisely so this works.")

    print("\n=== The limit case: deleting a key version ===")
    key.versions = [v for v in key.versions if v.version != old_wrapped.version]
    try:
        cipher.decrypt(old_cipher, old_wrapped)
        print("  still decrypted — that is a bug")
    except KMSError as exc:
        print(f"  {exc}")
    print("  There is no recovery. This is why KMS enforces a 7-30 day waiting")
    print("  period on key deletion, and why deleting a key is the one AWS")
    print("  action that can destroy data you still have every byte of.")

    print(f"\n  KMS call counts: {key.stats}")


if __name__ == "__main__":
    _demo()
