import pandas as pd

#read the pickle file to process the pandas dataframe
df = pd.read_pickle("contracts_clean.pkl")
print(df.columns)
