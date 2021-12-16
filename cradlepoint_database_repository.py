import pyodbc
import uuid
import pandas as pd
from datetime import datetime
from credentials import credentials as secrets


class Database:
    @staticmethod
    def query_database(query, params=None):
        if params:
            params = parameterize(params)

        try:
            connection = pyodbc.connect(secrets.connection_string, autocommit=True)

            return pd.read_sql_query(sql=query, params=params, con=connection)
        except Exception as error:
            return pd.DataFrame([error], columns=['Error'])

    def select_part_where_part_key(self, params):
        query = "EXEC dbo.select_part_wherePartKey " \
                "@partKey = ?"
        results = self.query_database(query, params)

        return results

    def select_part_where_serial_number(self, params):
        query = "EXEC dbo.select_part_whereSerialNumber " \
                "@serialNumber = ?"
        results = self.query_database(query, params)

        return results

    def insert_part(self, params):
        query = "EXEC dbo.insert_part " \
                "@partGuid = ?, " \
                "@partDefinitionKey = ?, " \
                "@partDefinitionBaseKey = ?, " \
                "@serialNumber = ?, " \
                "@partStatusEnum = ?, " \
                "@statusUpdateUserId = ?, " \
                "@statusUpdateDate = ?"
        results = self.query_database(query, params)

        return results

    def insert_part_status_log(self, params):
        query = "EXEC dbo.insert_partStatusLog " \
                "@partKey = ?, " \
                "@startDate = ?, " \
                "@partStatusEnum = ?, " \
                "@userId = ?"
        results = self.query_database(query, params)

        return results

    def insert_part_tag_data(self, params):
        query = "EXEC dbo.model_insert_partTagData " \
                "@partGuid = ?, " \
                "@partTagDataDefinitionName = ?, " \
                "@value = ?, " \
                "@userId = ?, " \
                "@tagDate = ?"
        results = self.query_database(query, params)

        return results

    def get_cradlepoint_part_numbers(self):
        query = "SELECT partDefinitionBaseKey, partNumber, description  " \
                "FROM dbo.partDefinitionBase pdb " \
                "WHERE " \
                    "pdb.[description] LIKE '%Cradlepoint%' OR " \
                    "pdb.[description] LIKE '%IBR%'"
        results = self.query_database(query)

        return results


class Part:
    def __init__(self):
        self.part_guid: str
        self.part_definition_key: int
        self.part_definition_base_key: int
        self.serial_number: str
        self.part_status_enum: int
        self.status_update_user_id: str
        self.status_update_date: str


class PartStatus:
    def __init__(self):
        self.part_key: int
        self.start_date: str
        self.part_status_enum: int
        self.user_id: str


class PartTagData:
    def __init__(self):
        self.part_guid: str
        self.part_tag_data_definition_name: str
        self.value: str
        self.user_id: str
        self.tag_date: str


def date():
    return datetime.utcnow().isoformat(sep=' ', timespec='milliseconds')


def parameterize(item):
    try:
        params = item.__dict__.values()
    except AttributeError:
        params = [item]

    return tuple(params)
