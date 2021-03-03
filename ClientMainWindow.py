import os, json, logging
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork
from PyQt5.QtCore import pyqtSlot

from UIClientMainWindow import Ui_clientMainWindow
from MainQueryDialogue import MainQueryDialogue

from Querier import DatabaseQuerier, ElasticSearchQuerier, RestApiQuerier
from DomainTypes import QueryType, QuerierThread
from ConfigurationManager import ConfigurationManager
from ContextTraceHighlighter import ContextTraceHighlighter
from Utilities import *


logger = logging.getLogger(__name__)

cfg = ConfigurationManager()



class ClientMainWindow(QtWidgets.QMainWindow):
    querierstarted = QtCore.pyqtSignal()
    hlcDatabaseQueryLaunched = QtCore.pyqtSignal(int, str)
    tdsDatabaseQueryLaunched = QtCore.pyqtSignal(int, str)
    elasticsearchQueryLaunched = QtCore.pyqtSignal(int, str)
    restApiQueryLaunched = QtCore.pyqtSignal(int, str)

    def __init__(self):
        super(ClientMainWindow, self).__init__()
        self.ui = Ui_clientMainWindow()
        self.ui.setupUi(self)

        self.ui.detailsDock.hide()

        self.ui.testButton.clicked.connect(self.test_button_onclick)
        self.ui.runButton.clicked.connect(self.run_button_onclick)
        self.ui.queryBundleTree.itemDoubleClicked.connect(self.query_selected)
        self.ui.queryTabs.tabBar().tabBarDoubleClicked.connect(lambda tabIndex: self.ui.queryTabs.removeTab(tabIndex))
        self.ui.actionExport_Current_Tab.triggered.connect(self.export_current_tab)

        cfg.read_configdata(self.ui.queryBundleTree)
        cfg.read_masterdata()

        self._init_queriers()
        self._establish_querier_connection()

        if cfg.locationMap:
            self.locationCompleter = QtWidgets.QCompleter([key for key in cfg.locationMap.keys()])
            self.locationCompleter.setFilterMode(QtCore.Qt.MatchContains)
            self.locationCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        else:
            self.locationCompleter = None

        self.contextTraceHighlighter = ContextTraceHighlighter(self.ui.detailsTextEdit.document())

    def _init_connection_status_labels(self):
        self.connectionStatusLabels = {}
        self.connectionStatusLabels[QueryType.DB_HLC] = self.ui.dbHlcConnLabel
        self.connectionStatusLabels[QueryType.DB_TDS] = self.ui.dbTdsConnLabel
        self.connectionStatusLabels[QueryType.ES] = self.ui.esConnLabel
        self.connectionStatusLabels[QueryType.REST_HLC] = self.ui.restHlcConnLabel

    def _update_connection_status_label(self, queryType, statusColor):
        self.connectionStatusLabels[queryType].setStyleSheet('QLabel{background-color:'+statusColor+';}')

    def _setup_querier(self, queryType, querier, launchSignal, displaySlot):
        t = self.querierThreads[queryType] = QuerierThread(querier=querier, thread=QtCore.QThread(self), querylaunched=launchSignal)
        t.querier.moveToThread(t.thread)
        t.thread.start()
        self.querierstarted.connect(t.querier.establish_connection)
        t.querier.connectionstatusupdated.connect(self.update_querier_connection_status)
        t.querylaunched.connect(t.querier.launch_query)
        t.querier.queryfinished.connect(displaySlot)

    def _init_queriers(self):
        self._init_connection_status_labels()
        self.querierThreads = {}
        if QueryType.DB_HLC in cfg.connectionParameters:
            self._setup_querier(QueryType.DB_HLC,
                DatabaseQuerier(QueryType.DB_HLC, cfg.connectionParameters[QueryType.DB_HLC]),
                self.hlcDatabaseQueryLaunched,
                self.display_database_query_result)
        else:
            self._update_connection_status_label(QueryType.DB_HLC, 'gray')
        if QueryType.DB_TDS in cfg.connectionParameters:
            self._setup_querier(QueryType.DB_TDS,
                DatabaseQuerier(QueryType.DB_TDS, cfg.connectionParameters[QueryType.DB_TDS]),
                self.tdsDatabaseQueryLaunched,
                self.display_database_query_result)
        else:
            self._update_connection_status_label(QueryType.DB_TDS, 'gray')
        if QueryType.ES in cfg.connectionParameters:
            self._setup_querier(QueryType.ES,
                ElasticSearchQuerier(cfg.connectionParameters[QueryType.ES]),
                self.elasticsearchQueryLaunched,
                self.display_elasticsearch_query_result)
        else:
            self._update_connection_status_label(QueryType.ES, 'gray')
        if QueryType.REST_HLC in cfg.connectionParameters:
            self._setup_querier(QueryType.REST_HLC,
                RestApiQuerier(cfg.connectionParameters[QueryType.REST_HLC]),
                self.restApiQueryLaunched,
                self.display_restapi_query_result)
        else:
            self._update_connection_status_label(QueryType.REST_HLC, 'gray')

    def _establish_querier_connection(self):
        self.querierstarted.emit()

    @pyqtSlot(QueryType, bool)
    def update_querier_connection_status(self, queryType, isConnected):
        self._update_connection_status_label(queryType, 'green' if isConnected else 'red')

    def _add_npdp_tooltip(self, dataModel, columnNamePattern, tooltipMap):
        if not tooltipMap:
            return
        colIndice = []
        for j in range(dataModel.columnCount()):
            if (columnNamePattern in dataModel.horizontalHeaderItem(j).text().lower()):
                colIndice.append(j)
        if not colIndice:
            return
        for i in range(dataModel.rowCount()):
            for j in colIndice:
                mapKey = dataModel.index(i, j).data()
                if mapKey in tooltipMap:
                    dataModel.setData(dataModel.index(i, j), tooltipMap[mapKey]['ToolTip Content'], QtCore.Qt.ToolTipRole)

    def _add_query_tab(self, queryName):
        queryDialogue = MainQueryDialogue(queryName)
        self.ui.queryTabs.addTab(queryDialogue, queryName)
        self.ui.queryTabs.setCurrentWidget(queryDialogue)

        if cfg.queries[queryName].modifiers:
            modifierList = [(modifier['modifier-name'], modifier['field']) for modifier in cfg.queries[queryName].modifiers]
            queryDialogue.add_modifiers(modifierList)

        if not cfg.queries[queryName].time_form:
            queryDialogue.hide_timelocation_frame()
        if not cfg.queries[queryName].location_form:
            queryDialogue.hide_locationlimit()

        queryDialogue.queryLaunched.connect(self.run_button_onclick)
        
        if self.locationCompleter:
            queryDialogue.set_location_completer(self.locationCompleter)

        if cfg.queries[queryName].query_type == QueryType.ES:
            queryDialogue.set_details_displayer(self.display_result_cell_details)


    @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def query_selected(self, item, col):
        queryName = item.text(col)
        if queryName in cfg.queries:
            self._add_query_tab(queryName)


    @pyqtSlot(QtCore.QModelIndex)
    def display_result_cell_details(self, resultCellIndex):
