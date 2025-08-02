
import polars as pl

def validate_email(df: pl.DataFrame, column: str) -> pl.Series:
    return df[column].str.contains(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def weighted_average(values, weights):
    """Compute weighted average of values with given weights."""
    import polars as pl
    return (values * weights).sum() / weights.sum()
