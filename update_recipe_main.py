import os
import pandas as pd

from profiling_DQ import acc_, categ_values, consist_


def gen_sample():
    parent_folder = "pd_exp_prep"
    data_input = f"{parent_folder}/data_input/menu.csv"
    input_df = pd.read_csv(data_input)
    # remove NA
    prep_df = input_df.dropna(subset=['physical_description'])
    # Sample 1000 rows
    df = prep_df.sample(n=100, random_state=42)
    # NO RERUN
    df.to_csv("history_update_problem/data.input/menu_sp.csv", index=False)


def gen_ev(sample_dir, gt_init):
    # Generate data quality evaluation matrix 
    #@params sample_dir: directory of all output CSV files 
    #@params gt_init: sample data ground truth (init version)
    ev_res = []
    csv_files = []
    for root, dirs, files in os.walk(sample_dir):
        for file in files:
            if file.endswith('.csv'):
                fp = os.path.join(root, file)
                print(f"current file: {fp}")
                csv_files.append(fp)
    
    merge_dfs = {}
    for file in csv_files:
        df = pd.read_csv(file)
        rows = df.shape[0]
        assert rows == 100
        # Calculate accuracy
        # NOTE: instead of using ground truth finalized version, we use initial version
        # NO UNIT Conversion.
        merge_df = pd.merge(gt_init, df, on='id', how='right', suffixes=('_gt', f'_tg'))
        merge_df['comparison'] = merge_df.apply(
                                    lambda row: acc_(row, 'size_gt', 'size_tg'),
                                    axis=1)
        acc_count = merge_df['comparison'].sum()
        acc_ratio = acc_count/rows
        print(f"Acc Count in {file}: {acc_count}")

        # Calculate completeness 
        # Count NA rows for each method
        size_na_count = merge_df['size_tg'].isna().sum()
        comp_ratio = 1-size_na_count/rows
        print(f"Completeness ratio in {file}: {comp_ratio}")
    
        # Append each row
        fname = file.split('/')[-1]
        ev_res.append([fname, acc_ratio, comp_ratio])
        merge_dfs[fname] = merge_df
    
    ev_matrix = pd.DataFrame(ev_res, 
                             columns=['Dataset', 'Accuracy', 'Completeness'])
    
    return ev_matrix,merge_dfs

def process_dq_matrix():
    # Generate sample dataset
    # Process dataset in OpenRefine
    # Evaluate data output
    par_folder = 'history_update_problem'
    
    # Using gt_init (sample data ground truth) to cal accuracy
    # Basic transformations..
    gt_init_fp = f"{par_folder}/ground.truth.init/menu_gd_init.csv"
    gt_init = pd.read_csv(gt_init_fp)

    out_dir = f"{par_folder}/data.out"
    ev, merge_dfs = gen_ev(out_dir, gt_init) # Generate evaluation matrix [accuracy, completenss, consistency]
    print(ev)
    ev.to_csv(f'{par_folder}/data.quality.matrix/ev_matrix.csv')
    
    log_dq = f"{par_folder}/data.quality.matrix"
    columns_keep = ["id", "size_gt", "size_tg", "comparison"]
    for f,merge_df in merge_dfs.items():
        filter_df = merge_df[columns_keep]
        filter_df.to_csv(f"{log_dq}/{f}", index=False)


def main():
    process_dq_matrix()
    # The main task is to infer the relationship between:
    # Diff(dx, dy) =<= Diff(rx, ry)
    # More correct cell values, Why? --> dx: False, dy: True

    pass


if __name__ == '__main__':
    main()