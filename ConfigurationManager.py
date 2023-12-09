import os, json, yaml, csv, pytz, logging
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QTreeWidgetItem

from DomainTypes import QueryType, QueryContent, UnitStateBit, ConnectionParameter


logger = logging.getLogger(__name__)



class ConfigurationManager:
    def __init__(self):
        self.queries = {}

        self.connectionParameters = {}
        self.unitStateTransitionMatrix = []

        self.npList = {}
        self.dpList = {}
        self.locationMap = {}
        self.cfMasterData = {}


    def read_configdata(self, queryBundleTree):
        with open(os.path.join(Path(__file__).parent.absolute(), 'config.yaml')) as configYamlFile:
            configData = yaml.load(configYamlFile, Loader=yaml.FullLoader)
        
        self.databaseRownumLimit = configData.get('database-rownum-limit', 10000)
        self.elasticsearchRownumLimit = configData.get('elasticsearch-rownum-limit', 500)

        self.localTimezone = pytz.timezone(configData.get('local-timezone-name', 'UTC'))
        tzOffsetStr = datetime.now(self.localTimezone).strftime('%z')
        self.localTimezoneOffsetStr = tzOffsetStr[0:len(tzOffsetStr)-2] + ':' + tzOffsetStr[-2:]
        
        self.trMasterDataFilename = configData.get('tr-masterdata-filename', '')
        self.cfMasterDataFilename = configData.get('cf-masterdata-filename', '')

        for connectionParameter in configData['connection-parameters']:
            self.connectionParameters[QueryType[connectionParameter.get('query-type', 'UNKNOWN')]] = ConnectionParameter(address=connectionParameter.get('address', ''),
                address_alt=connectionParameter.get('address-alt', ''),
                username=connectionParameter.get('username', None),
                password=connectionParameter.get('password', None),
                sid=connectionParameter.get('sid', None),
                databasename=connectionParameter.get('databasename', None),
                port=connectionParameter.get('port', None))

        if QueryType.DB_HLC in self.connectionParameters and self.connectionParameters[QueryType.DB_HLC].password == 'BAGOS_DB_DEFAULT':
            self.connectionParameters[QueryType.DB_HLC] = self.connectionParameters[QueryType.DB_HLC]._replace(password='bagos-1234')
        if QueryType.REST_HLC in self.connectionParameters and self.connectionParameters[QueryType.REST_HLC].password == 'BAGOS_REST_DEFAULT':
            self.connectionParameters[QueryType.REST_HLC] = self.connectionParameters[QueryType.REST_HLC]._replace(password='change')
        if QueryType.DB_TDS in self.connectionParameters and self.connectionParameters[QueryType.DB_TDS].password == 'TDS_DB_DEFAULT':
            self.connectionParameters[QueryType.DB_TDS] = self.connectionParameters[QueryType.DB_TDS]._replace(password='Start0815')

        for unitState in configData['scada-transition-matrix']:
            self.unitStateTransitionMatrix.append(UnitStateBit(name=unitState.get('state-name', ''),
                state_bit=unitState.get('state-bit', None),
                negative_bit=unitState.get('negative-bit', False)))

        for queryBundleData in configData['query-bundles']:
            bundleItem = QTreeWidgetItem([queryBundleData['bundle-name']])
            queryBundleTree.addTopLevelItem(bundleItem)
            for queryData in queryBundleData['bundle-content']:
                queryItem = QTreeWidgetItem([queryData['query-name']])
                bundleItem.addChild(queryItem)
                self.queries[queryData['query-name']] = QueryContent(query_type = QueryType[queryData.get('query-type', 'UNKNOWN')], 
                    static_connection_index = queryData.get('static-connection-index', -1), 
                    base_phrase = queryData.get('base-phrase', ''), 
                    time_form = queryData.get('time-form', None), 
                    location_form = queryData.get('location-form', None),
                    columns = queryData.get('columns', None), 
                    modifiers = queryData.get('modifiers', None), 
                    custom_conditions = queryData.get('custom-conditions', None),
                    appendix_phrase = queryData.get('appendix-phrase', None))
        queryBundleTree.expandAll()


    def read_masterdata(self):
        self._read_trmasterdata(self.trMasterDataFilename)
        self._read_cfmasterdata(self.cfMasterDataFilename)


    def _read_trmasterdata(self, filename):
        trMasterDataFilePath = os.path.join(Path(__file__).parent.absolute(), filename)
        if Path(trMasterDataFilePath).exists():
            with open(trMasterDataFilePath) as trMasterDataFile:
                trMasterData = json.load(trMasterDataFile)
            self.npList = trMasterData['npList']
            self.dpList = trMasterData['dpList']
            self.locationMap = trMasterData['locationMap']


    def _read_cfmasterdata(self, filename):
        cfDataCsvFilePath = os.path.join(Path(__file__).parent.absolute(), filename)
        if Path(cfDataCsvFilePath).exists():
            csvReader = csv.reader(open(cfDataCsvFilePath, 'r', encoding='utf8'))
            cfDataHeader = next(csvReader)
            cfColNr = {headerName.lower() : colNr for colNr, headerName in enumerate(cfDataHeader)}
            for cfData in csvReader:
                cfUnitKey = cfData[cfColNr['node_name']] + '_' + str(cfData[cfColNr['unit_id']])
                if not cfUnitKey in self.cfMasterData:
                    self.cfMasterData[cfUnitKey] = {'unit_ird': cfData[cfColNr['unit_ird']]}
                cfSignalKey = '_'.join([cfData[cfColNr['node_name']], str(cfData[cfColNr['unit_id']]), str(cfData[cfColNr['em_id']]), cfData[cfColNr['signal_id']]])
                self.cfMasterData[cfSignalKey] = {'unit_ird': cfData[cfColNr['unit_ird']],
                    'primary_ref': cfData[cfColNr['primary_ref']],
                    'signal_text': cfData[cfColNr['signal_text']],
                    'cfest_causetext': cfData[cfColNr['cfest_causetext']]}