# Generated from /home/ashutosh/PycharmProjects/local_llm/ExcelFormula.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .ExcelFormulaParser import ExcelFormulaParser
else:
    from ExcelFormulaParser import ExcelFormulaParser

# This class defines a complete listener for a parse tree produced by ExcelFormulaParser.
class ExcelFormulaListener(ParseTreeListener):

    # Enter a parse tree produced by ExcelFormulaParser#formula.
    def enterFormula(self, ctx:ExcelFormulaParser.FormulaContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#formula.
    def exitFormula(self, ctx:ExcelFormulaParser.FormulaContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#expression.
    def enterExpression(self, ctx:ExcelFormulaParser.ExpressionContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#expression.
    def exitExpression(self, ctx:ExcelFormulaParser.ExpressionContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#logicalExpr.
    def enterLogicalExpr(self, ctx:ExcelFormulaParser.LogicalExprContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#logicalExpr.
    def exitLogicalExpr(self, ctx:ExcelFormulaParser.LogicalExprContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#compareExpr.
    def enterCompareExpr(self, ctx:ExcelFormulaParser.CompareExprContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#compareExpr.
    def exitCompareExpr(self, ctx:ExcelFormulaParser.CompareExprContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#addExpr.
    def enterAddExpr(self, ctx:ExcelFormulaParser.AddExprContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#addExpr.
    def exitAddExpr(self, ctx:ExcelFormulaParser.AddExprContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#multExpr.
    def enterMultExpr(self, ctx:ExcelFormulaParser.MultExprContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#multExpr.
    def exitMultExpr(self, ctx:ExcelFormulaParser.MultExprContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#unaryExpr.
    def enterUnaryExpr(self, ctx:ExcelFormulaParser.UnaryExprContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#unaryExpr.
    def exitUnaryExpr(self, ctx:ExcelFormulaParser.UnaryExprContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#atom.
    def enterAtom(self, ctx:ExcelFormulaParser.AtomContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#atom.
    def exitAtom(self, ctx:ExcelFormulaParser.AtomContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#functionCall.
    def enterFunctionCall(self, ctx:ExcelFormulaParser.FunctionCallContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#functionCall.
    def exitFunctionCall(self, ctx:ExcelFormulaParser.FunctionCallContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#columnRef.
    def enterColumnRef(self, ctx:ExcelFormulaParser.ColumnRefContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#columnRef.
    def exitColumnRef(self, ctx:ExcelFormulaParser.ColumnRefContext):
        pass


    # Enter a parse tree produced by ExcelFormulaParser#literal.
    def enterLiteral(self, ctx:ExcelFormulaParser.LiteralContext):
        pass

    # Exit a parse tree produced by ExcelFormulaParser#literal.
    def exitLiteral(self, ctx:ExcelFormulaParser.LiteralContext):
        pass



del ExcelFormulaParser