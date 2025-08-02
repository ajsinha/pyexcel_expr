import antlr4
from antlr4 import *
from ExcelFormulaLexer import ExcelFormulaLexer
from ExcelFormulaParser import ExcelFormulaParser
from ExcelFormulaListener import ExcelFormulaListener
import polars as pl
import datetime
import warnings
import math
import numpy_financial as npf
from functools import reduce
import importlib


class FormulaToPolarsListener(ExcelFormulaListener):
    def __init__(self):
        self.stack = []
        self.function_map = {
            # Mathematical
            'SUM': 'sum',
            'AVERAGE': 'mean',
            'MIN': 'min',
            'MAX': 'max',
            'ABS': lambda args: f"abs({args[0]})",
            'ROUND': lambda args: f"{args[0]}.round( {args[1] if len(args) > 1 else 0})",
            #'ROUND': lambda args: f"round({args[0]}, {args[1] if len(args) > 1 else 0})",
            'CEILING': lambda args: f"ceil({args[0]})",
            'FLOOR': lambda args: f"floor({args[0]})",
            'MOD': lambda args: f"({args[0]} % {args[1]})",
            'POWER': lambda args: f"({args[0]} ** {args[1]})",
            'SQRT': lambda args: f"sqrt({args[0]})",
            'SUMPRODUCT': self._handle_sumproduct,
            # Statistical
            'MEDIAN': 'median',
            'STDEV': 'std',
            'VAR': 'var',
            # Logical
            'IF': self._handle_if,
            'IFERROR': self._handle_iferror,
            'AND': lambda args: f"({' & '.join(args)})",
            'OR': lambda args: f"({' | '.join(args)})",
            'NOT': lambda args: f"~({args[0]})",
            # Text
            'CONCAT': lambda args: f"pl.concat_str([{', '.join(self._mod_concat(args))}])",
            #'CONCAT': lambda args: f"pl.concat_str([{', '.join(args)}])",
            'LEFT': lambda args: f"({args[0]}).str.slice(0, {args[1]})",
            'RIGHT': lambda args: f"({args[0]}).str.slice(-{args[1]})",
            'MID': lambda args: f"({args[0]}).str.slice({args[1]}, {args[2]})",
            'LEN': lambda args: f"({args[0]}).str.len_chars()",
            'TRIM': lambda args: f"({args[0]}).str.strip_chars()",
            'UPPER': lambda args: f"({args[0]}).str.to_uppercase()",
            'LOWER': lambda args: f"({args[0]}).str.to_lowercase()",
            'SUBSTITUTE': lambda args: f"({args[0]}).str.replace({args[1]}, {args[2]})",
            # Date/Time
            'TODAY': lambda args: "pl.lit(datetime.datetime.now().date())",
            'NOW': lambda args: "pl.lit(datetime.datetime.now())",
            'YEAR': lambda args: f"({args[0]}).dt.year()",
            'MONTH': lambda args: f"({args[0]}).dt.month()",
            'DAY': lambda args: f"({args[0]}).dt.day()",
            'DATE': lambda args: f"pl.lit(datetime.date({args[0]}, {args[1]}, {args[2]}))",
            'DATEDIF': self._handle_datedif,
            # Database
            'COUNT': lambda args: f"({' + '.join(args)}).count()",
            'COUNTIF': self._handle_countif,
            'SUMIF': self._handle_sumif,
            # Lookup
            'VLOOKUP': self._handle_vlookup,
            'HLOOKUP': self._handle_hlookup,
            # Financial
            'FV': self._handle_fv,
            'PV': self._handle_pv,
            'NPV': self._handle_npv,
            'PMT': self._handle_pmt,
            'RATE': self._handle_rate,
            'IRR': self._handle_irr
        }

    def register_custom_function(self, func_name: str, handler=None, module_path: str = None):
        """Register a custom Excel-like function with a Polars handler or external Python function."""
        if module_path:
            try:
                module_name, func = module_path.rsplit('.', 1)
                module = importlib.import_module(module_name)
                handler = getattr(module, func)
                # Wrap external function to work with Polars Series
                polars_handler = lambda \
                    args: f"pl.struct({', '.join(f'arg{i}={arg}' for i, arg in enumerate(args))}).map_elements(lambda x: {module_path}({', '.join(f'x[\"arg{i}\"]' for i in range(len(args)))}), return_dtype=pl.Float64)"
                self.function_map[func_name.upper()] = polars_handler
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Failed to import function {module_path}: {str(e)}")
        elif handler:
            self.function_map[func_name.upper()] = handler
        else:
            raise ValueError("Either handler or module_path must be provided")

    def register_custom_function_old(self, func_name: str, handler):
        """Register a custom Excel-like function with a Polars or Python handler."""
        self.function_map[func_name.upper()] = handler

    def _mod_concat(self, args):
        mod_args = []
        for x in args:
            if x.startswith('pl.col('):
                mod_args.append(x)
            else:
                mod_args.append('pl.lit(' + str(x) + ')')
        return mod_args

    def _handle_if(self, args):
        condition, true_val, false_val = args
        return f"pl.when({condition}).then({true_val}).otherwise({false_val})"

    def _handle_iferror(self, args):
        value, value_if_error = args
        return f"pl.when({value}.is_not_null()).then({value}).otherwise({value_if_error})"

    def _handle_countif(self, args):
        range_expr, criteria = args
        return f"({range_expr}).filter({criteria}).count()"

    def _handle_sumif(self, args):
        range_expr, criteria, sum_range = args if len(args) == 3 else [args[0], args[1], args[0]]
        return f"({sum_range}).filter({criteria}).sum()"

    def _handle_vlookup(self, args):
        warnings.warn("VLOOKUP is approximated as a join in Polars; verify output.")
        lookup_value, table_range, col_index = args
        return f"pl.col('{lookup_value}').join({table_range}, on={lookup_value}, how='left').select(pl.col('{col_index}'))"

    def _handle_hlookup(self, args):
        warnings.warn("HLOOKUP is approximated as a join in Polars; verify output.")
        lookup_value, table_range, row_index = args
        return f"pl.col('{lookup_value}').join({table_range}, on={lookup_value}, how='left').select(pl.col('{row_index}'))"

    def _handle_datedif(self, args):
        start_date, end_date, unit = args
        unit = unit.strip("'").lower()
        # Ensure start_date is cast to Date if it's a string literal
        if start_date.startswith("'") and start_date.endswith("'"):
            start_date = f"pl.lit({start_date}).cast(pl.Date)"

        if end_date.startswith("'") and end_date.endswith("'"):
            end_date = f"pl.lit({end_date}).cast(pl.Date)"

        if unit == 'd':
            return f"(({end_date} - {start_date}).dt.total_days()).cast(pl.Int32, strict=False)"
        elif unit == 'm':
            return f"((({end_date} - {start_date}).dt.total_days() / 30.42).cast(pl.Int32, strict=False))"
        elif unit == 'y':
            return f"((({end_date} - {start_date}).dt.total_days() / 365.25).cast(pl.Int32, strict=False))"
        else:
            raise ValueError(f"Unsupported DATEDIF unit: {unit}")

    def _handle_sumproduct(self, args):
        if len(args) < 1:
            raise ValueError("SUMPRODUCT requires at least one argument")
        product_expr = reduce(lambda x, y: f"({x} * {y})", args)
        return f"({product_expr}).sum()"

    def _handle_datedif_ash(self, args):

        from datetime import datetime
        def clean_date_arg(date_string):
            if not date_string.startswith('pl.col('):
                return f'pl.lit({date_string}).str.strptime(pl.Datetime, format="%Y-%m-%d")'
            return date_string

        start_date, end_date, unit = args

        start_date = clean_date_arg(start_date)
        end_date = clean_date_arg(end_date)

        unit = unit.strip("'").lower()
        if unit == 'd':
            return f"(({end_date} - {start_date}).dt.total_days())"
        elif unit == 'm':
            return f"((({end_date} - {start_date}).dt.total_days() / 30.42).cast(pl.Int32))"
        elif unit == 'y':
            return f"((({end_date} - {start_date}).dt.total_days() / 365.25).cast(pl.Int32))"
        else:
            raise ValueError(f"Unsupported DATEDIF unit: {unit}")



    def _handle_fv(self, args):
        rate, nper, pmt, pv = args + ['0'] * (4 - len(args))
        return f"pl.struct(rate={rate}, nper={nper}, pmt={pmt}, pv={pv}).map_elements(lambda x: npf.fv(x['rate'], x['nper'], x['pmt'], x['pv']), return_dtype=pl.Float64)"

    def _handle_pv(self, args):
        rate, nper, pmt, fv = args + ['0'] * (4 - len(args))
        return f"pl.struct(rate={rate}, nper={nper}, pmt={pmt}, fv={fv}).map_elements(lambda x: npf.pv(x['rate'], x['nper'], x['pmt'], x['fv']), return_dtype=pl.Float64)"

    def _handle_npv(self, args):
        rate, *values = args
        values_expr = f"pl.concat_list([{', '.join(values)}])"
        return f"pl.struct(rate={rate}, values={values_expr}).map_elements(lambda x: npf.npv(x['rate'], x['values']), return_dtype=pl.Float64)"

    def _handle_pmt(self, args):
        rate, nper, pv, fv = args + ['0'] * (4 - len(args))
        return f"pl.struct(rate={rate}, nper={nper}, pv={pv}, fv={fv}).map_elements(lambda x: npf.pmt(float(x['rate']), float(x['nper']), float(x['pv']), float(x['fv'])), return_dtype=pl.Float64)"

    def _handle_rate(self, args):
        nper, pmt, pv, fv = args + ['0'] * (4 - len(args))
        return f"pl.struct(nper={nper}, pmt={pmt}, pv={pv}, fv={fv}).map_elements(lambda x: npf.rate(float(x['nper']), float(x['pmt']), float(x['pv']), float(x['fv'])), return_dtype=pl.Float64)"

    def _handle_irr(self, args):
        values = args
        values_expr = f"pl.concat_list([{', '.join(values)}])"
        return f"{values_expr}.map_elements(lambda x: npf.irr(x) if x is not None and len(x) > 1 and any(v != 0 for v in x) else float('nan'), return_dtype=pl.Float64)"

    def exitFormula(self, ctx):
        pass

    def exitLiteral(self, ctx):
        if ctx.NUMBER():
            self.stack.append(ctx.NUMBER().getText())
        elif ctx.STRING():
            text = ctx.STRING().getText()
            self.stack.append(f"'{text[1:-1]}'")
        elif ctx.BOOLEAN():
            self.stack.append(ctx.BOOLEAN().getText().capitalize())
        elif ctx.DATE():
            self.stack.append(f"pl.lit('{ctx.DATE().getText()}').cast(pl.Date)")

    def exitColumnRef(self, ctx):
        col_name = ctx.IDENTIFIER().getText()
        self.stack.append(f'pl.col("{col_name}")')

    def exitUnaryExpr(self, ctx):
        if ctx.getChild(0).getText() == '-':
            expr = self.stack.pop()
            self.stack.append(f"-{expr}")

    def exitLogicalExpr(self, ctx):
        if ctx.getChildCount() == 3:
            right = self.stack.pop()
            left = self.stack.pop()
            op = ctx.getChild(1).getText()
            op_map = {'&&': '&', '||': '|'}
            self.stack.append(f"({left} {op_map[op]} {right})")

    def exitCompareExpr(self, ctx):
        if ctx.getChildCount() == 3:
            right = self.stack.pop()
            left = self.stack.pop()
            op = ctx.getChild(1).getText()
            op_map = {'=': '==', '<>': '!='}
            polars_op = op_map.get(op, op)
            self.stack.append(f"({left} {polars_op} {right})")

    def exitAddExpr(self, ctx):
        if ctx.getChildCount() == 3:
            right = self.stack.pop()
            left = self.stack.pop()
            op = ctx.getChild(1).getText()
            self.stack.append(f"({left} {op} {right})")

    def exitMultExpr(self, ctx):
        if ctx.getChildCount() == 3:
            right = self.stack.pop()
            left = self.stack.pop()
            op = ctx.getChild(1).getText()
            polars_op = '**' if op == '^' else op
            self.stack.append(f"({left} {polars_op} {right})")

    def exitFunctionCall(self, ctx):
        func_name = ctx.IDENTIFIER().getText().upper()
        arg_count = len(ctx.expression()) if ctx.expression() else 0
        args = [self.stack.pop() for _ in range(arg_count)][::-1]

        if func_name in self.function_map.keys():
            if callable(self.function_map[func_name]):
                fmp= self.function_map[func_name]
                result = fmp(args)
            else:
                result = f"({' + '.join(args)}).{self.function_map[func_name]}()"
            self.stack.append(result)
        else:
            warnings.warn(f"Function {func_name} not supported in Polars; returning raw expression.")
            self.stack.append(f"{func_name}({', '.join(args)})")

    def convert_to_polars(self, formula: str) -> str:
        input_stream = InputStream(formula)
        lexer = ExcelFormulaLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = ExcelFormulaParser(stream)
        tree = parser.formula()

        listener = FormulaToPolarsListener()
        listener.function_map = self.function_map.copy()

        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        return listener.stack[0]

    def apply_formula(self, df: pl.DataFrame, formula: str, new_column: str) -> pl.DataFrame:
        import custom_functions
        polars_expr = self.convert_to_polars(formula)
        print(f'excel: {formula}, polars: {polars_expr}')
        eval_globals = {'pl': pl, 'math': math, 'datetime': datetime, 'npf': npf, 'reduce': reduce}
        try:
            # Attempt to import custom_functions, but don't fail if it doesn't exist
            custom_functions = importlib.import_module('custom_functions')
            eval_globals['custom_functions'] = custom_functions
        except ImportError:
            pass  # If custom_functions.py doesn't exist, external functions will fail at registration

        try:
            return df.with_columns(
                **{new_column: eval(polars_expr, eval_globals)})
        except Exception as e:
            raise ValueError(f"Error applying formula {formula}: {str(e)}")




