# LLM-based history update solution
import argparse
import requests
import json

import pandas as pd


model = "llama3"
parser = argparse.ArgumentParser()
parser.add_argument("--start", required=True, type=int)
parser.add_argument("--end", required=True, type=int)
parser.add_argument("--dry_run", default=False, action="store_true",
    help="whether it's a dry run or real run.")
parser.add_argument(
    "--temperature", type=float, default=0.7,
    help="temperature of 0 implies greedy sampling.")
# simple case: How many types of event in the menu table?
prep_learning = """
Here is a python script calling OpenRefine API to do the data cleaning, multiple functions/transformations are listed. 
The file path is py_scripts/refine.py. Find and read this script to learn the functions. 
"""
# 0. LLM learn generate chain of data operations as a data cleaning workflow
init_demo = """
Here are examples of using the operations to address data cleaning purpose.
/*
col : Week | When | Kickoff | Opponent | Results; Final score | Results; Team record | Game site | Attendance
row 1 : 1 | Saturday, April 13 | 7:00 p.m. | at Rhein Fire | W 27–21 | 1–0 | Rheinstadion | 32,092
row 2 : 2 | Saturday, April 20 | 7:00 p.m. | London Monarchs | W 37–3 | 2–0 | Waldstadion | 34,186
row 3 : 3 | Sunday, April 28 | 6:00 p.m. | at Barcelona Dragons | W 33–29 | 3–0 | Estadi Olímpic de Montjuïc | 17,503
*/
Purpose: what is the date of the competition with top 5 highest attendance?
Function Chain: f_add_column("Attendance number", f_row[*]) -> f_split_column("When", f_row[*]) -> f_sort_column("Attendance number", f_row[*]) ->  -> <END>
"""
plan_select_column_demo = '''If the table only needs a few columns to answer the question, we use f_select_column() to select these columns for it. For example,
/*
col : Code | County | Former Province | Area (km2) | Population | Capital
row 1 : 1 | Mombasa | Coast | 212.5 | 939,370 | Mombasa (City)
row 2 : 2 | Kwale | Coast | 8,270.3 | 649,931 | Kwale
row 3 : 3 | Kilifi | Coast | 12,245.9 | 1,109,735 | Kilifi
*/
Question: what is the total number of counties with a population higher than 500000?
Answer: County, Population
Explanation: The question asks about the number of counties with a population higher than 500,000. We need to know the county and its population. We select column "County" and column "Population".'''

plan_add_column_demo = '''To answer the question, we can first use f_add_column() to add more columns by applying transformations, similar to f_trans_column() to the table.

    /*
    col : week | when | kickoff | opponent | results; final score | results; team record | game site | attendance
    row 1 : 1 | saturday, april 13 | 7:00 p.m. | at rhein fire | w 27–21 | 1–0 | rheinstadion | 32,092
    row 2 : 2 | saturday, april 20 | 7:00 p.m. | london monarchs | w 37–3 | 2–0 | waldstadion | 34,186
    row 3 : 3 | sunday, april 28 | 6:00 p.m. | at barcelona dragons | w 33–29 | 3–0 | estadi olímpic de montjuïc | 17,503
    */
    Purpose: Which five competitions have the most attendance?
    Function: f_add_column("attendance number", f_row[*])
    Explanation: We copy the value from column "attendance" and create a new column "attendance number" for each row: f_row[*].
    '''
plan_sort_column_demo = '''If the purpose is about the order of items in a column, we use f_sort_column() to sort the items. For example,
    
    /*
    col : position | club | played | points
    row 1 : 1 | malaga cf | 42 | 79
    row 10 : 10 | cp merida | 42 | 59
    row 3 : 3 | cd numancia | 42 | 73
    */
    Purpose: Which club placed in the last position?
    Function: f_sort_column("position", f_row[*])
    Explanation: Sort the rows from column position to know the order of position from last to front.
    '''

plan_split_column_demo = ''' If the purpose is to extract partial cell values from the original values, we use f_split_column() to decompose cell values. For example,

    /*
    col : Week | When | Kickoff | Opponent | Results; Final score | Results; Team record | Game site | Attendance
    row 1 : 1 | Saturday, April 13 | 7:00 p.m. | at Rhein Fire | W 27–21 | 1–0 | Rheinstadion | 32,092
    row 2 : 2 | Saturday, April 20 | 7:00 p.m. | London Monarchs | W 37–3 | 2–0 | Waldstadion | 34,186
    row 3 : 3 | Sunday, April 28 | 6:00 p.m. | at Barcelona Dragons | W 33–29 | 3–0 | Estadi Olímpic de Montjuïc | 17,503
    */
    Purpose: What is the date of the competition with highest attendance?
    The existing columns are: "Week", "When", "Kickoff", "Opponent", "Results; Final score", "Results; Team record", "Game site", "Attendance".
    Function: f_split_column("When",",", f_row[*])
    Explanation: Split the value from all rows in column "When" with separator "," to extract date values.
    '''

