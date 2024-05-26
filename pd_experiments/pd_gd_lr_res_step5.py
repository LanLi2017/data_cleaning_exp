import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier


with open("data_output/pd_gd_updated.csv", "r")as f:
    df = pd.read_csv(f)

df1 = df.dropna(subset=['unit_capture'])
print(df1["unit_capture"].value_counts())

df1['unit_capture'] = df1['unit_capture'].replace('0',np.nan) # now value==2: unknown data
# Drop rows with missing values [width and height]
df1.dropna(subset=['width', 'height'], inplace=True)

# Label encode the unit_capture column for training
df1['unit_encoded'] = df1['unit_capture'].map({'cm': 0, 'inches': 1})

# separate the known and unknown unit captures
df1_train = df1[df1['unit_capture'].notna()]
df1_predict = df1[df1['unit_capture'].isna()]

# features and target for training
X_train = df1_train[['width', 'height']]
y_train = df1_train['unit_encoded']

# features for prediction 
X_predict = df1_predict[['width', 'height']]

#initialize the classifier
clf = RandomForestClassifier(n_estimators=100, random_state=42)

#train the classifier
clf.fit(X_train, y_train)

#predict the missing unit_capture
y_predict = clf.predict(X_predict)

# Map the predictions back to the unit_capture labels
df1.loc[df1['unit_capture'].isna(), 'unit_capture'] = y_predict
df1['unit_capture'] = df1['unit_capture'].map({0:'cm', 1:'inches'})

# mapping predicted data points back to original dataframe
df1.dropna(subset=['unit_capture'], inplace=True)
count_c = 0
count_i = 0
for idx, unit in zip(df1['id'], df1['unit_capture']):
    #TODO: convert the "cm" to "inches" with predicted data
    df.loc[df['id'] == idx, 'unit_capture'] = unit
    if unit == "cm":
        count_c += 1
        # print(f"The width: {df.loc[df['id'] == idx, 'width'].values[0]}")
        w = df.loc[df['id'] == idx, 'width'].values[0] *0.39
        h = df.loc[df['id'] == idx, 'height'].values[0] *0.39
        df.loc[df['id'] == idx, 'size'] = f"{round(w,2)}X{round(h,2)}"
    elif unit == "inches":
        count_i += 1
        w = df.loc[df['id'] == idx, 'width'].values[0]
        h = df.loc[df['id'] == idx, 'height'].values[0]
        df.loc[df['id'] == idx, 'size'] = f"{w}X{h}"

print(count_c, count_i)
print(df["unit_capture"].value_counts())

print("\nDataFrame after refilling predicted units:")
print(df)
df.to_csv('data_output/pd_or_lr_res.csv', index=False)
