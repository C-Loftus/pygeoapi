

from pygeoapi.provider.sql import GenericSQLProvider


class PostgreSQLProvider(GenericSQLProvider):
    """
    A provider for querying a PostgreSQL database
    """
    
    def __init__(self, provider_def):

        driver_name = 'postgresql+psycopg2'
        extra_conn_args = {
          'client_encoding': 'utf8',
          'application_name': 'pygeoapi'
        } 
        super().__init__(provider_def, driver_name, extra_conn_args)