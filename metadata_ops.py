# This python script is to extract key parameters from the data operation
# cell edit: (row id, column name, value)
# delete row: (row id)
# delete column: (column name)
# split column: (column name, separator)
# transform: (column name, function)
# join column: (column list, concatenator)
# rename column: (old column name, new column name)
import json
import pandas as pd
from pprint import pprint
from ORMA.OpenRefineClientPy3.google_refine.refine import refine
# from ORMA.OpenRefineClientPy3.google_refine.refine.refine import RowsResponseFactory

from ORMA.extra_info import generate_recipe


def aug_recipe(project_id):
    # using retrospective provenance to augment recipe
    enhanced_recipe, schema_info = generate_recipe(project_id)
    return enhanced_recipe, schema_info


def get_dataframe(rows:list, columns: list):
    rows_collect = []
    for row in rows:
        cell = []
        for value in row['cells']:
            if not value:
                cell.append(None)
            else:
                cell.append(value['v'])
        rows_collect.append(cell)
    df = pd.DataFrame(rows_collect, columns=columns)
    return df


def process_undo_redo(oprefine, history_id):
    oprefine.undo_redo_project(history_id)
    column_response = oprefine.do_json('get-models', include_engine=False)
    columns = [value['name'] for value in column_response['columnModel']['columns']]
    row_response = oprefine.do_json('get-rows', include_engine=False)
    df = get_dataframe(row_response['rows'], columns)
    return df


def get_removed_row(df_prev, df_cur):
    # Get the removed row IDs
    removed_row_ids = df_prev[~df_prev.isin(df_cur).all(axis=1)].index.tolist()
    return [r_id+1 for r_id in removed_row_ids]

def special_handling(op: dict, prev_id, last_id, oprefine):
    # This is to add missing information:
    # single cell edit; remove-row  
    desc = op['description']
    desc_list = desc.split(" ")
    head_3 = " ".join(desc_list[:3])
    if head_3 == 'Edit single cell':
        left = desc_list.index('row')
        right = desc_list.index('column')
        row_id = left + 1
        row_index = desc_list[row_id].replace(',', '')
        column_id = right + 1
        column_name = " ".join(desc_list[column_id:])
        return {"op": "single_cell_edit", "row": row_index, "column": column_name}
    elif "op" in op:
        if op["op"] == "core/row-removal":
            h_id = op['id']
            df_prev = process_undo_redo(oprefine, prev_id)
            df_cur = process_undo_redo(oprefine, h_id)
            rows_id = get_removed_row(df_prev, df_cur)
            # recover the original status
            oprefine.undo_redo_project(last_id)
            return {"row_index": rows_id}
    else:
        return False


def meta_extract(r1):
    transforms = []
    cell_edits = []
    del_rows = []
    del_cols = []
    split_cols = []
    join_cols = []
    rename_cols = []

    for state_id, ops in enumerate(r1):
        op_name = ops['op']
        if op_name == "core/text-transform":
            col_name = ops['columnName']
            func = ops['expression']
            transform = {
                        "state_id": state_id,
                        "col_name": col_name,
                        "function": func}
            transforms.append(transform)
        elif op_name == "core/column-split":
            col_name = ops['columnName']
            separator = ops['separator']
            split_col = {
                "state_id": state_id,
                "col_name": col_name,
                "sepator": separator
            }
            split_cols.append(split_col)
        elif op_name == "core/column-rename":
            col_name = ops['oldColumnName']
            new_name = ops['newColumnName']
            rename_col = {
                "state_id": state_id,
                "old_name": col_name,
                "new_name": new_name
            }
            rename_cols.append(rename_col)
        # elif op_name == ""

    print(transforms)
    return transforms


def main():
    project_id = 2221256614441
    oprefine = refine.RefineProject(refine.RefineServer(), project_id)
    
    enhanced_recipe, schema_info = aug_recipe(project_id)
    last_id = enhanced_recipe[-1]['id']
    for step_id, op in enumerate(enhanced_recipe):
        prev_id = enhanced_recipe[step_id-1]['id']
        spe_cases = special_handling(op, prev_id, last_id, oprefine)
        if isinstance(spe_cases, dict):
            op.update(spe_cases)
    with open("recipes/enhanced_orma/citation_A.json", 'w')as f_A:
        json.dump(enhanced_recipe, f_A, indent=4)

    # f1 = 'recipes/usecase1.json'
    # with open(f1, 'r') as fp:
    #     r1 = json.load(fp)
    # list_ops_r1 = meta_extract(r1)


if __name__ == '__main__':
    main()