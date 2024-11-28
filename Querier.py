import requests, cx_Oracle, logging, json, psycopg2
from elasticsearch7 import Elasticsearch

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSlot, QTimer

from DomainTypes import QueryType



logger = logging.getLogger(__name__)



class OracleQuerier(QtCore.QObject):
    connectionstatusupdated = QtCore.pyqtSignal(QueryType, bool)
    queryfinished = QtCore.pyqtSignal(int, dict)

    def __init__(self, dbName = QueryType.UNKNOWN, connectionParameter = None):
        super(OracleQuerier, self).__init__()
        self.name = dbName
        self.connectionParameter = connectionParameter
        self.dbs = {}
        self.cursors = {}
        self.connected = {1: False, 2: False}

    def try_connect(self, addr, connIndex):
        try:
            if self.connectionParameter.sid is not None:
                connectString = addr + '/' + self.connectionParameter.sid
            else:
                connectString = addr
            self.dbs[connIndex] = cx_Oracle.connect(self.connectionParameter.username, self.connectionParameter.password, connectString)
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



class PostgreSqlQuerier(QtCore.QObject):
    connectionstatusupdated = QtCore.pyqtSignal(QueryType, bool)
    queryfinished = QtCore.pyqtSignal(int, dict)

    def __init__(self, dbName = QueryType.UNKNOWN, connectionParameter = None):
        super(PostgreSqlQuerier, self).__init__()
        self.name = dbName
        self.connectionParameter = connectionParameter
        self.db = None
        self.cursor = None
        self.connected = False

    def try_connect(self):
        try:
            self.db = psycopg2.connect(
                host=self.connectionParameter.address,
                database=self.connectionParameter.databasename,
                port=self.connectionParameter.port,
                user=self.connectionParameter.username,
                password=self.connectionParameter.password)
            self.cursor = self.db.cursor()

            self.connected = True
            self.connectionstatusupdated.emit(self.name, True)
        except Exception:
            self.cursor = self.db = None
            self.connected = False
            logger.exception("Connect attempt to Database %s at %s failed.", self.name, self.connectionParameter.address)

    @pyqtSlot()
    def establish_connection(self):
        self.try_connect()

    @pyqtSlot(int, str)
    def launch_query(self, tabIndex, query):
        result = {}
        try:
            self.cursor.execute(query)
            result['columns'] = [col[0] for col in self.cursor.description]
            result['data'] = []
            for row in self.cursor:
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

        self.refreshTimer = QTimer()
        self.refreshTimer.timeout.connect(self.refresh_token)
        self.refreshTimer.start(285000) #in milliseconds
        self.refreshToken = None
        self.addressConnected = None

    def try_connect(self, addr):
        connResponse = None
        try:
            tokenUrl = addr+'/auth/realms/BagIQ/protocol/openid-connect/token'
            authParams = {
                'grant_type': 'password',
                'username': self.connectionParameter.username,
                'password': self.connectionParameter.password,
                'client_id': 'BagIQ-CRC',
                'client_secret': '30e55e1f-8754-49bf-b98a-2d5258e3b53b'
            }

            connResponse = requests.post(tokenUrl, authParams, verify=False)
            if connResponse:
                if connResponse.status_code == 200:
                    responseContent = connResponse.content.decode('utf-8')
                    self.accessToken = str(json.loads(responseContent)['access_token'])
                    self.refreshToken = str(json.loads(responseContent)['refresh_token'])
                    self.connected = True
                    self.baseUrl = addr+'/bagos/rest/'
                    self.addressConnected = addr
                else:
                    logger.error('Connection attempt failed with status code %s.', connResponse.status_code)
        except Exception:
            logger.error('Connection attempt to %s failed.', addr)

    def refresh_token(self):
        if not (self.connected and self.refreshToken):
            return
        try:
            refreshUrl = self.addressConnected + '/auth/realms/BagIQ/protocol/openid-connect/token'
            refreshData = {
                'grant_type': 'refresh_token',
                'client_id': 'BagIQ-CRC',
                'client_secret': '30e55e1f-8754-49bf-b98a-2d5258e3b53b',
                'refresh_token': self.refreshToken
            }
            response = requests.post(refreshUrl, data=refreshData, timeout=12, verify=False) #timeout in seconds
            if response and response.status_code == 200:
                responseContent = response.content.decode('utf-8')
                logger.info('REST connection token refreshed.')
                self.accessToken = str(json.loads(responseContent)['access_token'])
                self.refreshToken = str(json.loads(responseContent)['refresh_token'])
            else:
                logger.error('Refreshing token failed with %s response.', response.status_code if response else 'empty')
        except Exception as e:
            logger.exception(e)

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
            requestHeaders = {
                'Content-Type':'application/json',
                'Authorization':'Bearer ' + self.accessToken
            }
            queryResponse = requests.get(self.baseUrl+query, verify=False, headers=requestHeaders)

            if queryResponse.status_code == 200:
                self.queryfinished.emit(tabIndex, queryResponse.text)
            else:
                raise Exception('REST API query failed. Status Code:', queryResponse.status_code)
        except Exception as e:
            logger.exception(e)