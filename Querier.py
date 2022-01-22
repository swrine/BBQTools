import requests, cx_Oracle, logging
from elasticsearch import Elasticsearch

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSlot

from DomainTypes import QueryType



logger = logging.getLogger(__name__)



class DatabaseQuerier(QtCore.QObject):
    connectionstatusupdated = QtCore.pyqtSignal(QueryType, bool)
    queryfinished = QtCore.pyqtSignal(int, dict)

    def __init__(self, dbName = QueryType.UNKNOWN, connectionParameter = None):
        super(DatabaseQuerier, self).__init__()
        self.name = dbName
        self.connectionParameter = connectionParameter
        self.dbs = {}
        self.cursors = {}
        self.connected = {1: False, 2: False}

    def try_connect(self, addr, connIndex):
        try:
            self.dbs[connIndex] = cx_Oracle.connect(self.connectionParameter.username, self.connectionParameter.password, addr+'/'+self.connectionParameter.sid)
            self.cursors[connIndex] = self.dbs[connIndex].cursor()

            self.connected[connIndex] = True
            self.connectionstatusupdated.emit(self.name, True)
        except Exception:
            self.cursors[connIndex] = self.dbs[connIndex] = None
            self.connected[connIndex] = False
            logger.exception("Connect attempt to Database %s at %s failed.", self.name, addr)

    @pyqtSlot()
    def establish_connection(self):
        self.try_connect(self.connectionParameter.address, 1)
        if self.connectionParameter.address_alt:
            self.try_connect(self.connectionParameter.address_alt, 2)

    @pyqtSlot(int, str, int)
    def launch_query(self, tabIndex, query, connIndex):
        if connIndex != -1:
            logger.info('Query toward Alt DB:%s', query)
            if not self.connected[connIndex]:
                logger.exception('DB Query to DB of connection index %d, but the DB is not connected.', connIndex)
                return
        else:
            logger.info('Query can be sent to any DB:%s', query)
            connIndex = 1 if self.connected[1] else 2
        result = {}
        try:
            self.cursors[connIndex].execute(query)
            result['columns'] = [col[0] for col in self.cursors[connIndex].description]
            result['data'] = []
            for row in self.cursors[connIndex]:
                result['data'].append([QtGui.QStandardItem(cell if type(cell) == str else str(cell)) for cell in row])
            self.queryfinished.emit(tabIndex, result)
        except:
            logger.exception('DB Query Failed:%s', query)



class ElasticSearchQuerier(QtCore.QObject):
    connectionstatusupdated = QtCore.pyqtSignal(QueryType, bool)
    queryfinished = QtCore.pyqtSignal(int, list)

    def __init__(self, connectionParameter = None):
        super(ElasticSearchQuerier, self).__init__()
        self.connectionParameter = connectionParameter

    @pyqtSlot()
    def establish_connection(self):
        try:
            self.es = Elasticsearch([self.connectionParameter.address])
            if self.es.ping():
                self.connectionstatusupdated.emit(QueryType.ES, True)
        except Exception:
            self.es = None
            logger.exception("Connect attempt to Elasticsearch server failed.")

    @pyqtSlot(int, str)
    def launch_query(self, tabIndex, query):
        result = self.es.search(body=query)
        
        self.queryfinished.emit(tabIndex, result['hits']['hits'])



class RestApiQuerier(QtCore.QObject):
    connectionstatusupdated = QtCore.pyqtSignal(QueryType, bool)
    queryfinished = QtCore.pyqtSignal(int, str)

    def __init__(self, connectionParameter = None):
        super(RestApiQuerier, self).__init__()
        self.connectionParameter = connectionParameter
        self.connected = False

    def try_connect(self, addr):
        connResponse = None
        try:
            connResponse = requests.get('http://'+addr+'/bagos/rest/ping', timeout=5)
            if connResponse and connResponse.status_code == 200 and connResponse.text == "pong":
                self.connected = True
                self.baseUrl = 'http://'+addr+'/bagos/rest/'
        except Exception:
            logger.error('Connection attempt to %s failed.', addr)

    @pyqtSlot()
    def establish_connection(self):
        self.try_connect(self.connectionParameter.address)
        if not self.connected and self.connectionParameter.address_alt:
            self.try_connect(self.connectionParameter.address_alt)

        self.connectionstatusupdated.emit(QueryType.REST_HLC, self.connected)
        if not self.connected:
            logger.error('REST API cannot establish Connection.')

    @pyqtSlot(int, str)
    def launch_query(self, tabIndex, query):
        try:
            if not self.connected:
                raise Exception('REST API query failed: Not connected.')

            queryResponse = requests.get(self.baseUrl+query, headers={'Content-Type':'application/json'})

            if queryResponse.status_code == 200:
                self.queryfinished.emit(tabIndex, queryResponse.text)
            else:
                raise Exception('REST API query failed. Status Code:', queryResponse.status_code)
        except Exception as e:
            logger.exception(e)