def convert_to_polars(formula: str) -> str:
    input_stream = InputStream(formula)
    lexer = ExcelFormulaLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = ExcelFormulaParser(stream)
    tree = parser.formula()

    listener = FormulaToPolarsListener()
    walker = ParseTreeWalker()
    walker.walk(listener, tree)

    return listener.stack[0]


def create_sample_dataframe():
    return pl.DataFrame({
        "Price": [100.0, 150.0, -50.0, 200.0],
        "Tax": [10.0, 15.0, 5.0, 20.0],
        "Quantity": [5, 12, 8, 15],
        "Name": ["John", "Alice", "Bob", "Eve"],
        "Surname": ["Doe", "Smith", "Jones", "Brown"],
        "Date": [datetime.date(2025, 1, 1), datetime.date(2025, 2, 1),
                 datetime.date(2025, 3, 1), datetime.date(2025, 4, 1)],
        "Category": ["A", "B", "A", "C"],
        "Description": ["Item 1 desc", "Item 2 desc", "Item 3 desc", "Item 4 desc"],
        "Rate": [0.05, 0.06, 0.04, 0.05],
        "Periods": [10, 5, 8, 12],
        "Payment": [-100, -150, -50, -200],
        "CashFlows": [[-1000, 300, 400, 500], [-2000, 600, 700, 800], [-500, 200, 300, 400], [-3000, 900, 1000, 1100]]
    })

