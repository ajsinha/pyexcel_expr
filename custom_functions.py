
import polars as pl

def validate_email(df: pl.DataFrame, column: str) -> pl.Series:
    return df[column].str.contains(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
