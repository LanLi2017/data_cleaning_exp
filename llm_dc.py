from pprint import pprint
from langchain.llms import Ollama
import pandas as pd 
import json
import requests
import re
import difflib

from data_profiling.profiler import phrase_detect, word_occur

model = "llama3"
# model = 'stablelm-zephyr'

# Training LLM EXP:
# 1. init: zero shot
# 2. Example repair
# 3. Example repair + Sample data
# 4. Example repair + Sample data + Profiler 

"""Try to define representative repairs:
1. vocabulary control: fold,folded; in., inches
2. composite/singular size
3. information extraction: digitsXdigits might distribute to everywhere
4. from fraction to float
5. punctuations alter"""
example_repair = \
{
"8 x 5 in. fold. ; ill.": "8 x 5 inches folded",
"BROADSHEET; COL; ILLUS; 10.25 X 9.5;": "10.25 X 9.5",
"30x22.5cm folded; 30x45cm open": "30x22.5cm folded;30x45cm open",
"CARD; 5 X 8; ILLUS;": "5 X 8",
"28x21.5cm; digitize copy 1": "28x21.5cm",
"CARD; ILLUS; COL; 4/75X7.25;": "4.75X7.25",
"8 1/2 x 5 1/2 in. fold. ; ill.": "8.5 x 5.5 inches folded",
"CARD; ILLUS; COL; 5,25X8;": "5.25X8"
}
dc_obj = \
{
    "data input": "a column of composite values expressing physical description of menus: such as card types,\
        card color, and size information are expressed as digit X digit or digit x digit.",
    "data output": "extract size information from this target column physical_description.",
    "requirement": "Must follow the required format: 1.singular: digit x digit; 2. composite: a pair of digits \
        multiplication with key words. Key words: folded, open, unit measurement(cm, inches)."
}
# def extract_content_from_file(content):
#     # Regular expression to match [label]...[/label] blocks
#     pattern = re.compile(r'\[(.*?)\](.*?)\[\/(.*?)\]', re.DOTALL)

#     # Find all matches
#     matches = pattern.findall(content)
#     res = []
#     for match in matches:
#         res.append(' '.join(match).strip())
#     return res


# def prep_data(cell_values):
#     # Add <bos> <eos> token for each cell
#     cells_prep = []
#     for cell in cell_values:
#         cells_prep.append(f'bos {cell} eos')
#     return cells_prep

# Function to find closest match for a word in the primer list
def find_closest_match(word, primer_list):
    matches = difflib.get_close_matches(word, primer_list, n=1, cutoff=0.66)
    if matches:
        return matches[0]
    return None


def prep_profiler(df, target_col):
    """Profile result
    1. word and occurrances
    2. phrase (2Gram)
    #@primer: Sort the word_occur
    #@Control vocab: A bag of outliers similar to primer
    """
    primers = ["cm", "inches", "folded", "open"]
    # Count word occurance
    word_count = word_occur(df[target_col])
    words_list = list(word_count.keys())
    
    # Iterate over each word
    outliers = {}
    for word in words_list:
        matched_primer = find_closest_match(word, primers)
        if matched_primer:
            if matched_primer not in outliers:
                outliers[matched_primer] = []
            outliers[matched_primer].append(word)
    return outliers


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


# def prompt_ppl():
#     #archived
#     df = pd.read_csv('data_quality_exp/pd_experiments/data_input/menu.csv')
#     df_prep = df.dropna(subset=['physical_description'])
#     # Sample 1000 rows
#     df_sampled = df_prep.sample(n=1000, random_state=42)
#     prompt_parent = 'prompt'
#     # prompt_f = 'prompt_init.txt' # zero shot 
#     # prompt_f = 'prompt_exp_no_samples.txt' # few shots 
#     prompt_f = 'prompt_exp_samples.txt' # few shots 
#     with open(f'{prompt_parent}/{prompt_f}', 'r')as pf:
#         content = pf.read()
#         # Extract content from the text file
#         prompts = extract_content_from_file(content)
#     prompts_data = prompts + [f"Sample cells values from target column:{df_sampled['physical_description']}"] + [""]
#     # prompts_data = prompts + [""]


def main():
    raw_data = 'pd_exp_prep/data_input/menu.csv'
    target_col = 'physical_description'
    df = pd.read_csv(raw_data)
    df_prep = df.dropna(subset=[target_col])
    # Sample 100 rows
    df_sampled = df_prep.sample(n=100, random_state=42) 
    
    # prompt I: dc_obj
    zero_v = {**dc_obj}

    # prompt II: dc_obj + example
    exp_v =  {"example repair": example_repair}
    exp_v.update(dc_obj)

    # prompt III: dc_obj + example repair + sample data
    exp_samp_value = {**exp_v}
    exp_samp_value['Sample cell values in target column']= list(df_sampled[target_col])

    # prompt IV: dc_obj + example repair + sample data + profiler
    prof_results = prep_profiler(df, target_col)
    exp_samp_prof = {**exp_samp_value}
    prof_intro = {"control vocabulary(key-[value] pairs) as following": \
                  "key is the correct spelling, value is potential outliers. If encounter the outliers, replace value with the given key",
                  **prof_results}
    
    fp_prompts = {
        'zero_shot': [zero_v, ""],
        'exp': [exp_v, ""],
        'exp_samp': [exp_samp_value,
                       ""]
                       ,
        'prof_exp_samp': [exp_samp_prof, prof_intro, ""]
    }
    for fp, prompts in fp_prompts.items():
        with open(f'llm_res/{fp}.txt', 'w')as log_f:
            i = 0
            context = []
            while i < len(prompts):
                print(i)
                if i == len(prompts)-1:
                    user_input = "Write a python script to extract size information from this target column. \
                                Dataset input: `menu.csv`. The target column name is `physical_description`.\
                                Create a new column `size`: \
                                1. Format the data according to requirement. \
                                2. Learn from example repair (if provided) and create function to standardize cell value.\
                                3. Generalize repairing methods according to provided sample cell values (if provided). \
                                4. Using control vocabulary (if provided) to repair outliers."

                else:
                    user_input = json.dumps(prompts[i])
                print(user_input)
                context = generate(user_input, context, log_f)
                print()
                i += 1


if __name__ == '__main__':
    # try_prof()
    main()
