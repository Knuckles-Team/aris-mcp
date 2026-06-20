"""Identity credentials loader for the ARIS client facade."""

import requests
from agent_utilities.base_utilities import get_logger, to_boolean
from agent_utilities.core.config import setting

from aris_mcp.api.api_client_aris import ArisApi

logger = get_logger(__name__)


def _fetch_oauth_token() -> str | None:
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
            verify=to_boolean(setting("ARIS_SSL_VERIFY", True)),
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
        root). ``ARIS_SSL_VERIFY`` (default ``True``).

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
    verify = to_boolean(setting("ARIS_SSL_VERIFY", True))

    token = _fetch_oauth_token() or (setting("ARIS_TOKEN") or None)
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
        verify=verify,
        paths=paths,
    )
