# Input: dataframe llamado "df"
# Output: dataframe corregido

import pandas as pd

def clean_numeric_fields(df):
    for col in df.columns:
        # Solo procesamos columnas tipo texto
        if df[col].dtype == 'object':
            try:
                # Intentamos convertir a número
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                pass
    return df

def get_output_schema(df):
    return df


