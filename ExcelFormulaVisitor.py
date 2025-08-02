# Generated from /home/ashutosh/PycharmProjects/local_llm/ExcelFormula.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .ExcelFormulaParser import ExcelFormulaParser
else:
    from ExcelFormulaParser import ExcelFormulaParser

# This class defines a complete generic visitor for a parse tree produced by ExcelFormulaParser.

class ExcelFormulaVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by ExcelFormulaParser#formula.
    def visitFormula(self, ctx:ExcelFormulaParser.FormulaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#expression.
    def visitExpression(self, ctx:ExcelFormulaParser.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#logicalExpr.
    def visitLogicalExpr(self, ctx:ExcelFormulaParser.LogicalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#compareExpr.
    def visitCompareExpr(self, ctx:ExcelFormulaParser.CompareExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#addExpr.
    def visitAddExpr(self, ctx:ExcelFormulaParser.AddExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#multExpr.
    def visitMultExpr(self, ctx:ExcelFormulaParser.MultExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#unaryExpr.
    def visitUnaryExpr(self, ctx:ExcelFormulaParser.UnaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#atom.
    def visitAtom(self, ctx:ExcelFormulaParser.AtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#functionCall.
    def visitFunctionCall(self, ctx:ExcelFormulaParser.FunctionCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#columnRef.
    def visitColumnRef(self, ctx:ExcelFormulaParser.ColumnRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ExcelFormulaParser#literal.
    def visitLiteral(self, ctx:ExcelFormulaParser.LiteralContext):
        return self.visitChildren(ctx)



del ExcelFormulaParser