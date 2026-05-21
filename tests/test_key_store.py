"""Unit tests for the key_store module, exercised through an in-memory keyring fake."""

import pytest

from noidea.config import SERVICE_NAME
from noidea.key_store import KeyStatus, KeyStore, KeyStoreError
from tests.fakes import InMemoryKeyring


def _make_store(tmp_path):
    """Build a KeyStore wired to a fake keyring and a temp registry file."""
    return KeyStore(InMemoryKeyring(), str(tmp_path / "keys.json"))


class TestAddAndGet:
    def test_add_then_get_round_trips_the_secret(self, tmp_path):
        store = _make_store(tmp_path)
        store.add("anthropic", "sk-secret-123")
        assert store.get("anthropic") == "sk-secret-123"

    def test_add_returns_true_when_newly_registered(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.add("anthropic", "sk-1") is True

    def test_add_returns_false_when_already_registered(self, tmp_path):
        store = _make_store(tmp_path)
        store.add("anthropic", "sk-1")
        assert store.add("anthropic", "sk-2") is False

    def test_get_returns_none_when_no_secret_and_no_env(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        store = _make_store(tmp_path)
        assert store.get("anthropic") is None

    def test_get_falls_back_to_env_var_for_anthropic(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key-456")
        store = _make_store(tmp_path)
        assert store.get("anthropic") == "env-key-456"


class TestList:
    def test_list_is_empty_for_fresh_store(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.list() == []

    def test_list_returns_registered_names(self, tmp_path):
        store = _make_store(tmp_path)
        store.add("anthropic", "sk-1")
        assert store.list() == ["anthropic"]


class TestRemove:
    def test_remove_clears_both_stores(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        store = _make_store(tmp_path)
        store.add("anthropic", "sk-1")
        assert store.remove("anthropic") is True
        assert store.list() == []
        assert store.get("anthropic") is None

    def test_remove_returns_false_when_not_registered(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.remove("anthropic") is False


class TestStatusOf:
    def test_present_when_registered_with_secret(self, tmp_path):
        store = _make_store(tmp_path)
        store.add("anthropic", "sk-1")
        assert store.status_of("anthropic") is KeyStatus.PRESENT

    def test_unregistered_when_never_added(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.status_of("anthropic") is KeyStatus.UNREGISTERED

    def test_missing_secret_when_registered_but_keyring_empty(self, tmp_path):
        store = _make_store(tmp_path)
        store.add("anthropic", "sk-1")
        # Simulate drift: the registry keeps the name but the keyring secret vanishes.
        store._keyring.delete_password(SERVICE_NAME, "anthropic")
        assert store.status_of("anthropic") is KeyStatus.MISSING_SECRET


class TestAtomicity:
    """A failure on either store leaves no observable half-written state."""

    def test_add_rolls_back_keyring_when_registry_write_fails(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        fake = InMemoryKeyring()
        # A registry path under a missing directory makes the registry write fail.
        store = KeyStore(fake, str(tmp_path / "missing" / "keys.json"))
        with pytest.raises(KeyStoreError):
            store.add("anthropic", "sk-1")
        assert fake.get_password(SERVICE_NAME, "anthropic") is None

    def test_add_raises_and_leaves_registry_empty_when_keyring_fails(self, tmp_path):
        fake = InMemoryKeyring()
        fake.set_should_fail = True
        store = KeyStore(fake, str(tmp_path / "keys.json"))
        with pytest.raises(KeyStoreError):
            store.add("anthropic", "sk-1")
        assert store.list() == []

    def test_remove_rolls_back_registry_when_keyring_delete_fails(self, tmp_path):
        fake = InMemoryKeyring()
        store = KeyStore(fake, str(tmp_path / "keys.json"))
        store.add("anthropic", "sk-1")
        fake.delete_should_fail = True
        with pytest.raises(KeyStoreError):
            store.remove("anthropic")
        assert store.list() == ["anthropic"]
