# This file is to repair the executed csv file pd_split_gd.csv
# With pd_gd_python_revise.csv
# The goal is to replacing column with updated one 
# -> data input for pd_gd_pred_unit.py
import pandas as pd

# Read the first CSV file
df1 = pd.read_csv('data_output/pd_split_gd.csv')

# Read the second CSV file
df2 = pd.read_csv('data_output/pd_gd_python_revise.csv')

# Merge the two DataFrames on the 'id' column
merged_df = pd.merge(df1, df2, on='id')

# Replace the values in 'size 1', 'size 2', 'size 3' with 'width', 'height', 'optional' from the second DataFrame
merged_df['size 1'] = merged_df['width']
merged_df['size 2'] = merged_df['height']
merged_df['size 3'] = merged_df['optional']

# Drop the additional columns from the second DataFrame to keep the original structure
final_df = merged_df[["id","physical_description","unit_capture",
                       "size","width","height","optional"]]

# Save the updated DataFrame to a new CSV file
final_df.to_csv('data_output/pd_gd_updated.csv', index=False)

# Print the final DataFrame for verification
print(final_df)
