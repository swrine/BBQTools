from PyQt5 import QtCore, QtGui


def format(color, style=''):
    _color = QtGui.QColor()
    _color.setNamedColor(color)
    _format = QtGui.QTextCharFormat()
    _format.setForeground(_color)
    if 'bold' in style:
        _format.setFontWeight(QtGui.QFont.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)
    return _format

STYLES = {
    'domainword': format('black', 'italic'),
    'domainvalue': format('darkMagenta', 'bold'),
    'nullword': format('darkGray', 'bold'),
    'redword': format('red', 'bold'),    
    'brace': format('darkBlue', 'bold'),
    'np': format('darkMagenta', 'bold'),
    'dp': format('magenta', 'bold'),
    'trayid': format('blue', 'bold'),
    'globalid': format('blue', 'bold'),
    'lpn': format('darkCyan', 'bold'),
    'tcstep': format('black', 'bold'),
}


class ContextTraceHighlighter(QtGui.QSyntaxHighlighter):
    domainwords = ['MODULE', 'METHOD', 'TELEGRAM', 'PLC_ID', 'UNIT_ID', 'NP_ID', 'DP_ID', 'CONT_ID', 'GLOBAL_ID', 'LPN',
        'LOADING_STATE', 'TimeState', 'BagTagStateDerived', 'transportState', 'OperationalState']
    domainvalues = ['true', 'false', 'LY', 'LN', 'CY', 'CN', '3_DR', '3_DS', '3_RD', '3_RN', '3_CL', '3_XO', 'IATA']
    nullwords = ['null', 'NONE']
    redwords = ['error', 'exception', 'problem', 'warn', 'PBL_DEST']
    braces = ['\<', '\>', '\[', '\]']
    def __init__(self, document):
        QtGui.QSyntaxHighlighter.__init__(self, document)

        rules = []

        rules += [(r'\b%s\b' % w, 0, STYLES['domainword']) for w in ContextTraceHighlighter.domainwords]
        rules += [(r'\b%s\b' % w, 0, STYLES['domainvalue']) for w in ContextTraceHighlighter.domainvalues]
        rules += [(r'\b%s\b' % w, 0, STYLES['redword']) for w in ContextTraceHighlighter.redwords]
        rules += [(r'\b%s\b' % w, 0, STYLES['nullword']) for w in ContextTraceHighlighter.nullwords]        
        rules += [(r'%s' % b, 0, STYLES['brace']) for b in ContextTraceHighlighter.braces]

        rules += [
            (r'\bNP_ID\b:([A-Za-z0-9]+)', 1, STYLES['np']),
            (r'\"notificationPointId\":([A-Za-z0-9]+)', 1, STYLES['np']),
            (r'\bDP_ID\b:([A-Za-z0-9]+)', 1, STYLES['dp']),
            (r'\"destinationId\":([A-Za-z0-9]+)', 1, STYLES['dp']),

            (r'\bCONT_ID\b:([A-Za-z0-9]+)', 1, STYLES['trayid']),
            (r'\"trayId\":([A-Za-z0-9]+)', 1, STYLES['trayid']),
            (r'\bGLOBAL_ID\b:([A-Za-z0-9]+)', 1, STYLES['globalid']),
            (r'\"globalId\":([A-Za-z0-9]+)', 1, STYLES['globalid']),
            (r'\bLPN\b:([A-Za-z0-9]+)', 1, STYLES['lpn']),
            (r'\"transportGoodsId[0-9]?\":([A-Za-z0-9"]+)', 1, STYLES['lpn']),
            
            (r'\bTimeState\b:([A-Za-z0-9_]+)', 1, STYLES['domainvalue']),
            (r'\bBagTagStateDerived\b:([A-Za-z0-9_]+)', 1, STYLES['domainvalue']),
            (r'\btransportState\b:([A-Za-z0-9_]+)', 1, STYLES['domainvalue']),
            (r'\bOperationalState\b:([A-Za-z0-9_]+)', 1, STYLES['domainvalue']),

            (r'\bStep\b.[A-Z_]*\-?[0-9.]+', 0, STYLES['tcstep'])
        ]

        self.rules = [(QtCore.QRegularExpression(pat, QtCore.QRegularExpression.CaseInsensitiveOption), index, fmt) for (pat, index, fmt) in rules]


    def highlightBlock(self, text):
        for exp, nth, fmt in self.rules:
            matches = exp.globalMatch(text)
            while matches.hasNext():
                m = matches.next()
                self.setFormat(m.capturedStart(nth), m.capturedLength(nth), fmt)                
        self.setCurrentBlockState(0)