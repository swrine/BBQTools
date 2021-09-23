import datetime, re, logging
from PyQt5 import QtCore, QtGui, QtWidgets, QtSql
from PyQt5.QtCore import pyqtSlot

from UIMainQueryDialogue import Ui_mainQueryDialogue
from ResultTableProxyModel import ResultTableProxyModel


logger = logging.getLogger(__name__)


class MainQueryDialogue(QtWidgets.QWidget):
    queryLaunched = QtCore.pyqtSignal()

    def __init__(self, queryName):
        super(MainQueryDialogue, self).__init__()

        self.queryName = queryName

        self.ui = Ui_mainQueryDialogue()
        self.ui.setupUi(self)
        self.ui.resultTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.ui.resultTable.horizontalHeader().setMaximumSectionSize(750)

        self.update_timelimit_to_recent(3)

        self.ui.timeLimitRecent24hButton.clicked.connect(lambda: self.update_timelimit_to_recent(24))
        self.ui.timeLimitRecent12hButton.clicked.connect(lambda: self.update_timelimit_to_recent(12))
        self.ui.timeLimitRecent3hButton.clicked.connect(lambda: self.update_timelimit_to_recent(3))
        self.ui.timeLimitRecent1hButton.clicked.connect(lambda: self.update_timelimit_to_recent(1))

        self.ui.locationLimit.returnPressed.connect(self.queryLaunched)
        self.ui.filterLineEdit.returnPressed.connect(self.execute_filter)

        self.ui.actionFilter_Selected_Value.triggered.connect(self.filter_selected_value)
        self.ui.actionMark_Unmark_Selected_Rows.triggered.connect(self.mark_unmark_selected_rows)

    def timeLimit(self):
        return (self.ui.timeLimitFrom.dateTime(), self.ui.timeLimitTo.dateTime())

    def locationLimit(self):
        return self.ui.locationLimit.text()

    def modifiers(self):
        ret = []
        for modifier in self.ui.modifiersFrame.findChildren(QtWidgets.QLineEdit):
            if modifier.text():
                ret.append((modifier.objectName()[9:], modifier.text()))
        return ret

    def hide_timelocation_frame(self):
        self.ui.timeLocationFrame.hide()

    def hide_locationlimit(self):
        self.ui.locationLimitLabel.hide()
        self.ui.locationLimit.hide()

    def set_location_completer(self, completer):
        self.ui.locationLimit.setCompleter(completer)
    
    def set_details_displayer(self, displayer):
        self.ui.resultTable.doubleClicked.connect(displayer)

    def add_modifiers(self, modifierList):
        for (name, field) in modifierList:
            label = QtWidgets.QLabel(self.ui.modifiersFrame)
            self.ui.modifiersFrameLayout.addWidget(label)
            label.setText(name)

            lineEdit = QtWidgets.QLineEdit(self.ui.modifiersFrame)
            lineEdit.setMaximumSize(QtCore.QSize(100, 16777215))
            lineEdit.setObjectName("modifier_"+field)
            self.ui.modifiersFrameLayout.addWidget(lineEdit)
            lineEdit.returnPressed.connect(self.queryLaunched)
        spacerItem = QtWidgets.QSpacerItem(100, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.ui.modifiersFrameLayout.addItem(spacerItem)

    def update_timelimit_to_recent(self, h):
        nowDateTime = QtCore.QDateTime.currentDateTime()
        self.ui.timeLimitFrom.setDateTime(nowDateTime.addSecs(-h*3600))
        self.ui.timeLimitTo.setDateTime(nowDateTime.addSecs(3600))
    
    def setup_filter_field_completer(self):
        filterFieldCompleterList = []
        for colIndex in range(self.model.columnCount()):
            filterFieldCompleterList.append(self.model.horizontalHeaderItem(colIndex).text().replace(' ', '_'))
        self.filterFieldCompleter = QtWidgets.QCompleter(filterFieldCompleterList)
        self.filterFieldCompleter.setFilterMode(QtCore.Qt.MatchContains)
        self.filterFieldCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.ui.filterLineEdit.setCompleter(self.filterFieldCompleter)

    def setup_result_table(self):
        self.proxy = ResultTableProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setColumnHeaderMap()

        self.ui.resultTable.setModel(self.proxy)
        self.ui.resultTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self.ui.resultTable.addAction(self.ui.actionMark_Unmark_Selected_Rows)
        self.ui.resultTable.addAction(self.ui.actionFilter_Selected_Value)

        self.setup_filter_field_completer()

    @pyqtSlot()
    def filter_selected_value(self):
        curCellIndex = self.ui.resultTable.currentIndex()
        filterText = self.model.horizontalHeaderItem(curCellIndex.column()).text().replace(' ', '_')+':'+curCellIndex.data()
        self.ui.filterLineEdit.setText(filterText)
        self.execute_filter()
    
    @pyqtSlot()
    def mark_unmark_selected_rows(self):
        selectedRows = [self.proxy.mapToSource(viewIndex).row() for viewIndex in self.ui.resultTable.selectionModel().selectedIndexes()]
        focusRow = self.proxy.mapToSource(self.ui.resultTable.currentIndex()).row()
        if not focusRow in selectedRows:
            selectedRows.append(focusRow)
        for i in selectedRows:
            filledColor = QtGui.QBrush(QtCore.Qt.yellow) if not self.model.data(self.model.index(i, 0), QtCore.Qt.BackgroundRole) else None
            for j in range(self.model.columnCount()):
                self.model.setData(self.model.index(i, j), filledColor, QtCore.Qt.BackgroundRole)

    @pyqtSlot()
    def execute_filter(self):
        self.proxy.updateFilter(self.ui.filterLineEdit.text())

    def result_table_as_json(self):
        exportDataRows = []
        columnHeaders = [self.model.horizontalHeaderItem(j).text() for j in range(self.model.columnCount())]
        for i in range(self.proxy.rowCount()):
            exportRow = {}
            for j in range(self.proxy.columnCount()):
                exportRow[columnHeaders[j]] = self.proxy.index(i, j).data()
            exportDataRows.append(exportRow)
        return {'data':exportDataRows}

    def result_table_as_csv(self):
        exportData = []
        columnHeaders = [self.model.horizontalHeaderItem(j).text() for j in range(self.model.columnCount())]
        exportData.append(columnHeaders)
        for i in range(self.proxy.rowCount()):
            exportData.append([self.proxy.index(i, j).data() for j in range(self.proxy.columnCount())])
        return exportData