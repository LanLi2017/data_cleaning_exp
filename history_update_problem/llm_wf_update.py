# LLM-based history update solution
import argparse
import ast
import importlib.util
import inspect
from types import ModuleType
from typing import List
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
    def text_transform(project_id, column, expression):
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

    def mass_edit(project_id, column, edits):
        '''
        Replacing data values with new values in {{column}} with new values, old and new values are defined in {{edits}}
        edits: [{'from': ['foo'], 'to': 'bar'}, {...}]
        Example: 
        mass_edit(project_id, "city", edits=[{'from':["Cicago"], 'to':"Chicago"}])
        Replace cell values in column city from spelling "Cicago" to "Chicago"
        '''
        edits = json.dumps(edits)
        response = self.do_json('mass-edit',
                                {
                                    'columnName': column, 'expression': expression, 'edits': edits})
        return response

    def add_column(project_id, column, new_column, expression):
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

    def split_column(project_id,column,separator):
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

# map_func_fname = {
#     'split_column': 'prompts/split_column.txt' ,
#     'add_column': 'prompts/add_column.txt',
#     'text_transform': 'prompts/text_transform.txt',
#     'mass_edit': 'prompts/mass_edit.txt',
#     'rename_column':'prompts/rename_column.txt',
#     'remove_column': 'prompts/remove_column.txt',
# }

def export_intermediate_tb(project_id):
    # Call API to retrieve intermediate table
    rows = []
    csv_reader = export_rows(project_id)
    rows = list(csv_reader)
    columns = rows[0]
    data = rows[1:]
    # for row in csv_reader:
    #     rows.append(row)
    df = pd.DataFrame(data, columns=columns)
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


def gen_table_str(df):
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


def gen_col_str(df, col_name:str):
    column_values = df[col_name].astype(str).tolist()
    col_string = ' '.join(column_values)
    
    return col_string


def get_function_arguments(script_path: str, function_name: str) -> List[str]:
    """
    Get the arguments of a function from a given Python script.

    Parameters:
        script_path (str): Path to the Python script.
        function_name (str): Name of the function to inspect.

    Returns:
        List[str]: List of argument names.
    """
    # Load the script as a module
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get the function object
    func = getattr(module, function_name)
    
    # Get the function signature
    sig = inspect.signature(func)
    
    # Extract argument names
    args = [param.name for param in sig.parameters.values()
            if param.default == inspect.Parameter.empty]
    
    return args

def generate(prompt, context, log_f, temp=0):
    """
    Send a POST request to generate a response based on the provided prompt and context.

    Parameters:
        prompt (str): The input prompt for the generation.
        context (str): The context to be used for the generation.
        model (str): The model to be used for the generation. Defaults to 'default-model'.

    Returns:
        str: The context from the response if generation is done.

    Raises:
        Exception: If there is an error in the response.
    """
    r = requests.post('http://localhost:11434/api/generate',
                      json={
                          'model': model,
                          'prompt': prompt,
                          'context': context,
                          'options':{'temperature': temp}
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
        prompt_sel_col = "Learn how to select column based on given question:\n" + sel_col_learn
        sel_col_tb = format_sel_col(df)
        prompt_sel_col += "Table input:\n" + json.dumps(sel_col_tb)
        prompt_sel_col += f"Data cleaning objective: {dc_obj}"
        prompt_sel_col += """Step by step, Return one relevant column name(string) based on {{Data cleaning objective}} ONLY. NO EXPLANATIONS.
                             Example Return: 'column 1' """
        context, sel_col = generate(prompt_sel_col, context, log_f)
        print(sel_col)
        # cols_list = ast.literal_eval(sel_cols) 

        # TASK II: select operations 
        prompt_sel_ops = "Learn available python functions to process data in class RefineProject:" + prep_learning
        ops = get_operations(project_id)
        op_list = [dict['op'] for dict in ops]
        functions_list = [map_ops_func[operation].__name__ for operation in op_list]
        print(functions_list)
        prompt_sel_ops += f"Chain of operation history has been applied: {functions_list} ->\n"
        # prompt_sel_ops += f"Sample first 30 rows from the Intermediate Table: {gen_table_str(df)} \n"
        prompt_sel_ops += f"Data values in target column: {gen_col_str(df, sel_col)}"
        prompt_sel_ops += f"Data cleaning purpose: {dc_obj}"
        prompt_sel_ops += """
                           Return one selected function name from Functions Pool of RefineProject ONLY. NO EXPLANATIONS.
                           Functions pool: split_column, add_column, text_transform, mass_edit, rename_column, remove_column.
                           This task is to make the data in a good quality that fit for {{Data cleaning purpose}}."""
        
        context, sel_op = generate(prompt_sel_ops, context, log_f)
        print(sel_op)

        # TASK III: Learn operation arguments (share the same context with sel_op)
        args = get_function_arguments('call_or.py', sel_op)
        args.remove('project_id')  # No need to predict project_id
        args.remove('column')
        prompt_sel_args = f"""Next predicted operation is {sel_op}"""
        # prompt_sel_args += f"Sample first 30 rows from the Intermediate Table: {gen_table_str(df)} \n"
        with open(f'prompts/{sel_op}.txt', 'r') as f1:
            sel_args_learn = f1.read()
        prompt_sel_args += f"""
                            The purpose of applying operation is to make target column close to expected output.
                            """
        prompt_sel_args += f"""Learn proper arguments based on intermediate table and data cleaning purpose:
                                {sel_args_learn}"""
        
        if sel_op == 'split_column':
            prompt_sel_args += f"""
                                Therefore, the answer is: split_column(column={sel_col}, separator=?).
                                Return value for question mark.
                                """
        elif sel_op == 'add_column':
            prompt_sel_args += f"""
                                Therefore, the answer is: add_column(column={sel_col}, expression=?, new_column=? ).
                                Return value for question mark.
                                """
        elif sel_op == 'rename_column':
            prompt_sel_args += f"""
                                Therefore, the answer is: rename_column(column={sel_col}, new_column=?).
                                Return value for question mark.
                                """
        elif sel_op == 'text_transform':
            prompt_sel_args += f"""
                                Therefore, the answer is: text_transform(column={sel_col}",expression=?). 
                                Return value for question mark.
                                """
        elif sel_op == 'mass_edit':
            prompt_sel_args += f"""
                                Therefore, the answer is: text_transform(column={sel_col}",expression=?). 
                                Return value for question mark.
                                """
        elif sel_op == 'remove_column':
            prompt_sel_args += f"""
                                Therefore, the answer is: remove_column(column={sel_col})
                                """
        context, sel_args = generate(prompt_sel_args, context, log_f)
        print(f"selected arguments: {sel_args}")
        # TASK IV: Call API process data

        # Re-execute intermediate table
        df = export_intermediate_tb(project_id)
        # TASK V:
        # Keep passing intermediate table and data cleaning objective, until eod_flag is True. End the iteration.
        iter_prompt = dc_obj + f""" intermediate table:{df} """\
                            + exp_in_out \
                            + __eod
        context, eod_flag = generate(iter_prompt, [], log_f)
        print(eod_flag)
        break 

    # prompt += "Learn how to generate arguments for operation add column: \n" + 
    log_f.close()