'''
def apply_formula(df: pl.DataFrame, formula: str, new_column: str, listener: FormulaToPolarsListener = None) -> pl.DataFrame:
    polars_expr = convert_to_polars(formula, listener)
    try:
        return df.with_columns(**{new_column: eval(polars_expr, {'pl': pl, 'math': math, 'datetime': datetime, 'npf': npf})})
    except Exception as e:
        raise ValueError(f"Error applying formula {formula}: {str(e)}")
'''
def apply_formula(df: pl.DataFrame, formula: str, new_column: str, listener: FormulaToPolarsListener = None) -> pl.DataFrame:
    polars_expr = convert_to_polars(formula, listener)
    eval_globals = {'pl': pl, 'math': math, 'datetime': datetime, 'npf': npf, 'reduce': reduce}
    try:
        # Attempt to import custom_functions, but don't fail if it doesn't exist
        custom_functions = importlib.import_module('custom_functions')
        eval_globals['custom_functions'] = custom_functions
    except ImportError:
        pass  # If custom_functions.py doesn't exist, external functions will fail at registration
    try:
        return df.with_columns(**{new_column: eval(polars_expr, eval_globals)})
    except Exception as e:
        raise ValueError(f"Error applying formula {formula}: {str(e)}")

# Test suite
def run_tests():
    df = create_sample_dataframe()
    listener = FormulaToPolarsListener()

    # Register a custom function with return_dtype
    listener.register_custom_function(
        'CUSTOM_DISCOUNT',
        lambda args: f"({args[0]} * (1 - {args[1]} / 100)).cast(pl.Float64)"
    )

    # Register an external function
    listener.register_custom_function(
        'WEIGHTED_AVERAGE',
        module_path='custom_functions.weighted_average'
    )

    test_cases = [
        # Basic
        {
            "formula": "=Price + Tax",
            "new_column": "Total",
            "expected_values": [110.0, 165.0, -45.0, 220.0]
        },
        # Logical
        {
            "formula": "=IF(Quantity > 10, Price * 0.9, Price)",
            "new_column": "DiscountedPrice",
            "expected_values": [100.0, 135.0, -50.0, 180.0]
        },
        # Text
        {
            "formula": "=CONCAT(Name, \" \", Surname)",
            "new_column": "FullName",
            "expected_values": ["John Doe", "Alice Smith", "Bob Jones", "Eve Brown"]
        },
        {
            "formula": "=TRIM(Name)",
            "new_column": "TrimmedName",
            "expected_values": ["John", "Alice", "Bob", "Eve"]
        },
        # Mathematical
        {
            "formula": "=ABS(Price)",
            "new_column": "AbsPrice",
            "expected_values": [100.0, 150.0, 50.0, 200.0]
        },
        {
            "formula": "=ROUND(Price / Tax, 2)",
            "new_column": "PriceTaxRatio",
            "expected_values": [10.0, 10.0, -10.0, 10.0]
        },
        {
            "formula": "=POWER(Price, 2)",
            "new_column": "PriceSquared",
            "expected_values": [10000.0, 22500.0, 2500.0, 40000.0]
        },
        # Date
        {
            "formula": "=DATEDIF(\"2025-01-01\", Date, \"d\")",
            "new_column": "DaysSinceStart",
            "expected_values": [0, 31, 59, 90]
        },
        {
            "formula": "=YEAR(Date)",
            "new_column": "Year",
            "expected_values": [2025, 2025, 2025, 2025]
        },
        # Financial
        {
            "formula": "=FV(Rate, Periods, Payment, Price)",
            "new_column": "FutureValue",
            "expected_values": [
                npf.fv(0.05, 10, -100, 100),
                npf.fv(0.06, 5, -150, 150),
                npf.fv(0.04, 8, -50, -50),
                npf.fv(0.05, 12, -200, 200)
            ]
        },
        {
            "formula": "=PV(Rate, Periods, Payment, Price)",
            "new_column": "PresentValue",
            "expected_values": [
                npf.pv(0.05, 10, -100, 100),
                npf.pv(0.06, 5, -150, 150),
                npf.pv(0.04, 8, -50, -50),
                npf.pv(0.05, 12, -200, 200)
            ]
        },
        {
            "formula": "=NPV(Rate, CashFlows)",
            "new_column": "NetPresentValue",
            "expected_values": [
                npf.npv(0.05, [-1000, 300, 400, 500]),
                npf.npv(0.06, [-2000, 600, 700, 800]),
                npf.npv(0.04, [-500, 200, 300, 400]),
                npf.npv(0.05, [-3000, 900, 1000, 1100])
            ]
        },
        {
            "formula": "=PMT(Rate, Periods, Price)",
            "new_column": "PaymentAmount",
            "expected_values": [
                npf.pmt(0.05, 10, 100),
                npf.pmt(0.06, 5, 150),
                npf.pmt(0.04, 8, -50),
                npf.pmt(0.05, 12, 200)
            ]
        },
        {
            "formula": "=RATE(Periods, Payment, Price)",
            "new_column": "InterestRate",
            "expected_values": [
                npf.rate(10, -100, 100, 0),
                npf.rate(5, -150, 150, 0),
                npf.rate(8, -50, -50, 0),
                npf.rate(12, -200, 200, 0)
            ]
        },
        {
            "formula": "=IRR(CashFlows)",
            "new_column": "InternalRate",
            "expected_values": [
                npf.irr([-1000, 300, 400, 500]),
                npf.irr([-2000, 600, 700, 800]),
                npf.irr([-500, 200, 300, 400]),
                npf.irr([-3000, 900, 1000, 1100])
            ]
        },
        # Custom
        {
            "formula": "=CUSTOM_DISCOUNT(Price, 10)",
            "new_column": "CustomDiscount",
            "expected_values": [90.0, 135.0, -45.0, 180.0]
        },
        # SUMPRODUCT
        {
            "formula": "=SUMPRODUCT(Price, Quantity)",
            "new_column": "TotalValue",
            "expected_values": [100.0 * 5 + 150.0 * 12 + (-50.0) * 8 + 200.0 * 15]
        },
        # External function
        {
            "formula": "=WEIGHTED_AVERAGE(Price, Quantity)",
            "new_column": "WeightedAvg",
            "expected_values": [(100.0 * 5 + 150.0 * 12 + (-50.0) * 8 + 200.0 * 15) / (5 + 12 + 8 + 15)]
        }
    ]

    for test in test_cases:
        formula = test["formula"]
        new_column = test["new_column"]
        expected_values = test["expected_values"]
        try:
            result_df = listener.apply_formula(df, formula, new_column)
            actual_values = result_df[new_column].to_list()
            # Handle float comparisons with tolerance
            if isinstance(expected_values[0], float):
                assert all(abs(a - b) < 1e-6 for a, b in zip(actual_values, expected_values)), \
                    f"Failed: {formula}\nExpected: {expected_values}\nGot: {actual_values}"
            else:
                assert actual_values == expected_values, \
                    f"Failed: {formula}\nExpected: {expected_values}\nGot: {actual_values}"
            print(f"Passed: {formula} -> Added column '{new_column}' with values {actual_values}")
        except Exception as e:
            print(f"Error: {formula} -> {str(e)}")


if __name__ == "__main__":
    run_tests()