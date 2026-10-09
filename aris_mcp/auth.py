"""Identity credentials loader for the ARIS client facade."""

import logging

import requests
from agent_connector_sdk.config import setting
from agent_connector_sdk.tls.profile import ResolvedTLSProfile
from agent_connector_sdk.tls.resolve import resolve_tls_profile

from aris_mcp.api.api_client_aris import ArisApi

logger = logging.getLogger(__name__)


def _fetch_oauth_token(tls_profile: ResolvedTLSProfile) -> str | None:
    """Fetch an OAuth2 client-credentials token when configured, else ``None``.

    ARIS Cloud / Connect issue tokens via an OAuth2 ``client_credentials`` flow
    scoped to a tenant. Set ``ARIS_OAUTH_URL`` + ``ARIS_CLIENT_ID`` +
    ``ARIS_CLIENT_SECRET`` (and optionally ``ARIS_TENANT``) to use it.
    """
    oauth_url = setting("ARIS_OAUTH_URL")
    client_id = setting("ARIS_CLIENT_ID")
    client_secret = setting("ARIS_CLIENT_SECRET")
    if not (oauth_url and client_id and client_secret):
        return None
    data = {"grant_type": "client_credentials"}
    tenant = setting("ARIS_TENANT")
    if tenant:
        data["tenant"] = tenant
    try:
        resp = requests.post(
            oauth_url,
            data=data,
            auth=(client_id, client_secret),
            timeout=30,
            **tls_profile.requests_kwargs(),
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as exc:  # noqa: BLE001 - surfaced as "no client" upstream
        logger.warning("ARIS OAuth token fetch failed: %s", exc)
        return None


def get_client() -> ArisApi:
    """Build a configured ARIS :class:`ArisApi` client from the environment.

    Connection:
        ``ARIS_API_BASE`` — REST base URL (default
        ``http://localhost/abs/api``; for ARIS Cloud this is the tenant API
        root). TLS is resolved through the shared ``AgentConfig`` transport
        profile: the standard ``SSL_CERT_FILE``/``SSL_CERT_DIR`` for a
        system-wide CA, or a named profile (``ARIS_TLS_PROFILE`` /
        ``ARIS_TLS_PROFILE_REF``) resolved from a ``TLS_PROFILES`` catalog for
        a private-PKI tenant's CA/client-cert material. Verification is
        always on — there is no boolean escape hatch.

    Auth (first match wins):
        1. OAuth2 client-credentials — ``ARIS_OAUTH_URL`` + ``ARIS_CLIENT_ID`` +
           ``ARIS_CLIENT_SECRET`` (+ optional ``ARIS_TENANT``).
        2. Static bearer — ``ARIS_TOKEN``.
        3. HTTP basic — ``ARIS_USERNAME`` / ``ARIS_PASSWORD``.

    Endpoint paths:
        ``ARIS_PATHS_JSON`` — optional JSON overriding the default ARIS Connect
        ABS REST path templates (keys: models, model, model_objects,
        model_connections, model_attributes, object_attributes) for tenants
        whose REST layout differs.
    """
    import json

    base_url = setting("ARIS_API_BASE", "http://localhost/abs/api")
    tls_profile = resolve_tls_profile(
        "aris",
        profile_name=setting("ARIS_TLS_PROFILE", "") or None,
        profile_ref=setting("ARIS_TLS_PROFILE_REF", "") or None,
    )

    token = _fetch_oauth_token(tls_profile) or (setting("ARIS_TOKEN") or None)
    username = setting("ARIS_USERNAME") or None
    password = setting("ARIS_PASSWORD") or None

    paths = None
    raw_paths = setting("ARIS_PATHS_JSON")
    if raw_paths:
        try:
            paths = json.loads(raw_paths)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ignoring invalid ARIS_PATHS_JSON: %s", exc)

    return ArisApi(
        base_url=base_url,
        token=token,
        username=username,
        password=password,
        tls_profile=tls_profile,
        paths=paths,
    )
