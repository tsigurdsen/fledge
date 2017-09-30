# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Storage layer python client
"""

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import urllib.parse
import json
from collections import OrderedDict
from foglamp import logger

_LOGGER = logger.setup(__name__)


class PayloadBuilder(object):
    """ Payload Builder to be used in Python wrapper class for Storage Service
    Ref: https://docs.google.com/document/d/1qGIswveF9p2MmAOw_W1oXpo_aFUJd3bXBkW563E16g0/edit#
    Ref: http://json-schema.org/

    TODO: Add json validator feature directly from json schema.
          Ref: http://json-schema.org/implementations.html#validators
    """

    def __init__(self, payload=OrderedDict()):
        self.payload = payload
        with open('schemajson.json') as data_file:
            self.schema = json.load(data_file)

    # TODO: Add Validator for each section/key with the help of self.schema
    # TODO: Add tests

    @staticmethod
    def verify_condition(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 3:
                if arg[1] in ['<', '>', '=', '>=', '<=', 'LIKE', 'IN', '!=']:
                    retval = True
        return retval

    @staticmethod
    def verify_aggregation(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 2:
                if arg[0] in ['min', 'max', 'avg', 'sum', 'count']:
                    retval = True
        return retval

    @staticmethod
    def verify_orderby(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 2:
                if arg[1].upper() in ['ASC', 'DESC']:
                    retval = True
        return retval

    def SELECT(self, *args):
        if len(args) > 0:
            self.payload.update({"columns": ','.join(args)})
        return self

    def SELECTALL(self, *args):
        return self

    def FROM(self, tbl_name):
        self.payload.update({"table": tbl_name})
        return self

    def UPDATETABLE(self, tbl_name):
        return self.FROM(tbl_name)

    def COLS(self, kwargs):
        values = {}
        for key, value in kwargs.items():
            values.update({key: value})
        return values

    def UPDATE(self, **kwargs):
        self.payload.update({"values": self.COLS(kwargs)})
        return self

    def INSERT(self, **kwargs):
        self.payload.update(self.COLS(kwargs))
        return self

    def INSERTINTO(self, tbl_name):
        return self.FROM(tbl_name)

    def DELETE(self, tbl_name):
        return self.FROM(tbl_name)

    def WHERE(self, arg):
        condition = {}
        if self.verify_condition(arg):
            condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
            self.payload.update({"where": condition})
        return self

    def WHERE_AND(self, *args):
        for arg in args:
            condition = {}
            if self.verify_condition(arg):
                condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
                self.payload["where"].update({"and": condition})
        return self

    def WHERE_OR(self, *args):
        for arg in args:
            if self.verify_condition(arg):
                condition = {}
                condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
                self.payload["where"].update({"or": condition})
        return self

    def GROUPBY(self, *args):
        self.payload.update({"group": ', '.join(args)})
        return self

    def AGGREGATE(self, *args):
        for arg in args:
            aggregate = {}
            if self.verify_aggregation(arg):
                aggregate.update({"operation": arg[0], "column": arg[1]})
                if 'aggregate' in self.payload:
                    if isinstance(self.payload['aggregate'], list):
                        self.payload['aggregate'].append(aggregate)
                    else:
                        self.payload['aggregate'] = list(self.payload.get('aggregate'))
                        self.payload['aggregate'].append(aggregate)
                else:
                    self.payload.update({"aggregate": aggregate})
        return self

    def HAVING(self):
        # TODO: To be implemented
        return self

    def LIMIT(self, arg):
        if isinstance(arg, int):
            self.payload.update({"limit": arg})
        return self

    def ORDERBY(self, *args):
        for arg in args:
            sort = {}
            if self.verify_orderby(arg):
                sort.update({"column": arg[0], "direction": arg[1]})
                if 'sort' in self.payload:
                    if isinstance(self.payload['sort'], list):
                        self.payload['sort'].append(sort)
                    else:
                        self.payload['sort'] = list(self.payload.get('sort'))
                        self.payload['sort'].append(sort)
                else:
                    self.payload.update({"sort": sort})
        return self

    def execute(self):
        return dict(self.payload)

    def execute_query_params(self):
        where = self.payload['where']
        query_params = {where['column']: where['value']}
        for key, value in where.items():
            if key == 'and':
                query_params.update({value['column']: value['value']})
        return urllib.parse.urlencode(query_params)

if __name__ == "__main__":
    pb = PayloadBuilder(payload=OrderedDict())
    # Select
    sql = pb.\
        SELECT('id', 'type', 'repeat', 'process_name').\
        FROM('schedules').\
        WHERE(['id', '=', 'test']).\
        WHERE_AND(['process_name', '=', 'test']). \
        WHERE_OR(['process_name', '=', 'sleep']).\
        LIMIT(3).\
        GROUPBY('process_name', 'id').\
        ORDERBY(['process_name', 'desc']).\
        AGGREGATE(['count', 'process_name']).\
        execute()
    print(str(sql).replace("'", '"'))

    pb = PayloadBuilder(payload=OrderedDict())
    # Insert
    sql = pb.\
        INSERTINTO('schedules').\
        INSERT(id='test', process_name='sleep', type=3, repeat=45677).\
        execute()
    print(str(sql).replace("'", '"'))

    pb = PayloadBuilder(payload=OrderedDict())
    # Insert
    sql = pb.\
        UPDATETABLE('schedules').\
        UPDATE(id='test', process_name='sleep', type=3, repeat=45677).\
        WHERE(['id', '=', 'test']). \
        execute()
    print(str(sql).replace("'", '"'))

    from foglamp.core.service_registry.service_registry import Service
    from foglamp.storage.storage import Storage

    Service.Instances.register(name="store", s_type="Storage", address="0.0.0.0", port=8080)

    pb = PayloadBuilder(payload=OrderedDict())
    sql = pb.WHERE(["key", "=", "COAP_CONF"]).execute()
    tbl_name = 'configuration'
    q = str(sql).replace("'", '"')
    print(Storage().query_tbl_with_payload(tbl_name, q))

    pb = PayloadBuilder(payload=OrderedDict())
    # sql = pb.WHERE(["key", "=", "COAP_CONF"]).WHERE_AND(["ts", "=", "2017-09-15 12:33:22.619847+05:30"]).execute_query_params()
    sql = pb.WHERE(["key", "=", "COAP_CONF"]).execute_query_params()
    tbl_name = 'configuration'
    print(Storage().query_tbl(tbl_name, sql))
