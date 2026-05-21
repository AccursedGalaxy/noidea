"""Test doubles for the key_store seam: an in-memory keyring with no OS dependency."""

import keyring.errors


class InMemoryKeyring:
    """Mimics the keyring module interface, backed by a dict instead of the OS keyring.

    Keyed by (service_name, username) so it behaves like the real namespaced store.
    Optional failure injection lets tests exercise the half-written-state rollback paths.
    """

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}
        self.set_should_fail = False
        self.delete_should_fail = False

    def get_password(self, service_name: str, username: str) -> str | None:
        assert isinstance(service_name, str), "service_name must be a string"
        assert isinstance(username, str), "username must be a string"
        return self._store.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        assert isinstance(username, str), "username must be a string"
        assert isinstance(password, str), "password must be a string"
        if self.set_should_fail:
            raise keyring.errors.KeyringError("injected set failure")
        self._store[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        assert isinstance(username, str), "username must be a string"
        if self.delete_should_fail:
            raise keyring.errors.KeyringError("injected delete failure")
        if (service_name, username) not in self._store:
            raise keyring.errors.PasswordDeleteError("no such password")
        del self._store[(service_name, username)]
