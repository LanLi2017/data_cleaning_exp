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
Function Chain: f_add_column(Attendance number, f_row[*]) -> f_split_column(When, f_row[*]) -> f_sort_column(Attendance number, f_row[*]) ->  -> <END>
"""
plan_select_column_demo = '''If the table only needs a few columns to answer the question, we use f_select_column() to select these columns for it. For example,
/*
col : Code | County | Former Province | Area (km2) | Population | Capital
row 1 : 1 | Mombasa | Coast | 212.5 | 939,370 | Mombasa (City)
row 2 : 2 | Kwale | Coast | 8,270.3 | 649,931 | Kwale
row 3 : 3 | Kilifi | Coast | 12,245.9 | 1,109,735 | Kilifi
*/
Question: what is the total number of counties with a population higher than 500000?
Function: f_select_column(County, Population)
Explanation: The question asks about the number of counties with a population higher than 500,000. We need to know the county and its population. We select column "County" and column "Population".'''

plan_add_column_demo = '''To answer the question, we can first use f_add_column() to add more columns by applying transformations, similar to f_trans_column() to the table.

    /*
    col : week | when | kickoff | opponent | results; final score | results; team record | game site | attendance
    row 1 : 1 | saturday, april 13 | 7:00 p.m. | at rhein fire | w 27–21 | 1–0 | rheinstadion | 32,092
    row 2 : 2 | saturday, april 20 | 7:00 p.m. | london monarchs | w 37–3 | 2–0 | waldstadion | 34,186
    row 3 : 3 | sunday, april 28 | 6:00 p.m. | at barcelona dragons | w 33–29 | 3–0 | estadi olímpic de montjuïc | 17,503
    */
    Purpose: Return top 5 competitions that have the most attendance.
    Function: f_add_column(attendance number, f_row[*])
    Explanation: We copy the value from column "attendance" and create a new column "attendance number" for each row: f_row[*].
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


def gen_table_str(fp):
    # generate sample table string as the task input [intermediate table]
    df = pd.read_csv(fp, index_col=None)
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
    dc_obj = "what's the most occurred page count for the menus?"
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
    prompt = init_demo + '\n'
    with open(f'CoT.response/llm_dcw.txt', 'w')as log_f:
            # 1. LLM predict next operation: five op-demo and chain-of ops 
            fname = "menu_llm.csv"
            data_input = gen_table_str(fpath) # generate intermediate table (T)
            # TASK I: select target column(s)
            with open("prompts/f_select_column.txt", 'r')as f:
                sel_col_learn = f.read()
            prompt += "Learn how to select columns based on given question:\n" + sel_col_learn
            sel_col_tb = format_sel_col(fpath)
            prompt += "Table input:\n" + json.dumps(sel_col_tb)
            prompt += f"Purpose I: {dc_obj} \n"
            prompt += f"Please infer the column(s) that is related to the Purpose I (No explanatins, only the column name(s))"
            prompt += "The answer is : \n"
            context = generate(prompt, context, log_f)
    

    # TASK II: get_certain_columns(table_str: str, columns: list[str])
    # while not flag_ops['E']:
        #   prompt += "Intermediate Table:\n" + data_input
        #   prompt += f"Chain of operation history has been applied: {ops} ->\n"
        #   prompt += f"Data cleaning purpose: {dc_obj}"
    #     prompt += "Learn operation add column:\n" + plan_add_column_demo
        # prompt += "Learn operation split column:\n" + plan_split_column_demo
        # prompt += "Learn operation rename column:\n" + plan_rename_column_demo
        # prompt += "Learn operation transform column:\n" + plan_transform_column_demo
        # prompt += "Learn operation sort column:\n" + plan_sort_column_demo
        # prompt += "operations pool: add_col, split_col, rename_col, transform_col, sort_col, E \n"
        # prompt += "choose one operation from the operations pool, and return the operation name"
            


        
        # 2. LLM generate required arguments 
        # prompt += "Learn how to generate arguments for operation add column: \n" + 
