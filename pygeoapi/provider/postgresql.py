

from pygeoapi.provider.sql import GenericSQLProvider


class PostgreSQLProvider(GenericSQLProvider):
    """
    A provider for querying a PostgreSQL database
    """
    def __init__(self, provider_def: dict):
        """
        PostgreSQLProvider Class constructor

        :param provider_def: provider definitions from yml pygeoapi-config.
                             data,id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor
        :returns: pygeoapi.provider.PostgreSQLProvider
        """

        driver_name = 'postgresql+psycopg2'
        extra_conn_args = {
          'client_encoding': 'utf8',
          'application_name': 'pygeoapi'
        }
        super().__init__(provider_def, driver_name, extra_conn_args)