#        print(index.data(), ' ', index.row(), ' z ', index.column())
        if len(resultCellIndex.data()) < 100:
            return
        if self.ui.detailsDock.isHidden():
            self.ui.detailsDock.show()

        self.ui.detailsTextEdit.clear()
        self.ui.detailsTextEdit.appendPlainText(resultCellIndex.data())
        if '3_AT_S3_AT_D{3_TX' in resultCellIndex.data():
            self.ui.detailsTextEdit.appendPlainText('Table Binary Contents:')
            for lineOfText in decode_binary_routing_table_content(resultCellIndex.data()):
                self.ui.detailsTextEdit.appendPlainText(lineOfText)


    def export_current_tab(self):
        (exportFilePath, exportFileExt) = QtWidgets.QFileDialog.getSaveFileName(self, 'Export To', os.path.join(Path(__file__).parent.absolute(), 'BBQExport'),"CSV Files (*.csv);;JSON Files (*.json)")
        curTabIndex = self.ui.queryTabs.currentIndex()
        queryDialogue = self.ui.queryTabs.widget(curTabIndex)
        if exportFileExt == 'CSV Files (*.csv)':
            write_csv_file(exportFilePath, queryDialogue.result_table_as_csv())
        elif exportFileExt == 'JSON Files (*.json)':
            write_json_file(exportFilePath, queryDialogue.result_table_as_json())


    @pyqtSlot()
    def test_button_onclick(self):
        print(match_cfunit_state(4, cfg.unitStateTransitionMatrix))
        print(match_cfunit_state(1, cfg.unitStateTransitionMatrix))
        print(match_cfunit_state(8, cfg.unitStateTransitionMatrix))

        tabIndex = self.ui.queryTabs.currentIndex()
        queryDialogue = self.ui.queryTabs.widget(tabIndex)

        queryDialogue.model = QtGui.QStandardItemModel(queryDialogue)
        queryDialogue.model.setHorizontalHeaderLabels(['col 1', 'col 2', 'col np'])
        for i in range(10):            
            queryDialogue.model.appendRow([QtGui.QStandardItem(str(i * 10 + j)) for j in range(3)])

        queryDialogue.setup_result_table()


    def launch_database_query(self, tabIndex):
        queryDialogue = self.ui.queryTabs.widget(tabIndex)
        queryContent = cfg.queries[queryDialogue.queryName]

        query = queryContent.base_phrase
        query += f" WHERE (ROWNUM <= {cfg.databaseRownumLimit}) "

        if queryContent.custom_conditions:
            for cond in queryContent.custom_conditions:
                query += f" AND ({cond['condition']}) "

        if queryContent.time_form:
            (timeLimitFrom, timeLimitTo) = queryDialogue.timeLimit()
            if timeLimitFrom:
                query += f" AND ({queryContent.time_form} >= TIMESTAMP '{timeLimitFrom.toString('yyyy-MM-dd hh:mm:ss')} {cfg.localTimezoneOffsetStr}') "
            if timeLimitTo:
                query += f" AND ({queryContent.time_form} <= TIMESTAMP '{timeLimitTo.toString('yyyy-MM-dd hh:mm:ss')} {cfg.localTimezoneOffsetStr}') "

        locKey = queryDialogue.locationLimit()
        if queryContent.location_form and locKey in cfg.locationMap:
            if queryContent.location_form == '_PREDEFINED' and queryContent.query_type == QueryType.DB_TDS:
                query += f" AND ({cfg.locationMap[locKey]['TDS_LocationFilter']}) "
            else:
                locationNpLimit = ",".join(cfg.locationMap[locKey]['NP_ID'])
                query += f" AND ({queryContent.location_form} IN ({locationNpLimit})) "

        for (field, content) in queryDialogue.modifiers():
            query += f" AND ({field} LIKE '{content}') "
        if queryContent.appendix_phrase:
            query += " " + queryContent.appendix_phrase
        logger.info(query.replace('\n', ' '))

        self.querierThreads[queryContent.query_type].querylaunched.emit(tabIndex, query)

    @pyqtSlot(int, dict)
    def display_database_query_result(self, tabIndex, queryResult):
        queryDialogue = self.ui.queryTabs.widget(tabIndex)
        queryDialogue.model = QtGui.QStandardItemModel(queryDialogue)
        queryDialogue.model.setHorizontalHeaderLabels(queryResult['columns'])
        for rowOfItems in queryResult['data']:
            queryDialogue.model.appendRow(rowOfItems)

        self._add_npdp_tooltip(queryDialogue.model, 'np', cfg.npList)
        self._add_npdp_tooltip(queryDialogue.model, 'dp', cfg.dpList)

        queryDialogue.setup_result_table()

    def launch_elasticsearch_query(self, tabIndex):
        queryDialogue = self.ui.queryTabs.widget(tabIndex)
        queryContent = cfg.queries[queryDialogue.queryName]

        modifierList = []
        negativeModifierList = []
        for (field, content) in queryDialogue.modifiers():
 #           modifierType = queryContent.modifiers[field].get('modifier-type', 'match_phrase')
            if field[0:1] == '^':
                modifierList.append( {'match_phrase_prefix':{field[1:]: {"query":content}}} )
            else:
                modifierList.append( {'match_phrase':{field: {"query":content}}} )

        for cond in queryContent.custom_conditions:
            modifierList.append(json.loads(cond['condition']))

        (timeLimitFrom, timeLimitTo) = queryDialogue.timeLimit()
        if timeLimitFrom and timeLimitTo:
            strTimeLimitFrom = timeLimitFrom.toUTC().toString(QtCore.Qt.ISODate)
            strTimeLimitTo = timeLimitTo.toUTC().toString(QtCore.Qt.ISODate)
            modifierList.append({"range": {"@timestamp": {"format": "strict_date_optional_time", "gte": strTimeLimitFrom, "lte": strTimeLimitTo}}})
        
        locKey = queryDialogue.locationLimit()
        if queryContent.location_form and locKey in cfg.locationMap:
            if queryContent.location_form == '_PREDEFINED':
                modifierList.append(cfg.locationMap[locKey]['ES_LocationFilter'])

        queryBody = {
            "size": cfg.elasticsearchRownumLimit,
            "sort": [ {"@timestamp": {"order": "desc", "unmapped_type": "boolean"}} ],
            "script_fields": {},
            "docvalue_fields": [ {"field": "@timestamp", "format": "date_time"} ],
            "query": { "bool": {"must": modifierList, "must_not": negativeModifierList} }
            }       
        logger.info(json.dumps(queryBody))

        queryDialogue.model = QtGui.QStandardItemModel(queryDialogue)

        columnHeaders = [col['column-name'] for col in queryContent.columns]
        if cfg.cfMasterData and queryDialogue.queryName == 'Scada Telegrams':
            columnHeaders += ['IRD', 'Unit State Text', 'Reference', 'Signal Text', 'Aux: Cause Text / Hidden States']
        queryDialogue.model.setHorizontalHeaderLabels(columnHeaders)

        self.querierThreads[queryContent.query_type].querylaunched.emit(tabIndex, json.dumps(queryBody))


    @pyqtSlot(int, list)
    def display_elasticsearch_query_result(self, tabIndex, queryResult):
        queryDialogue = self.ui.queryTabs.widget(tabIndex)
        queryContent = cfg.queries[queryDialogue.queryName]
        resultColumns = [col['field'] for col in queryContent.columns]

        for row in queryResult:
            rowOfItems = []
            for col in resultColumns:
                cellData = row['_source'].get(col, '-')
                if col == '@timestamp':
                    cellData = convert_time_utc_to_local(cellData, cfg.localTimezone)
                elif col == 'TRANSACTION_STATUS':
                    cellData = cellData.replace('committed', 'cmt')
                elif type(cellData) == list:
                    cellData = ','.join(str(item) for item in cellData)
                elif type(cellData) != str:
                    cellData = str(cellData)
                rowOfItems.append(QtGui.QStandardItem(cellData))

            if cfg.cfMasterData and queryDialogue.queryName == 'Scada Telegrams':
                scadaAddtionalItems = []
                if row['_source'].get('TELEGRAM', '-') == '2_SS':
                    cfSignalKey = '_'.join([row['_source']['connection_name'][:5], str(row['_source']['unitId']), str(row['_source']['emId']), str(row['_source']['signalId'])])
                    if cfSignalKey in cfg.cfMasterData:
                        cfData = cfg.cfMasterData[cfSignalKey]
                        scadaAddtionalItems = [cfData['unit_ird'], '-', cfData['primary_ref'], cfData['signal_text'], cfData['cfest_causetext']]
                    else:
                        scadaAddtionalItems = ['Data Not Found' for i in range(4)]
                elif row['_source'].get('TELEGRAM', '-') == '2_US':
                    cfUnitKey = row['_source']['connection_name'][:5] + '_' + str(row['_source']['unitId'])
                    unitIrd = cfg.cfMasterData[cfUnitKey]['unit_ird'] if cfUnitKey in cfg.cfMasterData else 'Data Not Found'
                    (primaryUnitState, hiddenUnitStates) = match_cfunit_state(row['_source']['unitState'], cfg.unitStateTransitionMatrix)
                    scadaAddtionalItems = [unitIrd, primaryUnitState, '-', '-', hiddenUnitStates]
                if not scadaAddtionalItems:
                    scadaAddtionalItems = ['-' for i in range(5)]
                rowOfItems += [QtGui.QStandardItem(item) for item in scadaAddtionalItems]

            queryDialogue.model.appendRow(rowOfItems)

        self._add_npdp_tooltip(queryDialogue.model, 'np', cfg.npList)
        self._add_npdp_tooltip(queryDialogue.model, 'dp', cfg.dpList)

        queryDialogue.setup_result_table()


    def launch_restapi_query(self, tabIndex):
        queryDialogue = self.ui.queryTabs.widget(tabIndex)
        queryContent = cfg.queries[queryDialogue.queryName]

        modifiersPhrase = ''
        for (field, content) in queryDialogue.modifiers():
            modifiersPhrase += ('&' if len(modifiersPhrase) > 0 else '') + field + '=' + content

        self.querierThreads[queryContent.query_type].querylaunched.emit(tabIndex, queryContent.base_phrase+'?'+modifiersPhrase)

    @pyqtSlot(int, str)
    def display_restapi_query_result(self, tabIndex, queryResult):
        queryDialogue = self.ui.queryTabs.widget(tabIndex)
        queryContent = cfg.queries[queryDialogue.queryName]

        queryDialogue.model = QtGui.QStandardItemModel(queryDialogue)

        queryResultDict = json.loads(queryResult)
        if 'statusCode'in queryResultDict and queryResultDict['statusCode'] != 'SUCCESS':
            (resultColumns, resultData) = listize_json(queryResultDict)
            queryDialogue.model.appendRow([QtGui.QStandardItem(cell if type(cell) == str else str(cell)) for cell in resultData])
        else:
            (resultColumns, resultData) = tablize_special_rest_data(queryContent.base_phrase, queryResultDict, cfg.localTimezone)
            for resultRow in resultData:
                queryDialogue.model.appendRow([QtGui.QStandardItem(cell if type(cell) == str else str(cell)) for cell in resultRow])

        queryDialogue.model.setHorizontalHeaderLabels(resultColumns)
        queryDialogue.setup_result_table()


    @pyqtSlot()
    def run_button_onclick(self):
        curTabIndex = self.ui.queryTabs.currentIndex()
        queryName = self.ui.queryTabs.widget(curTabIndex).queryName
        queryType = cfg.queries[queryName].query_type

        if queryType == QueryType.DB_HLC or queryType == QueryType.DB_TDS:
            self.launch_database_query(curTabIndex)
        elif queryType == QueryType.ES:
            self.launch_elasticsearch_query(curTabIndex)
        elif queryType == QueryType.REST_HLC:
            self.launch_restapi_query(curTabIndex)
