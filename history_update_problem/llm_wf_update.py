# LLM-based history update solution
import importlib.util
import inspect
from typing import List
import requests
import json
import re

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
    
    def reorder_rows(project_id, sort_by=None):
        ''' reorder_rows if need to the results need to be retrieved through some order. e.g., what's the most/least/top N occurred (frequency)
        species' names.
        Example: reorder_rows(project_id, 'frequency')
        if sort_by is not None:
            self.sorting = Sorting(sort_by)
        response = self.do_json('reorder-rows', {'sorting': self.sorting.as_json()})
        # clear sorting
        self.sorting = Sorting()
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
"core/column-removal": remove_column,
"core/row-reorder": reorder_rows,
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


def extract_exp(content):
    """This function is to extract python code from generated results"""
    match = re.search(r'```(.*?)```', content, re.DOTALL)
    if match:
        code_block = match.group(1).strip()
        code_block = code_block.replace('; ', '\n')
        return code_block
    else:
        print("No code block found.")
        return False


def diff_check(func_name, old_df, new_df, target_col):
    """This function is using the diff of applied ops as a context to inspire
        LLMs to generate next operation"""
    """Qs: which kind of diff refer to good cleaning operation?"""
    # return:
    # column-level diff: {column-schema: }
    # cell-level diff: 
    if func_name=='text_transform':
         differences = {}
         len_df = len(new_df)
         assert len(old_df) == len(new_df)

         for i in range(len_df):
            old_value = old_df.iloc[i][target_col]
            new_value = new_df.iloc[i][target_col]
            if old_value != new_value:
                differences[i] = {old_value: new_value}
        
         prompt_changes = f"""The changes resulted by text_transform: a dictionary of pairs of old value and new value: {differences}"""
         return prompt_changes


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
            You are an expert in data cleaning and able to choose appropriate operations and arguments to prepare the data in good format
            and correct semantics. Available data cleaning functions include split_column (add more columns by splitting original composite values), 
            add_column (add new column), text_transform (apply expression to transform data), mass_edit (standardize data by replacing old values with new values), 
            rename_column (give more meaningful column names), remove_column.
            Return True If NO data cleaning operation is needed on the intermediate table, i.e., the current table can address the {{Data Cleaning Objective}}: 
            data values from the target column are accurate (no mispelling or outliers) and complete (less missing values), no duplicates, 
            no inconsistencies (no violations of the data quality rules).
            Otherwise, Return False.
             """
    __ev_op = """
            Evaluation Instruction: 
            This instruction is to teach you how to evaluate the performance of applied function: whether 
            the function correctly transforms the data.
            Checking the changes (dictionary type, every key-value pair represent: {old value: new value}) by different functions
            in different ways: 
            For text transform, the performance is good if new values are more consistent: same format, same semantics, less missing values,
            more correct spellings. Conversely, this function will decrease the data quality and should be reverted.   
            """
    __op = __ev_op +\
            """
            Return True or False ONLY. NO EXPLANATIONS.
            Since you have selected one data cleaning function and generated arguments to transform the data at this step.
            Provided descriptions and examples learned for this function, and actual changes caused by this operation,  
            please refer to Evaluation Instruction to check whether it is correctly applied on the dataset. The answer is important for it reflect the quality 
            of the function. You CAN ONLY return True if the changes strongly show that new values are better than the old values.
            Otherwise, Return False.
            """
    # Compare with using example in and out
    # __eod_exp = """ 
            # Return True or False ONLY. NO EXPLANATIONS.
            # Return True: If NO data preparation is needed anymore on the intermediate table: 
            # data values are in high quality to address the {{Data Cleaning Objective}}.
            # (similar to {{Expected data output after data cleaning}}). 
            # Otherwise, Return False.
            #  """
    # dc_obj = """ 
    #          The task is to figure out how the size of menus evolves over the decades. 
    #          For this task, you will use {{menu}} dataset from NYPL(New York Public Library). 
    #          Dataset Description: {{A mix of simple bibliographic description of the menus}},
    #          The relevant columns input: {{physical_description}}
    #          """
    dc_obj = """ 
             {{Data Cleaning Objective}}:
             The task is to figure out how many different events are recorded in the collected menus. 
             For this task, you will use {{menu}} dataset from NYPL(New York Public Library). 
             Dataset Description: {{A mix of simple bibliographic description of the menus}}.
             """
    log_f = open("CoT.response/llm_dcw.txt", "w")
    # fpath = "data.in/menu_llm.csv"
    ops = [] # operation history 
    project_id = 2681949500112    
    df_init = export_intermediate_tb(project_id)
    prompt_init = dc_obj + f""" intermediate table:{df_init} """\
                      + __eod
                            # + exp_in_out \
   
    context, eod_flag = generate(prompt_init, [], log_f)
    print('======')
    print(eod_flag)

    while eod_flag == "False":
        context = []
        # The eod_flag is True.
        # Return current intermediate table
        df = export_intermediate_tb(project_id)
        av_cols = df.columns.to_list()


        # 1. LLM predict next operation: five op-demo and chain-of ops 
        # TASK I: select target column(s)
        with open("prompts/f_select_column.txt", 'r')as f:
            sel_col_learn = f.read()
        prompt_sel_col = "Learn how to select column based on given question:\n" + sel_col_learn
        sel_col_tb = format_sel_col(df)
        prompt_sel_col += "Table input:\n" + json.dumps(sel_col_tb)
        prompt_sel_col += f"Data cleaning objective: {dc_obj}"
        prompt_sel_col += f"""Available columns for chosen: {av_cols}.
                             TASK I: Step by step, Return one relevant column name(string) based on {{Data cleaning objective}} ONLY. NO EXPLANATIONS.
                             Example Return: column 1 """
        context, sel_col = generate(prompt_sel_col, context, log_f)
        while sel_col not in av_cols:
            prompt_regen = f"""The selected columns are not in {av_cols}. Please regenerate column name for TASK I."""
            context, sel_col = generate(prompt_regen, context, log_f)
        print(sel_col)

        # TASK II: select operations 
        prompt_sel_ops = "TASK II: Step by step, learn available python functions to process data in class RefineProject:" + prep_learning
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
        
        func_pool = ["split_column", "add_column", "text_transform", "mass_edit", "rename_column", "remove_column"]
        context, sel_op = generate(prompt_sel_ops, context, log_f)
        print(f"selected operation is {sel_op}")
        sel_op = sel_op.strip('`')
        
        while sel_op not in func_pool:
            prompt_regen = f"""The selected operation is not found in {functions_list}. Please regenerate function name for TASK II."""
            context, sel_op = generate(prompt_regen, context, log_f)
            sel_op = sel_op.strip('`')

        # TASK III: Learn operation arguments (share the same context with sel_op)
        args = get_function_arguments('call_or.py', sel_op)
        args.remove('project_id')  # No need to predict project_id
        args.remove('column')
        prompt_sel_args = f"""Next predicted operation is {sel_op}"""
        # prompt_sel_args += f"Sample first 30 rows from the Intermediate Table: {gen_table_str(df)} \n"
        with open(f'prompts/{sel_op}.txt', 'r') as f1:
            sel_args_learn = f1.read()
        prompt_sel_args += f"""TASK III: Step by step, learn proper arguments based on intermediate table and data cleaning purpose:
                                {sel_args_learn}"""
        prompt_exp_lr = f"""
                        You are a professional python developer and can write a function to transform the data in proper
                        format. With the selected function and examples, please write a proper python function. 
                        """
        if sel_op == 'split_column':
            prompt_sel_args += f"""
                                Therefore, the answer is: split_column(column=, separator=?).
                                column SHOULD BE {sel_col}. What's the separator?
                                ONLY generate value for {{separator}}. 
                                """
            context, sep = generate(prompt_sel_args, context, log_f)
            sel_args= {'column':sel_col, 'separator':sep}
            split_column(project_id, **sel_args)
        elif sel_op == 'add_column':
            # prompt_sel_args += prompt_exp_lr
            prompt_sel_args += f"""
                                Therefore, the answer is: add_column(column=, expression=?, new_column=? ).
                                column SHOULD BE {sel_col}. 
                                Return format: A dictionary of expression and new_column.
                                No explanations.
                                """
            context, res_dict = generate(prompt_sel_args, context, log_f)
            while not isinstance(res_dict, dict):
                prompt_sel_args += f"""Return format is incorrect, it should be a dictionary, keys: expression and new_column,
                                       Please regenerate the correct values for the provided keys."""
                context, res_dict = generate(prompt_sel_args, context, log_f)
            sel_args = {'column': sel_col}.update(res_dict) 
            add_column(project_id, **sel_args)
        elif sel_op == 'rename_column':
            prompt_sel_args += f"""
                                Therefore, the answer is: rename_column(column=, new_column=?).
                                column SHOULD BE {sel_col}. What's the new_column?
                                ONLY generate value for new_column. 
                                """
            context, new_col = generate(prompt_sel_args, context, log_f)
            sel_args = {'column': sel_col, 'new_column': new_col}
            rename_column(project_id, **sel_args)
        elif sel_op == 'text_transform':
            prompt_sel_args += prompt_exp_lr
            prompt_sel_args += f"""
                                Therefore, the answer is: text_transform(column=,expression=?). 
                                column SHOULD BE {sel_col}. What's the expression?
                                ONLY generate python code for expression.
                                """
            context, exp = generate(prompt_sel_args, context, log_f)
            format_exp = extract_exp(exp)
            print(format_exp)
            while format_exp is False:
                print('regenerate....')
                context, exp = generate(prompt_sel_args, context, log_f)
                format_exp = extract_exp(exp)
                print('end')
            sel_args = {'column': sel_col, 'expression': f"{format_exp}"}
            text_transform(project_id, **sel_args)
        elif sel_op == 'mass_edit':
            prompt_sel_args += f"""
                                Therefore, the answer is: mass_edit(column=, edits=[?]).
                                column SHOULD BE {sel_col}. What's the edits?
                                ONLY generate value for the edits. 
                                """
            context, edits = generate(prompt_sel_args, context, log_f)
            sel_args = {'column': sel_col, 'edits': edits}
            mass_edit(project_id, **sel_args)
        elif sel_op == 'remove_column':
            prompt_sel_args += f"""
                                Therefore, the answer is: remove_column(column=).
                                column SHOULD BE {sel_col}. 
                                """
            sel_args = {'column': sel_col}
            remove_column(project_id, **sel_args)
        elif sel_op == "reorder_rows":
            prompt_sel_args += f"""
                                Therefore, the answer is: reorder_rows(sort_by=?).
                                Sort by which column?
                                ONLY generate value for sort_by. 
                                """
            context, sort_col = generate(prompt_sel_args, context, log_f)
            sel_args = {'sort_by': sort_col}
            reorder_rows(project_id, **sel_args)
       
        with open("prompts/full_chain_demo.txt", 'r')as f2:
            full_chain_learn = f2.read()
        prompt_full_chain = "Learn when to generate {{True}} for eod_flag and end the data cleaning operations generation:\n" + full_chain_learn
        
        # Re-execute intermediate table
        cur_df = export_intermediate_tb(project_id)
        prompt_init_prov = f""" Understanding how the selected operation and arguments perform on the dataset is important
                            for we will understand how the changes applied by the operation and whether this operation improve the
                            data quality to meet cleaning objectives. 
                            """
        changes = diff_check(sel_op, df, cur_df, sel_col)
        print(f"*********{changes}********")
        prompt_changes = prompt_init_prov + changes\
                         + sel_args_learn + __op
        # EOD Flag I: Does the selected operation perform correctly on the dataset?
        context, eod_flag1 = generate(prompt_changes, [], log_f)
        print(f"LLMs believe the operation is correctly applied: {eod_flag1}")

        # TASK V:
        # Keep passing intermediate table and data cleaning objective, until eod_flag is True. End the iteration.
        iter_prompt = prompt_full_chain + dc_obj + f""" intermediate table:{cur_df} """\
                      + __eod
                            # + exp_in_out \
   
        context, eod_flag2 = generate(iter_prompt, [], log_f)
        print(f'LLMs believe current table is good enough to address objectives: {eod_flag2}')
        eod_flag = eod_flag1 and eod_flag2
        print(eod_flag)

    # prompt += "Learn how to generate arguments for operation add column: \n" + 
    log_f.close()
