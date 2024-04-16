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
from ORMA.orma import ORMAProcessor, cluster_main, get_schema_list, merge_basename, translate_operator_json_to_graph


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
        return {"op": "single_cell_edit", "row": row_index, "columnName": column_name}
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


def col_extract(recipe):
    cols = []
    for state_id, ops in enumerate(recipe):
        col_dict = {}
        if 'op' in [*ops]:
            op_name = ops['op']
            if op_name == "core/column-addition":
                col_name = merge_basename(ops) # it could be a list or a string 
                if isinstance(col_name, list):
                    col_dict = {col:state_id for col in col_name}
                else:
                    col_dict = {col_name: state_id}
            elif op_name == "core/column-rename":
                col_name = ops['oldColumnName']
                col_dict = {col_name: state_id}
            # elif op_name == "single_cell_edit":
            #     col_name = 
            else:
                try:
                    col_name = ops['columnName']
                    col_dict = {col_name: state_id}
                except:
                    pass
        if col_dict:
            cols.append(col_dict)
    return cols


def exe_enhanced_recipe(project_id, fname):
    oprefine = refine.RefineProject(refine.RefineServer(), project_id)
    enhanced_recipe, schema_info = aug_recipe(project_id)
    last_id = enhanced_recipe[-1]['id']
    for step_id, op in enumerate(enhanced_recipe):
        prev_id = enhanced_recipe[step_id-1]['id']
        spe_cases = special_handling(op, prev_id, last_id, oprefine)
        if spe_cases:
            op.update(spe_cases)
    with open(fname, 'w')as fp:
        json.dump(enhanced_recipe, fp, indent=4)
    return enhanced_recipe, schema_info


# Detect linked nodes
def dfs(graph, u):
    visited_nodes = [u]
    try:
        for v in graph[u]:
            visited_nodes += dfs(graph, v)
    except KeyError:
        pass
    return visited_nodes


def detect_conflicts():
    # if rowid/column name overlap (at least one of them)
    # check the other key parameters..
    # return the data cleaning steps
    pass 


def main():
    project_id_Alice = 2221256614441
    project_id_Bob = 1883828664735
    
    # add information to the old recipe:
    er1, schema_info_1 = exe_enhanced_recipe(project_id_Alice, "recipes/enhanced_orma/alice.json")
    er2, schema_info_2 = exe_enhanced_recipe(project_id_Bob, "recipes/enhanced_orma/bob.json")

    # f1 = 'recipes/usecase1.json'
    # with open(f1, 'r') as fp:
    #     r1 = json.load(fp)
    # list_ops_r1 = meta_extract(r1)

def test_():
    recipe, schema_info = exe_enhanced_recipe(1720089821831, "recipes/enhanced_orma/test_rremoval.json")
    
    # schemas = get_schema_list(schema_info)
    orma_proc = ORMAProcessor()
    # orma_data = translate_operator_json_to_graph(recipe, schemas)
    # for data in orma_data:
    #     print(data.process)
    #     print(data.in_node_names)
    orma_proc.generate_views(output="ORMA_Output/test_rremoval.png", type= 'parallel_view',
                             json_data=recipe, schema_info=schema_info)
    cols = col_extract(recipe) # [{'Book Title': 0}, {''}]
    
    # column_ids: dict[str, set[int]] = {}
    # for arrangement in cols:
    #     for col, col_id in arrangement.items():
    #         column_ids.setdefault(col, set()).add(col_id)
    
    # result = []
    # query = cluster_main(2221256614441)
    # for columns in query:
    #     ids = set()
    #     for col in columns:
    #         ids.update(column_ids.get(col, set()))
    #     result.append(ids)
    
    # pprint(result)
    


if __name__ == '__main__':
    test_()
    # main()