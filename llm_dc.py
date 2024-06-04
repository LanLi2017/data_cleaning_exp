from pprint import pprint
from langchain.llms import Ollama
import pandas as pd 
import json
import requests
import re

# model = "llama3"
model = 'stablelm-zephyr'
# llm = Ollama(model="llama3")
# res = llm.predict(input)
# print (res)

def extract_content_from_file(content):
    # Regular expression to match [label]...[/label] blocks
    pattern = re.compile(r'\[(.*?)\](.*?)\[\/(.*?)\]', re.DOTALL)

    # Find all matches
    matches = pattern.findall(content)
    res = []
    for match in matches:
        res.append(' '.join(match).strip())
    print(res)
    return res


def prep_data(cell_values):
    # Add <bos> <eos> token for each cell
    cells_prep = []
    for cell in cell_values:
        cells_prep.append(f'bos {cell} eos')
    return cells_prep


def generate(prompt, context, log_f):
    r = requests.post('http://localhost:11434/api/generate',
                      json={
                          'model': model,
                          'prompt': prompt,
                          'context': context,
                      },
                      stream=True)
    r.raise_for_status()

    for line in r.iter_lines():
        body = json.loads(line)
        response_part = body.get('response', '')
        # the response streams one token at a time, print that as we receive it
        print(response_part, end='', flush=True)
        log_f.write(response_part)

        if 'error' in body:
            raise Exception(body['error'])

        if body.get('done', False):
            return body['context']

def main():
    df = pd.read_csv('data_quality_exp/pd_experiments/data_input/menu.csv')
    df_prep = df.dropna(subset=['physical_description'])
    # Sample 1000 rows
    df_sampled = df_prep.sample(n=1000, random_state=42)
    prompt_parent = 'prompt'
    prompt_f = 'prompt_init.txt'
    with open(f'{prompt_parent}/{prompt_f}', 'r')as pf:
        content = pf.read()
        # Extract content from the text file
        prompts = extract_content_from_file(content)
    prompts_data = prompts + [f"Sample cells values from target column:{df_sampled}"] + [""]
    context = []
    i = 0
    log_f = open(f'llm_res/{prompt_f}', 'w')
    while i < len(prompts_data):
        if i == len(prompts_data)-1:
            user_input = "Write a python script to extract size information from this target column. "
        else:
            user_input = prompts_data[i]
        print(user_input)
        context = generate(user_input, context, log_f)
        # log_f.write(str(context)+'\n')
        print()
        i += 1


if __name__ == '__main__':
    main()
