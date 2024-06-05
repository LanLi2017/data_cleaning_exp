# To complete these objectives, I'll be using a combination of 
# data manipulation, string processing, and predictive modeling techniques. 
# Let me know if you have any specific requirements or constraints that might impact the approach!
# Here's a Python script using pandas and regular expressions to 
# extract size information from the `physical_description` column in the `menu.csv` dataset:
import pandas as pd
import re

# Load the menu.csv dataset
df = pd.read_csv('../menu.csv')

# Define a regular expression pattern to match sizes (e.g., 10cm, 5inches)
size_pattern = r'(\d+(?:\.\d+)?)([a-z]+)'

# Create an empty list to store extracted size information
sizes = []

# Iterate through each row in the dataset
count_ = 0
for index, row in df.iterrows():
    # Extract size information from physical_description column using regular expression
    if pd.isnull(row['physical_description']):
        sizes.append(None)
    else:
        match = re.search(size_pattern, row['physical_description'])
        if match:
            count_ += 1
            # Extract the numeric value (size) and unit (e.g., cm, inches)
            size_value = float(match.group(1))
            size_unit = match.group(2).lower()
            
            # Convert units from centimeters to inches
            if size_unit == 'cm':
                size_value *= 0.3937
            
            # Append the extracted size information to the list
            sizes.append((size_value, size_unit))
        else:
            # Keep the original cell values if not match
            sizes.append(None)

# Create a new column 'size' and populate it with the extracted size information
df['size'] = sizes

print(df.head())  # Print the first few rows of the updated dataset
print(count_)
df.to_csv('../cleaned_ds/init_size.csv', index=False)
# Here's how the script works:

# 1. Load the `menu.csv` dataset into a pandas DataFrame using `pd.read_csv`.
# 2. Define a regular expression pattern `size_pattern` to match size information (e.g., `10cm`, `5inches`). The pattern consists of two groups: `(?:\d+(?:\.\d+)?)([a-z]+)`. The first group matches the numeric value, and the second group matches the unit.
# 3. Create an empty list `sizes` to store extracted size information.
# 4. Iterate through each row in the dataset using `df.iterrows`.
# 5. For each row, extract size information from the `physical_description` column using the regular expression pattern.
# 6. If a match is found, extract the numeric value (size) and unit (e.g., cm, inches) using `match.group(1)` and `match.group(2).lower()`, respectively.
# 7. Convert units from centimeters to inches if necessary.
# 8. Append the extracted size information to the list `sizes`.
# 9. Create a new column `'size'` and populate it with the extracted size information using the list comprehension `df['size'] = sizes`.

# This script should extract size information from the `physical_description` column and create a new column `'size'` containing the extracted values.