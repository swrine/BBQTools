import logging
from PyQt5 import QtCore, QtGui

from BBQLFilterParsing import bbqlExpression


logger = logging.getLogger(__name__)


class ResultTableProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        QtCore.QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.bbqlFilter = None

    def setColumnHeaderMap(self):
        self.columnHeaderMap = {}
        for colIndex in range(self.sourceModel().columnCount()):
            colName = self.sourceModel().horizontalHeaderItem(colIndex).text().lower().replace(' ', '_')
            self.columnHeaderMap[colName] = colIndex

    def updateFilter(self, filterText):
        if not filterText:
            self.bbqlFilter = None
            self.invalidateFilter()
            return
        try:
            self.bbqlFilter = bbqlExpression.parseString(filterText)[0]
            self.bbqlFilterFields = self.bbqlFilter.filterFields()
            self.rowData = {}
            
            self.invalidateFilter()
        except Exception as e:
            logger.error(e)
            self.bbqlFilter = None

    def filterAcceptsRow(self, sourceRow, sourceParent):
        if not self.bbqlFilter:
            return True

        for field in self.bbqlFilterFields:
            idx = self.sourceModel().index(sourceRow, self.columnHeaderMap[field], sourceParent)
            self.rowData[field] = self.sourceModel().data(idx)

        ret = self.bbqlFilter.evaluateFilter(self.rowData)
        return ret