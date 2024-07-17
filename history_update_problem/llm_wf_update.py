# LLM-based history update solution
import argparse
import ast
import requests
import json

import pandas as pd

# from history_update_problem.call_or import export_rows
from call_or import *


model = "llama3"
# parser = argparse.ArgumentParser()
# parser.add_argument("--start", required=True, type=int)
# parser.add_argument("--end", required=True, type=int)
# parser.add_argument("--dry_run", default=False, action="store_true",
#     help="whether it's a dry run or real run.")
# parser.add_argument(
#     "--temperature", type=float, default=0.7,
#     help="temperature of 0 implies greedy sampling.")
# simple case: How many types of event in the menu table?
prep_learning = """
Here is a python script calling OpenRefine API to do the data cleaning, multiple functions/transformations are defined. 
Python code:

class RefineProject:
    def text_transform(project_id, column, expression,on_error='set-to-blank', repeat=False, repeat_count=10):
        '''
        OpenRefine's transformations can change {{column}} contents by applying {{expression}}:
        The default is GREL (General Refine Expression Language), Altertively, it accept python code.
        Example: text_transform(project_id, column="id", expression="return int(value)") 
        Using python code to transform values in column id as integer. 
        '''
        response = self.do_json('text-transform',
                                {
                                    'columnName': column,
                                    'expression': expression,
                                    'onError': on_error,
                                    'repeat': repeat,
                                    'repeatCount': repeat_count,
                                })
        return response

    def mass_edit(project_id, column, edits, expression='value'):
        '''
        Replacing data values with new values in {{column}} with new values, old and new values are defined in {{edits}}
        Example: 
        mass_edit(project_id, "city", edit_from="Cicago", edit_to="Chicago")
        Replace cell values in column city from spelling "Cicago" to "Chicago"
        '''
        edits = json.dumps(edits)
        response = self.do_json('mass-edit',
                                {
                                    'columnName': column, 'expression': expression, 'edits': edits})
        return response

    def add_column(project_id, column, new_column, expression='jython:return value', column_insert_index=None,
                   on_error='set-to-blank'):
        '''Add a new column named as {{new_column}} based on {{expression}}. if the expression is default, then copy-paste cell values from {{column}} to {{new_column}}
        using jython: followed the code if the expression is written in python.
        Example: add_column(project_id, "name", "full name", expression="jython:res=cells['first name'].value+','+cells['last name'].value\nreturn res" )'''
        if column_insert_index is None:
            column_insert_index = self.column_order[column] + 1
        response = self.do_json('add-column',
                                {
                                    'baseColumnName': column,
                                    'newColumnName': new_column,
                                    'expression': expression,
                                    'columnInsertIndex': column_insert_index,
                                    'onError': on_error})
        self.get_models()
        return response

    def split_column(project_id,column,separator=',',mode='separator',regex=False,guess_cell_type=True,remove_original_column=False):
        '''split {{column}} by {{separator}} to generate more new columns
        Example: split_column(project_id, "full_name", "," )
        Explain: cell values in column full_name are composite values{{first name, last name}} concatenated with ',', splitting column and we can extract
        first name and last name as the new columns.'''
        response = self.do_json('split-column',
                                {
                                    'columnName': column,
                                    'separator': separator,
                                    'mode': mode,
                                    'regex': regex,
                                    'guessCellType': guess_cell_type,
                                    'removeOriginalColumn': remove_original_column,
                                })
        self.get_models()
        return response

    def rename_column(project_id, column, new_column):
        '''Give old {{column}} name a more meaningful {{new_column}} name.
        Example: rename_column(project_id, 'column 1', 'city')
        Explain: the old column name {{column 1}} is updated as {{city}}, which becomes more meaningful.'''
        response = self.do_json('rename-column',
                                {
                                    'oldColumnName': column,
                                    'newColumnName': new_column,
                                })
        self.get_models()
        return response
        
    def remove_column(project_id, column):
        '''remove {{column}} if it is useless or of low quality, e.g., most cells are empty and cannot be inferred.
        Example: remove_column(project_id, 'currency')
        Explain: most of the cells in column {{currency}} are NA, so we remove this column.'''
        response = self.do_json('remove-column', {'columnName': column})
        self.get_models()
        return response
"""
exp_in_out = """
Data input before data cleaning:
/*
col : physical_description 
row 1 : CARD; 4.75X7.5;
row 2 : BROADSIDE; ILLUS; COL; 5.5X8.50; 
row 3 : BROADSIDE; ILLUS; COL; 3,5X7;
row 4 : CARD;ILLUS;5.25X8/25;
row 5 : 30x21cm folded; 30x42cm open
row 6 : CARD; ILLUS; 6 x 9.75 in.
row 7 : Booklet; 8.25 x 11.5 inches
*/

Expected data output after data cleaning:
/*
col : physical_description               | size              | unit
row 1 : CARD; 4.75X7.5;                  | 4.75X7.5          | 
row 2 : BROADSIDE; ILLUS; COL; 5.5X8.50; | 5.5X8.50          |
row 3 : BROADSIDE; ILLUS; COL; 3,5X7;    | 3.5X7             |      
row 4 : CARD;ILLUS;5.25X8/25;            | 5.25X8.25         |
row 5 : 30x21cm folded; 30x42cm open     | 30x21; 30x42      | cm
row 6 : CARD; ILLUS; 6 x 9.75 in.        | 6 x 9.75          | inches
row 7 : Booklet; 8.25 x 11.5 inches      | 8.25 x 11.5       | inches
*/
"""
map_ops_func = {
"core/column-split": split_column,
"core/column-addition": add_column,
"core/text-transform": text_transform,
"core/mass-edit": mass_edit,
"core/column-rename": rename_column,
"core/column-removal": remove_column
}


