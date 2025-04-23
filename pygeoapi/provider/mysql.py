
from pygeoapi.provider.sql import GenericSQLProvider


class MySQLProvider(GenericSQLProvider):

    """
    A provider for a MySQL database

    Your mysql db should have the following environment variables
    set so that the connection can be established:
        MYSQL_ROOT_PASSWORD
        MYSQL_USER
        MYSQL_PASSWORD
        MYSQL_DATABASE
    """

    def __init__(self, provider_def: dict):
        driver_name = 'mysql+pymysql'
        extra_conn_args = {
            'charset': 'utf8mb4',
        }
        super().__init__(provider_def, driver_name, extra_conn_args)
