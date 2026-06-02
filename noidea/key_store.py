"""Single owner of the API-key invariant: a keyring secret is bound to a name in keys.json.

Two stores exist because the OS keyring offers no "list usernames" API, so a JSON registry
enumerates the provider names. This module owns the coordination between them — every registered
name has a keyring secret and vice-versa — so callers never touch keyring or the registry directly.
"""

# Defer annotation evaluation: the `list` method below shadows the builtin `list`, which would
# otherwise break `-> list[str]` annotations at class-definition time on Python < 3.14.
from __future__ import annotations

import json
import os
from enum import Enum

import keyring
import keyring.errors  # Explicit import so `keyring.errors.*` resolves under static analysis.
from dotenv import load_dotenv

from noidea.config import CONFIG_DIR, SERVICE_NAME

# Load .env here because this module owns the env-var fallback for the secret.
load_dotenv()

KEYS_FILENAME = "keys.json"
KEYS_PATH = os.path.join(CONFIG_DIR, KEYS_FILENAME)

# The env var each provider's key falls back to, for CI/headless use. Ollama is absent on
# purpose: it needs no key, so it never reads one. This table is the only provider→env-var map.
_PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


class KeyStoreError(Exception):
    """A keyring or registry operation failed. Callers handle this one type, not keyring's."""


class KeyStatus(Enum):
    """The reconciliation state of a provider across the two stores."""

    PRESENT = "present"  # Registered and the keyring holds its secret.
    MISSING_SECRET = (
        "missing_secret"  # Registered but the keyring has no secret (drift).
    )
    UNREGISTERED = "unregistered"  # Not in the registry at all.


class KeyStore:
    """Owns the keyring secret store and the JSON name registry behind one interface."""

    def __init__(self, keyring_backend, registry_path: str):
        assert keyring_backend is not None, "keyring_backend must be provided"
        assert isinstance(registry_path, str) and registry_path, (
            "registry_path must be non-empty"
        )
        self._keyring = keyring_backend
        self._registry_path = registry_path

    def add(self, provider: str, secret: str) -> bool:
        """Write the secret to the keyring and register the name; True if newly registered.

        Reads the registry first so a corrupt registry fails before any store is touched.
        If the registry write fails after the keyring write, the keyring secret is rolled
        back so no orphan secret survives the failure.
        """
        assert isinstance(provider, str) and provider, (
            "provider must be a non-empty string"
        )
        assert isinstance(secret, str) and secret, "secret must be a non-empty string"
        names = self._read_registry()
        try:
            self._keyring.set_password(SERVICE_NAME, provider, secret)
        except keyring.errors.KeyringError as error:
            raise KeyStoreError(
                f"could not write secret to keyring: {error}"
            ) from error
        if provider in names:
            return False
        names.append(provider)
        try:
            self._write_registry(names)
        except KeyStoreError:
            self._delete_quietly(provider)
            raise
        return True

    def remove(self, provider: str) -> bool:
        """Remove the name from the registry and the secret from the keyring; True if it existed."""
        assert isinstance(provider, str) and provider, (
            "provider must be a non-empty string"
        )
        names = self._read_registry()
        if provider not in names:
            return False
        names.remove(provider)
        self._write_registry(names)
        try:
            self._keyring.delete_password(SERVICE_NAME, provider)
        except keyring.errors.PasswordDeleteError:
            # The secret was already absent (prior drift); the goal state is reached anyway.
            pass
        except keyring.errors.KeyringError as error:
            # Roll back the registry so the two stores never disagree after a failure.
            names.append(provider)
            self._write_registry(names)
            raise KeyStoreError(
                f"could not delete secret from keyring: {error}"
            ) from error
        return True

    def list(self) -> list[str]:
        """Return the registered provider names."""
        names = self._read_registry()
        assert isinstance(names, list), "registry must be a list"
        return names

    def get(self, provider: str) -> str | None:
        """Return the keyring secret, falling back to the provider's env var if it has one."""
        assert isinstance(provider, str) and provider, (
            "provider must be a non-empty string"
        )
        secret = self._read_secret(provider)
        if not secret:
            # No keyless provider (e.g. ollama) is in the table, so it never reads an env var.
            env_var = _PROVIDER_ENV_VARS.get(provider)
            if env_var:
                secret = os.environ.get(env_var)
        assert secret is None or isinstance(secret, str), (
            "secret must be a string or None"
        )
        return secret

    def status_of(self, provider: str) -> KeyStatus:
        """Reconcile the two stores for one provider into a single status."""
        assert isinstance(provider, str) and provider, (
            "provider must be a non-empty string"
        )
        registered = provider in self._read_registry()
        # Read the keyring directly, bypassing the env fallback, so real drift stays visible.
        has_secret = bool(self._read_secret(provider))
        if not registered:
            return KeyStatus.UNREGISTERED
        return KeyStatus.PRESENT if has_secret else KeyStatus.MISSING_SECRET

    def _read_secret(self, provider: str) -> str | None:
        """Read the raw keyring secret, surfacing backend failures as KeyStoreError."""
        try:
            return self._keyring.get_password(SERVICE_NAME, provider)
        except keyring.errors.KeyringError as error:
            raise KeyStoreError(
                f"could not read secret from keyring: {error}"
            ) from error

    def _delete_quietly(self, provider: str) -> None:
        """Best-effort keyring delete used to roll back a half-written add; never raises."""
        try:
            self._keyring.delete_password(SERVICE_NAME, provider)
        except keyring.errors.KeyringError:
            # Rollback is best-effort: the original failure is what the caller must see.
            pass

    def _read_registry(self) -> list[str]:
        """Read the registry, treating a missing file as an empty registry."""
        if not os.path.exists(self._registry_path):
            return []
        try:
            with open(self._registry_path) as f:
                names = json.load(f)
        except (OSError, json.JSONDecodeError) as error:
            raise KeyStoreError(
                f"could not read registry {self._registry_path}: {error}"
            ) from error
        assert isinstance(names, list), "registry must deserialize to a list"
        return names

    def _write_registry(self, names: list[str]) -> None:
        assert isinstance(names, list), "names must be a list"
        try:
            with open(self._registry_path, "w") as f:
                json.dump(names, f)
        except OSError as error:
            raise KeyStoreError(
                f"could not write registry {self._registry_path}: {error}"
            ) from error


key_store = KeyStore(keyring, KEYS_PATH)
