"""TLS-profile and credential-priority coverage for ``aris_mcp.auth``.

Guards against a regression back to a bare ``ARIS_SSL_VERIFY`` boolean or a
``urllib3.disable_warnings`` call: TLS verification must stay on by default
and a configured profile must be honoured end-to-end.
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from aris_mcp.auth import get_client


def _self_signed_ca_pem(common_name: str) -> str:
    """A minimal real (parseable) self-signed CA certificate for TLS tests."""
    now = datetime.now(UTC)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .sign(key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.PEM).decode("ascii")


def test_get_client_verifies_by_default():
    """No TLS env vars configured -> the resolved profile still verifies."""
    with patch.dict(os.environ, {"ARIS_API_BASE": "http://aris.test/abs/api"}, clear=True):
        client = get_client()
        assert client.tls_profile.verify_enabled is True
        assert client._session.verify is True


def test_get_client_honors_ca_bundle_profile(tmp_path):
    """A configured CA bundle (the standard SSL_CERT_FILE override) is
    resolved and applied to the session — proving a private-PKI tenant is
    configured with its CA rather than by disabling verification."""
    ca_bundle = tmp_path / "aris-ca.pem"
    ca_bundle.write_text(_self_signed_ca_pem("Synthetic ARIS Test Root"))
    with patch.dict(
        os.environ,
        {
            "ARIS_API_BASE": "https://aris.internal/abs/api",
            "SSL_CERT_FILE": str(ca_bundle),
        },
        clear=True,
    ):
        client = get_client()
        assert client.tls_profile.verify_enabled is True
        assert client.tls_profile.ca_bundle_path == ca_bundle
        assert client._session.verify == str(ca_bundle)


def test_get_client_honors_named_tls_profile():
    """``ARIS_TLS_PROFILE`` selects a named profile from the catalog — proving
    the documented env var is actually wired, not merely described."""
    catalog = (
        '{"profiles": {"private-pki": {"system_trust": false, '
        '"ca_directory": "/etc/ssl/certs"}}}'
    )
    with patch.dict(
        os.environ,
        {
            "ARIS_API_BASE": "https://aris.internal/abs/api",
            "ARIS_TLS_PROFILE": "private-pki",
            "TLS_PROFILES": catalog,
        },
        clear=True,
    ):
        client = get_client()
        assert client.tls_profile.verify_enabled is True
        assert client.tls_profile.name == "private-pki"
        assert client.tls_profile.system_trust is False


def test_oauth_token_fetch_uses_resolved_tls_profile():
    """The OAuth2 client-credentials POST uses the resolved profile, never a
    bare boolean — a regression here would silently downgrade verification
    on the one raw ``requests.post`` call outside the session wrapper."""
    with patch.dict(
        os.environ,
        {
            "ARIS_API_BASE": "http://aris.test/abs/api",
            "ARIS_OAUTH_URL": "https://aris.test/oauth/token",
            "ARIS_CLIENT_ID": "client-id",
            "ARIS_CLIENT_SECRET": "client-secret",
        },
        clear=True,
    ):
        with patch("aris_mcp.auth.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"access_token": "tok"}
            mock_post.return_value.raise_for_status.return_value = None
            get_client()
            assert mock_post.called
            _, kwargs = mock_post.call_args
            assert kwargs["verify"] is True
