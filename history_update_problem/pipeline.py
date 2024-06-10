import pandas as pd


def main():
    parent_folder = "../pd_exp_prep"
    data_input = f"{parent_folder}/data_input/menu.csv"
    input_df = pd.read_csv(data_input)
    # remove NA
    prep_df = input_df.dropna(subset=['physical_description'])
    # Sample 1000 rows
    df = prep_df.sample(n=100, random_state=42)
    df.to_csv("sample_data/menu_sp.csv", index=False)


if __name__ == '__main__':
    main()