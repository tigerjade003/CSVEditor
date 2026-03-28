import pandas as pd

def get_data(path = None):
    if path is None:
        raise ValueError("Path must be provided.")
    if not path.endswith('.csv'):
        raise ValueError("File must be a CSV file.")
    data = pd.read_csv(path)
    return data

def write_data(data = None, path = None):
    if data is None:
        raise ValueError("Data must be provided.")
    if not isinstance(data, pd.DataFrame):
        raise ValueError("Data must be a pandas DataFrame.")
    if path is None:
        raise ValueError("Path must be provided.")
    data.to_csv(path, index=False)
