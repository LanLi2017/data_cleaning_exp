import pandas as pd 
import numpy as np
import re 
   
def acc_(row, gt_col, tg_col):
    #@params gt_col: ground truth column
    #@params tg_col: target column
    gt_val = row[gt_col].strip().replace(' ', '') if pd.notna(row[gt_col]) else ''
    tg_val = row[tg_col].strip().replace(' ', '') if pd.notna(row[tg_col]) else ''
    return gt_val == tg_val


def consist_(df, sing_ids, comp_ids):
    # Format Consistency 
    sing_pattern = re.compile(r'\d*\.?\d+\s*[Xx]\s*\d*\.?\d+\s*')
    cmp_pattern = re.compile(r'\d*\.?\d+\s*[Xx]\s*\d*\.?\d+(\s+\w+)?\s*;\s*\d*\.?\d+\s*[Xx]\s*\d*\.?\d+(\s+\w+)?')
    res = []
    for index, row in df.iterrows():
        size = row['size']
        if not pd.isnull(size):
            if row['id'] in sing_ids:
                match = bool(sing_pattern.match(size))
                res.append((row['id'], match))
            elif row['id'] in comp_ids:
                match = bool(cmp_pattern.match(size))
                res.append((row['id'], match))
        else:
            res.append((row['id'], False))
    return res 



def categ_values(filtered_ids, df, col='size'):
    # Categorize values in target columns:
    # Return ids for composite; singular
    comp_ids = df[df[col].str.contains(';', na=False)]['id'].tolist()
    sing_ids = list(set(filtered_ids) - set(comp_ids))
    assert len(sing_ids)+len(comp_ids)==len(filtered_ids)
    return sing_ids, comp_ids


def main():
    parent_folder = 'data_quality_exp/input.dataset'
    # split_mapping: locate 4th as size; 
    # split_recursive: recursive and appending values-split;
    # split_normalize_len: locate outliers by length; 
    # split_regex_recur: regex match pattern
    dataset = ['pd_split_mapping.csv', 
               'pd_split_recur.csv',
               'pd_split_norm_len.csv',
               'pd_split_regex_recur.csv']
    cols = ['id', 'size']
    # load ground truth dataset
    gd_dataset = 'data_quality_exp/ground_truth_pd/menu_size.csv'
    gd_df = pd.read_csv(gd_dataset)
    # unit: [cm, inches, unknown]
    # filtered NA rows => measure completeness
    filtered_gt_cp = gd_df.dropna(subset=['physical_description'])
    gt_cp_ids = filtered_gt_cp['id'].tolist()
    print(f"After removing NA rows, the number of rows: {len(gt_cp_ids)}")

    # filtered unknown unit rows 
    # 1. accuracy 2. consistency 
    gt_prep = filtered_gt_cp[filtered_gt_cp['unit_capture']!='0']
    filtered_ids = gt_prep['id'].tolist()
    print(f"After removing unknown rows, the number of rows: {len(filtered_ids)}")

    # create evaluation matrix
    ev_res = []

    for ds in dataset:
        target_df = pd.read_csv(f"{parent_folder}/{ds}")
        print(f'The total rows of target dataset: {target_df.shape[0]}')

        # Task I : Calculate Completeness 
        filtered_target_dataset = target_df[target_df['id'].isin(gt_cp_ids)]
        len_rows = filtered_target_dataset.shape[0]
        print(f'The total rows after filter out the NA row {len_rows}')
        # Count NA rows for each method
        size_na_count = filtered_target_dataset['size'].isna().sum()
        comp_ratio = 1-size_na_count/len_rows
        print(f"Completeness ratio in {ds}: {comp_ratio}")
        
        td_prep = target_df[target_df['id'].isin(filtered_ids)]
        len_prep_rows = td_prep.shape[0]
        print(f'The total rows after filter out unknown rows {len_prep_rows}')
        merged_df = pd.merge(gt_prep, td_prep, on='id', suffixes=('_gt', '_tg'))
        # Task II: Calculate Accuracy 
        merged_df['comparison'] = merged_df.apply(
                                    lambda row: acc_(row, 'size_gt', 'size_tg'), 
                                    axis=1)
        acc_count = merged_df['comparison'].sum()
        acc_ratio = acc_count/len_prep_rows
        print(f"Accuracy ratio in {ds}: {acc_ratio}")

        # Task III: Calculate Consistency
        sing_ids, comp_ids = categ_values(filtered_ids, gt_prep)
        match_res = consist_(target_df, sing_ids, comp_ids)
        consis_ratio = sum(1 for _,match in match_res if match is True)/len_prep_rows
        print(f"Consistency ratio in {ds}: {consis_ratio}")
        # Append each row
        ev_res.append([ds, comp_ratio, acc_ratio, consis_ratio])
    
    ev_matrix = pd.DataFrame(ev_res, 
                             columns=['Dataset', 'Completeness', 'Accuracy', 'Consistency'])
    
    print(ev_matrix)

if __name__ == '__main__':
    main()