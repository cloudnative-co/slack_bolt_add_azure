import logging
import os
from logging import Logger
from typing import Optional

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from slack_bolt.authorization.authorize import InstallationStoreAuthorize
from slack_bolt.oauth import OAuthFlow
from slack_sdk import WebClient
from slack_sdk_azure.oauth.installation_store.azure_blob import AzureBlobInstallationStore
from slack_sdk_azure.oauth.state_store.azure_blob import AzureBlobOAuthStateStore

from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.util.utils import create_web_client


class AzureBlobOAuthFlow(OAuthFlow):
    _logger : Logger

    def __init__(
        self,
        *,
        client: Optional[WebClient] = None,
        logger: Optional[Logger] = None,
        settings: Optional[OAuthSettings] = None,
        oauth_state_container_name: Optional[str] = None,  # required
        installation_container_name: Optional[str] = None,  # required
    ):
        logger = logger or logging.getLogger(__name__)
        client_id = os.environ.get("SLACK_CLIENT_ID")
        client_secret = os.environ.get("SLACK_CLIENT_SECRET")
        connect_str = os.environ.get("AZURE_BLOB_CONNECTION_STR")
        oauth_state_container_name = oauth_state_container_name or os.environ["SLACK_STATE_BLOB_CONTAINER_NAME"]
        installation_container_name = installation_container_name or os.environ["SLACK_INSTALLATION_BLOB_CONTAINER_NAME"]

        if client_id is None:
            msg = "Slack client-id is not set as an environment variable"
            logger.error(msg)
            raise Exception(msg)
        if client_secret is None:
            msg = "Slack client-secret is not set as an environment variable"
            logger.error(msg)
            raise Exception(msg)

        settings = settings or OAuthSettings(client_id=client_id, client_secret=client_secret)

        blob_client = BlobServiceClient.from_connection_string(connect_str)
        self._logger = logger

        if settings.state_store is None or not isinstance(settings.state_store, AzureBlobOAuthStateStore):
            settings.state_store = AzureBlobOAuthStateStore(
                logger=logger,
                client=blob_client,
                container_name=oauth_state_container_name,
                expiration_seconds=settings.state_expiration_seconds,
            )

        if settings.installation_store is None or not isinstance(
            settings.installation_store, AzureBlobInstallationStore
        ):
            settings.installation_store = AzureBlobInstallationStore(
                logger=logger,
                client=blob_client,
                container_name=installation_container_name,
                client_id=settings.client_id,
            )

        # Set up authorize function to surely use this installation_store.
        # When a developer use a settings initialized outside this constructor,
        # the settings may already have pre-defined authorize.
        # In this case, the /slack/events endpoint doesn't work along with the OAuth flow.
        settings.authorize = InstallationStoreAuthorize(
            logger=logger,
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            installation_store=settings.installation_store,
            bot_only=settings.installation_store_bot_only,
            user_token_resolution=(
                settings.user_token_resolution if settings is not None else "authed_user"
            ),
        )

        OAuthFlow.__init__(self, client=client, logger=logger, settings=settings)

    @property
    def client(self) -> WebClient:
        if self._client is None:
            self._client = create_web_client(logger=self.logger)
        return self._client

    @property
    def logger(self) -> Logger:
        if self._logger is None:
            self._logger = logging.getLogger(__name__)
        return self._logger
