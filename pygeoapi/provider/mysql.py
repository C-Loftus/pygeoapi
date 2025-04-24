
from pygeoapi.provider.sql import GenericSQLProvider


class MySQLProvider(GenericSQLProvider):

    """
    A provider for a MySQL database
    """

    def __init__(self, provider_def: dict):
        """
        MySQLProvider Class constructor

        :param provider_def: provider definitions from yml pygeoapi-config.
                             data,id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor
        :returns: pygeoapi.provider.MySQLProvider
        """

        driver_name = 'mysql+pymysql'
        extra_conn_args = {
            'charset': 'utf8mb4',
        }
        super().__init__(provider_def, driver_name, extra_conn_args)
