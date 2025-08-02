import polars as pl


def run_dq_check(df: pl.DataFrame, rules: list[str], evaluate_dq_rule) -> list[dict]:
    """
    Runs data quality checks on the given DataFrame using the provided rules.

    Args:
        df (pl.DataFrame): The DataFrame to check.
        rules (list[str]): List of DQ rules as strings.
        evaluate_dq_rule (callable): A function that takes df and a rule string and returns a boolean Series indicating where the rule passes.

    Returns:
        list[dict]: A list of dictionaries, each containing a failed rule and the corresponding row data.
    """
    failures = []
    for rule in rules:
        try:
            # Evaluate the rule on the DataFrame
            passed = evaluate_dq_rule(df, rule)
            # Filter rows where the rule fails
            failed_rows = df.filter(~passed)
            # For each failed row, add to the failures list
            for row_dict in failed_rows.to_dicts():
                failures.append({
                    "rule": rule,
                    "row": row_dict
                })
        except Exception as e:
            # Handle errors in rule evaluation
            print(f"Error evaluating rule '{rule}': {e}")
    return failures

# Example DataFrame
df = pl.DataFrame({
    "columnA": [1, 2, 3, 4, 5],
    "columnB": ["a", "b", "c", "d", "e"]
})

# Example rules
rules = ["columnA > 3", "columnB == 'c'"]

# Example evaluate_dq_rule function (for demonstration)
def evaluate_dq_rule(df, rule):
    # Simple parser for basic expressions
    parts = rule.split()
    if len(parts) != 3:
        raise ValueError("Invalid rule format")
    col, op, val = parts
    try:
        val = int(val)  # Try converting to integer
    except ValueError:
        val = val  # Keep as string if not numeric
    if op == ">":
        return df.select(pl.col(col) > val).to_series()
    elif op == "==":
        return df.select(pl.col(col) == val).to_series()
    else:
        raise ValueError("Unsupported operator")

# Run DQ check
failures = run_dq_check(df, rules, evaluate_dq_rule)

# Print the report
for failure in failures:
    print(f"Rule '{failure['rule']}' failed for row: {failure['row']}")