from pyparsing import infixNotation, opAssoc, Keyword, Word, alphanums

# define classes to be built at parse time, as each matching
# expression type is parsed
class BbqlBoolOperand:
    def __init__(self, t):
        self.field = t[0].lower().replace(' ', '_')
        self.pattern = t[2]
        self.label = self.field + ':' + self.pattern

    def filterFields(self):
        return set([self.field])

    def evaluateFilter(self, rowData):
        return self.pattern in rowData[self.field]

    def __str__(self):
        return self.label

    __repr__ = __str__


class BoolBinOp:
    def __init__(self, t):
        self.args = t[0][0::2]

    def filterFields(self):
        ret = set()
        for child in self.args:
            ret.update(child.filterFields())
        return ret

    def evaluateFilter(self, rowData):
        return self.evalop(child.evaluateFilter(rowData) for child in self.args)

    def __str__(self):
        sep = " %s " % self.reprsymbol
        return "(" + sep.join(map(str, self.args)) + ")"


class BoolAnd(BoolBinOp):
    reprsymbol = "&"
    evalop = all


class BoolOr(BoolBinOp):
    reprsymbol = "|"
    evalop = any


class BoolNot:
    def __init__(self, t):
        self.arg = t[0][1]

    def filterFields(self):
        return self.arg.filterFields()

    def evaluateFilter(self, rowData):
        v = self.arg.evaluateFilter(rowData)
        return not v

    def __str__(self):
        return "~" + str(self.arg)

    __repr__ = __str__


bbqlColumnName = Word(alphanums+"_")
bbqlFilterPattern = Word(alphanums+"_"+"."+"-")
bbqlColumnFilter = bbqlColumnName+":"+bbqlFilterPattern
bbqlBoolOperand = bbqlColumnFilter
bbqlBoolOperand.setParseAction(BbqlBoolOperand)


bbqlExpression = infixNotation(
    bbqlBoolOperand,
    [
        ("not", 1, opAssoc.RIGHT, BoolNot),
        ("and", 2, opAssoc.LEFT, BoolAnd),
        ("or", 2, opAssoc.LEFT, BoolOr),
    ],
)

  #      res = boolExpr.parseString(t)[0]
  #      result = res.evaluateFilter(rowData1)
