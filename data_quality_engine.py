import polars as pl
import pandas as pd
import re
from typing import Dict, Any, Callable, List
import logging
from datetime import datetime, date
import importlib.util
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataQualityEngine:
    def __init__(self, rules_file: str):
        """Initialize the data quality engine with rules from an Excel file."""
        self.rules = self._load_rules(rules_file)
        self.custom_functions: Dict[str, Callable] = {}
        self.results: List[Dict[str, Any]] = []

    def _load_rules(self, rules_file: str) -> pl.DataFrame:
        """Load data quality rules from an Excel file."""
        try:
            rules_df = pl.read_excel(rules_file)
            required_columns = ['rule_id', 'column', 'rule_type', 'rule_expression', 'error_message']
            if not all(col in rules_df.columns for col in required_columns):
                raise ValueError(f"Rules file must contain columns: {required_columns}")
            return rules_df
        except Exception as e:
            logger.error(f"Failed to load rules file: {str(e)}")
            raise

    def load_custom_functions(self, module_path: str):
        """Load custom Python functions from a specified module."""
        try:
            spec = importlib.util.spec_from_file_location("custom_functions", module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["custom_functions"] = module
            spec.loader.exec_module(module)

            for func_name in dir(module):
                func = getattr(module, func_name)
                if callable(func) and not func_name.startswith('_'):
                    self.custom_functions[func_name] = func
                    logger.info(f"Loaded custom function: {func_name}")
        except Exception as e:
            logger.error(f"Failed to load custom functions: {str(e)}")
            raise

    def _parse_excel_expression(self, expression: str, column: str) -> str:
        """Convert Excel-style expression to Polars expression, handling nested IFs, string, numeric, date operations, and IN statements."""

        # Replace column references with Polars syntax
        def replace_column_refs(match):
            col_name = match.group(1)
            return f'pl.col("{col_name}")'

        expression = re.sub(r'\[([^\]]*)\]', replace_column_refs, expression)

        # Convert Excel functions to Polars
        excel_to_polars = {
            r'\bAND\b': ' & ',
            r'\bOR\b': ' | ',
            r'\bNOT\b': '~',
            r'\bISBLANK\b': 'is_null',
            r'\bLEN\b': 'str.len_bytes',
            r'\bIF\b': 'when',
            r'\bTODAY\b': f'pl.lit(date({date.today().year},{date.today().month},{date.today().day}))',
            r'\bDATEDIF\b': 'date_diff',
            r'\bSUM\b': 'sum',
            r'\bCOUNT\b': 'count',
            r'\bAVG\b': 'mean',
            r'\bLEFT\b': 'str.slice(0, ',
            r'\bRIGHT\b': 'str.slice(-',
            r'\bCONCAT\b': 'str.concat',
            r'\bROUND\b': 'round',
            r'\bABS\b': 'abs',
            r'\bYEAR\b': 'dt.year',
            r'\bMONTH\b': 'dt.month',
            r'\bDAY\b': 'dt.day',
            r'\bUPPER\b': 'str.to_uppercase',
            r'\bLOWER\b': 'str.to_lowercase'
        }

        for excel_func, polars_func in excel_to_polars.items():
            expression = re.sub(excel_func, polars_func, expression, flags=re.IGNORECASE)

        # Handle IN statements
        expression = re.sub(
            r'IN\(([^)]+)\)',
            lambda m: f'is_in([{m.group(1)}])',
            expression,
            flags=re.IGNORECASE
        )

        # Handle nested IF statements
        def parse_nested_if(expr: str) -> str:
            pattern = r'when\(([^()]+|\([^()]*\)),\s*([^,]+),\s*([^)]+)\)'
            while re.search(pattern, expr, re.IGNORECASE):
                expr = re.sub(
                    pattern,
                    r'pl.when(\1).then(\2).otherwise(\3)',
                    expr,
                    flags=re.IGNORECASE
                )
            return expr

        expression = parse_nested_if(expression)

        # Handle DATEDIF
        expression = re.sub(
            r'date_diff\(([^,]+),\s*([^,]+),\s*"([^"]+)"\)',
            r'(\1 - \2).dt.\3()',
            expression,
            flags=re.IGNORECASE
        )

        # Handle string operations
        expression = re.sub(
            r'str\.slice\(([^,]+),\s*(\d+)\)',
            r'\1.str.slice(\1, \2)',
            expression
        )

        # Handle aggregate functions
        aggregate_functions = ['sum', 'count', 'mean']
        for agg_func in aggregate_functions:
            expression = re.sub(
                rf'{agg_func}\((pl\.col\("[^"]+"\))\)',
                rf'\1.{agg_func}()',
                expression,
                flags=re.IGNORECASE
            )

        return expression

    def _apply_rule(self, df: pl.DataFrame, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single rule to the dataframe."""
        try:
            rule_id = rule['rule_id']
            column = rule['column']
            rule_type = rule['rule_type'].lower()
            expression = rule['rule_expression']
            error_message = rule['error_message']

            if rule_type == 'excel':
                polars_expr = self._parse_excel_expression(expression, column)
                referenced_columns = re.findall(r'pl\.col\("([^"]+)"\)', polars_expr)
                missing_cols = [col for col in referenced_columns if col not in df.columns]
                if missing_cols:
                    raise ValueError(f"Columns {missing_cols} not found in dataframe")

                aggregate_functions = ['sum', 'count', 'mean']
                is_aggregate = any(func in polars_expr.lower() for func in aggregate_functions)

                if is_aggregate:
                    group_cols = [col for col in df.columns if col not in referenced_columns and col != 'row_id']
                    if group_cols:
                        result = df.group_by(group_cols).agg(pl.col('*')).filter(~eval(polars_expr, {'pl': pl}))
                    else:
                        result = df.filter(~eval(polars_expr, {'pl': pl}))
                else:
                    result = df.filter(~eval(polars_expr, {'pl': pl}))

            elif rule_type == 'python':
                if expression not in self.custom_functions:
                    raise ValueError(f"Custom function {expression} not found")
                result = df.filter(~self.custom_functions[expression](df, column))

            elif rule_type == 'regex':
                try:
                    result = df.filter(~df[column].str.contains(expression))
                except Exception as e:
                    raise ValueError(f"Invalid regex pattern: {str(e)}")

            elif rule_type == 'format':
                try:
                    if expression.startswith('date:'):
                        date_format = expression.split(':', 1)[1]
                        result = df.filter(~df[column].cast(pl.Utf8).str.strptime(pl.Date, date_format).is_not_null())
                    elif expression.startswith('number:'):
                        num_format = expression.split(':', 1)[1]
                        if num_format == 'integer':
                            result = df.filter(~df[column].cast(pl.Int64, strict=False).is_not_null())
                        elif num_format.startswith('decimal:'):
                            decimals = int(num_format.split(':')[1])
                            result = df.filter(
                                ~df[column].cast(pl.Float64, strict=False)
                                .map_elements(lambda x: abs(x - round(x, decimals)) < 1e-10, return_dtype=pl.Boolean)
                            )
                        else:
                            raise ValueError(f"Unsupported number format: {num_format}")
                    elif expression.startswith('string:'):
                        str_format = expression.split(':', 1)[1]
                        result = df.filter(~df[column].cast(pl.Utf8).str.contains(str_format))
                    else:
                        raise ValueError(f"Invalid format specification: {expression}")
                except Exception as e:
                    raise ValueError(f"Format validation failed: {str(e)}")
            else:
                raise ValueError(f"Unsupported rule type: {rule_type}")

            failed_count = result.height
            referenced_columns = re.findall(r'\[([^\]]*)\]', rule['rule_expression']) if rule_type in ['excel', 'regex',
                                                                                                       'format'] else [
                column]
            failed_records = result.select(['row_id'] + [col for col in referenced_columns if col in df.columns])

            return {
                'rule_id': rule_id,
                'column': column,
                'failed_count': failed_count,
                'error_message': error_message,
                'failed_records': failed_records,
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"Error applying rule {rule_id}: {str(e)}")
            return {
                'rule_id': rule_id,
                'column': column,
                'failed_count': -1,
                'error_message': f"Rule execution failed: {str(e)}",
                'failed_records': pl.DataFrame(),
                'timestamp': datetime.now()
            }

    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Validate the dataframe against all rules and return results."""
        if 'row_id' not in df.columns:
            df = df.with_row_count('row_id')

        self.results = []
        for rule in self.rules.to_dicts():
            result = self._apply_rule(df, rule)
            self.results.append(result)

        summary = pl.DataFrame({
            'rule_id': [r['rule_id'] for r in self.results],
            'column': [r['column'] for r in self.results],
            'failed_count': [r['failed_count'] for r in self.results],
            'error_message': [r['error_message'] for r in self.results],
            'timestamp': [r['timestamp'] for r in self.results]
        })

        return summary

    def save_results(self, output_path: str):
        """Save validation results to an Excel file."""
        try:
            with pl.Config(tbl_rows=-1):
                summary = self.validate_results()
                summary.write_excel(output_path, worksheet='Summary')

                for result in self.results:
                    if result['failed_records'].height > 0:
                        result['failed_records'].write_excel(
                            output_path,
                            worksheet=f"Rule_{result['rule_id']}"
                        )
            logger.info(f"Results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")
            raise

    def validate_results(self) -> pl.DataFrame:
        """Return validation results as a DataFrame."""
        return pl.DataFrame({
            'rule_id': [r['rule_id'] for r in self.results],
            'column': [r['column'] for r in self.results],
            'failed_count': [r['failed_count'] for r in self.results],
            'error_message': [r['error_message'] for r in self.results],
            'timestamp': [r['timestamp'] for r in self.results]
        })


# Test script
if __name__ == "__main__":
    # Create sample rules file with IN statement and other operations
    rules_data = pl.DataFrame({
        'rule_id': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
        'column': ['name', 'age', 'email', 'salary', 'department', 'name', 'join_date', 'salary', 'code', 'department'],
        'rule_type': ['excel', 'excel', 'python', 'excel', 'excel', 'regex', 'format', 'format', 'format', 'excel'],
        'rule_expression': [
            'IF(UPPER([name]) = [name], TRUE, FALSE)',
            'IF(ROUND(ABS([age]) / [salary], 2) < 0.001, TRUE, FALSE)',
            'validate_email',
            'IF(SUM([salary]) > 100000, IF(AVG([salary]) > 50000, TRUE, FALSE), FALSE)',
            'IF(AND([department]="IT", OR(LOWER(CONCAT([name],"_it")) = "john_it", [salary] > 60000)), TRUE, FALSE)',
            '^[A-Z][a-z]+$',
            'date:%Y-%m-%d',
            'number:decimal:2',
            'string:^[A-Z]{3}\d{3}$',
            'IF([department] IN ("IT", "HR", "Finance"), TRUE, FALSE)'
        ],
        'error_message': [
            'Name must be uppercase',
            'Age to salary ratio invalid',
            'Invalid email format',
            'Salary aggregate requirements not met',
            'Department and name/salary requirements not met',
            'Name must start with capital letter followed by lowercase',
            'Join date must be in YYYY-MM-DD format',
            'Salary must have exactly 2 decimal places',
            'Code must be 3 letters followed by 3 digits',
            'Department must be IT, HR, or Finance'
        ]
    })
    rules_data.write_excel('rules.xlsx')

    # Create sample custom functions file
    with open('custom_functions.py', 'w') as f:
        f.write("""
import polars as pl

def validate_email(df: pl.DataFrame, column: str) -> pl.Series:
    return df[column].str.contains(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
""")

    # Sample data
    data = pl.DataFrame({
        'name': ['JOHN', 'Jane', 'bob', 'BOBBY', 'Alice'],
        'age': [25, 30, 35, 22, 28],
        'email': ['john@example.com', 'jane@example.com', 'invalid', 'bob@', 'alice@example.com'],
        'salary': [50000.00, 60000.50, 55000.123, 45000.00, 65000.00],
        'join_date': [
            '2023-01-15', '2024-06-20', '2022/03/10', '2024-01-01', '2023-07-01'
        ],
        'department': ['IT', 'HR', 'IT', 'Finance', 'Marketing'],
        'code': ['ABC123', 'DEF456', 'GH789', 'IJK123', 'LMN456']
    }).with_columns(pl.col('join_date').cast(pl.Utf8))

    # Create engine and load rules
    engine = DataQualityEngine('rules.xlsx')

    # Load custom functions
    engine.load_custom_functions('custom_functions.py')

    # Validate data
    results = engine.validate(data)

    # Save results
    engine.save_results('validation_results.xlsx')

    # Print results
    print("\nValidation Results:")
    print(results)