def export_intermediate_tb(project_id):
    # Call API to retrieve intermediate table
    rows = []
    csv_reader = export_rows(project_id)
    for row in csv_reader:
        rows.append(row)
    df = pd.DataFrame(rows)
    return df


def format_sel_col(df):
    table_caption = "A mix of simple bibliographic description of the menus"
    # df = pd.read_csv(fp)
    columns = df.columns.tolist() # column schema information 
    col_priority = []
    for col in df.columns:
        # Get the column name
        column_name = col
        # Get three row values from the column
        row_values = df[col].head(3).tolist()
        # Append column name and three row values as a sublist
        col_priority.append([column_name] + row_values)
    return {
        "table_caption": table_caption,
        "columns": columns,
        "table_column_priority": col_priority
    }


def gen_table_str(fp, col_sel_res):
    with open(col_sel_res, 'r') as file:
        column_string = file.read().strip()  # Read the content and remove any surrounding whitespace/newlines
    # Split the string by commas to get a list of column names
    target_cols = [col.strip() for col in column_string.split(',')]
    print(f"target columns: {target_cols}")
    # generate sample table string as the task input [intermediate table]
    df = pd.read_csv(fp, index_col=None)[target_cols]
    # Sample the first 30 rows
    df = df.head(30)
    # Prepend "row n:" to each row
    df.insert(0, 'Row', [f'row {i+1}:' for i in range(len(df))])
    # Convert the DataFrame to a Markdown string without the header
    rows_lines = [f"row {i+1}: | " + " | ".join(map(str, row)) + " |" for i, row in df.iterrows()]
    # rows_lines = [f"| " + " | ".join(map(str, row)) + " |" for _, row in df.iterrows()]
    # Add the column schema line
    column_names = " | ".join(df.columns)
    column_schema = f'col: | {column_names} |\n'
    # Combine the column schema with the DataFrame content
    table_str = column_schema + "\n".join(rows_lines)
    return table_str