plan_rename_column_demo = '''If the column name is not meaningful, we use f_rename_column() to revise current one. We call f_rename_column() to revise the column name.

/*
col : Code | County | Former Province | Area (km2) | Population; Census 2009 | Capital
row 1 : 1 | Mombasa | Coast | 212.5 | 939,370 | Mombasa (City)
row 2 : 2 | Kwale | Coast | 8,270.3 | 649,931 | Kwale
row 3 : 3 | Kilifi | Coast | 12,245.9 | 1,109,735 | Kilifi
*/
Purpose: What is the total number of counties with a population in 2009 higher than 500,000?
Function: f_rename_column("Population; Census 2009", "Population", f_row[*])
Explanation: Rename the column "Population; Census 2009" as "Population" to address the purpose.'''

plan_transform_column_demo = '''Using f_trans_column() to apply function (python code or GREL(General Refine Expression Language)) to transform the data values in correct format.

/*
col : code | county | former province | area (km2) | population; census 2009 | capital
row 1 : 1 | mombasa | coast | 212.5 | 939,370 | mombasa (city)
row 2 : 2 | kwale | coast | 8,270.3 | 649,931 | kwale
row 3 : 3 | kilifi | coast | 12,245.9 | 1,109,735 | kilifi
*/
Purpose: Which place that has a population in 2009 higher than 500,000.
Function: f_trans_column("population; census 2009", "value.toNumber()", f_row[*])
Explanation: We use GREL expression: toNumber() to transform the cell values from column "population; census 2009" into numerical type for further analysis.
'''


def format_sel_col(fp):
    table_caption = "A mix of simple bibliographic description of the menus"
    df = pd.read_csv(fp)
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


def gen_arguments():
    
    pass


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

    for line in r.iter_lines():
        body = json.loads(line)
        response_part = body.get('response', '')
        # the response streams one token at a time, print that as we receive it
        # print(response_part, end='', flush=True)
        log_f.write(response_part)

        if 'error' in body:
            raise Exception(body['error'])

        if body.get('done', False):
            return body['context']
        

if __name__ == "__main__":
    dc_obj = "What is the menu id with the most number of page count?"
    fpath = "data.in/menu_llm.csv"
    ops = [] # operation history 
    
    flag_ops = {
        "add_col": False,
        "E": False,
        # "split_col":False,
        # "rename_col":False,
        # "transform_col":False,
        # "sort_col":False,
    }
    # facet/select_row should be an argument for all the operations 
    context = []
    llm_col_fp = 'CoT.response/llm_col_name.txt'
    llm_op_fp = 'CoT.response/llm_op_name.txt'
    with open(llm_col_fp, 'w')as log_f:
            # 1. LLM predict next operation: five op-demo and chain-of ops 
            # TASK I: select target column(s)
            with open("prompts/f_select_column.txt", 'r')as f:
                sel_col_learn = f.read()
            prompt = "Learn how to select columns based on given question:\n" + sel_col_learn
            sel_col_tb = format_sel_col(fpath)
            prompt += "Table input:\n" + json.dumps(sel_col_tb)
            prompt += f"Print one or more column names that are related to the {dc_obj} (No explanatins, only the column name(s)). If multiple columns are used, use comma to list them."
            prompt += "The answer is : \n"
            context = generate(prompt, context, log_f)

    # TASK II: get_certain_columns(table_str: str, columns: list[str])
    data_input = gen_table_str(fpath, llm_col_fp) # generate intermediate table (T)
    # TASK III: LLM-based data cleaning workflow generation 
    sel_rows_fp = "prompts/f_row.txt"
    while not flag_ops['E']:
        # 1. Learn operations demo
        prompt = "Learn operation add column:\n" + plan_add_column_demo
        prompt += "Learn operation split column:\n" + plan_split_column_demo
        prompt += "Learn operation rename column:\n" + plan_rename_column_demo
        prompt += "Learn operation transform column:\n" + plan_transform_column_demo
        prompt += "Learn operation sort column:\n" + plan_sort_column_demo
        prompt = init_demo + '\n'
        prompt += "operations pool: f_add_col, f_split_col, f_rename_col, f_transform_col, f_sort_col, E \n"
        prompt += f"Chain of operation history has been applied: {ops} ->\n"
        prompt += "Intermediate Table:\n" + data_input
        prompt += f"Data cleaning purpose: {dc_obj}"
        prompt += "generate next operation from the operations pool, and return the operation name ONLY (NO explanation)"
        with open(llm_op_fp, 'w')as log_f1:
            context = generate(prompt, context, log_f1)
        # 2. LLM generate required arguments 
        # determine the rows, f_rows[] first.
        with open(sel_rows_fp, "r")as f_row:
            sel_row_learn = f_row.read()
        prompt = "Learn operation select rows:\n" + sel_row_learn
        # prompt += "Learn how to generate arguments for operation add column: \n" + 
