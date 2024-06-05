import pandas as pd
import re

# Load the dataset
df = pd.read_csv('../menu.csv')

# Define a function to extract size information
def extract_size(row):
    description = row['physical_description']
    pattern = r'(\d+(?:\.\d+)?)(?: x (\d+(?:\.\d+)?))?(?: in|cm)?'
    if pd.isnull(description):
        return None
    else:
        match = re.search(pattern, description)
        if match:
            size1 = float(match.group(1))
            if match.group(2):
                size2 = float(match.group(2))
                return f"{size1} x {size2}"
            else:
                return str(size1)
        else:
            return None

# Apply the function to each row in the target column
df['size'] = df.apply(lambda row: extract_size(row), axis=1)

# Print the updated dataframe
print(df.head())
df.to_csv('../cleaned_ds/exp_no_sample_size.csv')

# This script defines a function `extract_size` that uses regular expressions to extract size information from a given description. The pattern matches one or two numbers (with optional decimal points) and an optional " x" separator, followed by an optional unit ("in" or "cm"). The function returns the extracted size(s) as a string.

# The script then applies this function to each row in the `physical_description` column using the `.apply()` method. The resulting sizes are stored in a new column called `size`.

# Finally, the script prints the first few rows of the updated dataframe using the `.head()` method.