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

    @pyqtSlot()
    def establish_connection(self):
        try:
            self.db = cx_Oracle.connect(self.connectionParameter.username, self.connectionParameter.password, self.connectionParameter.address+'/'+self.connectionParameter.sid)
            self.cursor = self.db.cursor()

            self.connectionstatusupdated.emit(self.name, True)
        except Exception:
            self.cursor = self.db = None
            logger.exception("Connect attempt to %s Database failed.", self.name)

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

    @pyqtSlot()
    def establish_connection(self):
        loginResponse = None
        try:
            self.ui1Session = requests.Session()
            loginResponse = self.ui1Session.post('http://'+self.connectionParameter.address+'/uiservice/rest/security/login', data={'username':'MesUser','password':'change'})
            if loginResponse and loginResponse.status_code == 200:
                self.curSession = self.ui1Session
                self.baseUrl = 'http://'+self.connectionParameter.address+'/uiservice/rest/'
            else:
                self.ui2Session = requests.Session()
                loginResponse = self.ui2Session.post('http://'+self.connectionParameter.address_alt+'/uiservice/rest/security/login', data={'username':'MesUser','password':'change'})
                self.curSession = self.ui2Session
                self.baseUrl = 'http://'+self.connectionParameter.address_alt+'/uiservice/rest/'
            if loginResponse and loginResponse.status_code == 200:
                self.connected = True
        except Exception as e:
            logger.exception(e)
        finally:
            self.connectionstatusupdated.emit(QueryType.REST_HLC, self.connected)
            if not self.connected:
                logger.error('REST API cannot establish Connection:%s.', loginResponse.status_code if loginResponse else 'StatusCode N/A')
        

    @pyqtSlot(int, str)
    def launch_query(self, tabIndex, query):
        try:
            if not self.connected:
                raise Exception('REST API query failed: Not connected.')

            queryResponse = self.curSession.get(self.baseUrl+query, headers={'Content-Type':'application/json'})

            if queryResponse.status_code == 200:
                self.queryfinished.emit(tabIndex, queryResponse.text)
            else:
                raise Exception('REST API query failed. Status Code:' + queryResponse.status_code)
        except Exception as e:
            logger.exception(e)