def generate(prompt, context, log_f):
    r = requests.post('http://localhost:11434/api/generate',
                      json={
                          'model': model,
                          'prompt': prompt,
                          'context': context,
                          'options':{'temperature':0}
                      },
                      stream=True)
    r.raise_for_status()
    
    res = []
    for line in r.iter_lines():
        body = json.loads(line)
        response_part = body.get('response', '')
        # the response streams one token at a time, print that as we receive it
        # print(response_part, end='', flush=True)
        res.append(response_part)
        log_f.write(response_part)

        if 'error' in body:
            raise Exception(body['error'])

        if body.get('done', False):
            return body['context'], ''.join(res)
        

if __name__ == "__main__":
    # Define EOD: End of Data Cleaning
    # Input:intermediate table; Example output format
    # Output: False/True
    __eod = """ 
            Return True or False ONLY. NO EXPLANATIONS.
            Return True: If NO data preparation is needed anymore on the intermediate table: data values are in high quality 
            (similar to {{Expected data output after data cleaning}}). 
            Otherwise, Return False.
             """
    dc_obj = """ 
             The task is to figure out how the size of menus evolves over the decades. 
             For this task, you will use {{menu}} dataset from NYPL(New York Public Library). 
             Dataset Description: {{A mix of simple bibliographic description of the menus}},
             The relevant columns input: {{physical_description}}
             """
    log_f = open("CoT.response/llm_dcw.txt", "w")
    # fpath = "data.in/menu_llm.csv"
    ops = [] # operation history 
    project_id = 2681949500112
    eod_flag = "False" # Initialize Flag for "end of data cleaning" as False
    
    while eod_flag == "False":
        context = []
        # The eod_flag is True.
        # Return current intermediate table
        df = export_intermediate_tb(project_id)

        # 1. LLM predict next operation: five op-demo and chain-of ops 
        # TASK I: select target column(s)
        with open("prompts/f_select_column.txt", 'r')as f:
            sel_col_learn = f.read()
        prompt_sel_col = "Learn how to select columns based on given question:\n" + sel_col_learn
        sel_col_tb = format_sel_col(df)
        prompt_sel_col += "Table input:\n" + json.dumps(sel_col_tb)
        prompt_sel_col += f"Data cleaning objective: {dc_obj}"
        prompt_sel_col += """Return relevant column name(s) in a python list based on {{Data cleaning objective}} ONLY. NO EXPLANATIONS.
                             Example Return: ['column 1', 'column 2']"""
        context, sel_cols = generate(prompt_sel_col, context, log_f)
        print(sel_cols)
        cols_list = ast.literal_eval(sel_cols) 

        # TASK II: select operations 
        prompt_sel_ops = "Learn available python functions to process data in class RefineProject:" + prep_learning
        ops = get_operations(project_id)
        op_list = [dict['op'] for dict in ops]
        functions_list = [map_ops_func[operation].__name__ for operation in ops]
        prompt_sel_ops += f"Chain of operation history has been applied: {functions_list} ->\n"
        prompt_sel_ops += "Intermediate Table:\n" + df
        prompt_sel_ops += f"Data cleaning purpose: {dc_obj}"
        prompt_sel_ops += """To make the data in a good quality that fit for {{Data cleaning purpose}}, select one 
                           function from RefineProject."""
        
        context, sel_op = generate(prompt_sel_ops, context, log_f)
        print(sel_op)

        # prompt += f"Generate a python script under the folder 'CoT.response', name it as table_{process_id}.py"
        # process_id += 1

        # TASK III: Call API process data


        # Re-execute intermediate table
        df = export_intermediate_tb(project_id)
        # TASK IV:
        # Keep passing intermediate table and data cleaning objective, until eod_flag is True. End the iteration.
        iter_prompt = dc_obj + f""" intermediate table:{df} """\
                            + exp_in_out \
                            + __eod
        context, eod_flag = generate(iter_prompt, context, log_f)
        print(eod_flag)
        break

        # TASK II: get_certain_columns(table_str: str, columns: list[str])
        
        # process_id = 0


    # prompt += "Learn how to generate arguments for operation add column: \n" + 
    log_f.close()
