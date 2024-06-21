# data_cleaning_exp
<!-- 1. Data Profiling for Systematically Evaluate Data Quality
2. Transparent Data Cleaning
3. Reusable Data Cleaning Framework -->

## History Update Problem
Experiment I:
- [Process Document](history_update_problem/openrefine_recipes_gen.md)

Experiment II:
- LLM-based workflow analysis 
- Chain-of-Table Prompts



## LLM-based Data Cleaning 
_Pipeline:__
1. Run llm_dc.py
- [data input](pd_exp_prep/data_input/menu.csv)
- prompt types:
[1].zero_shot: data cleaning objectives, requirements
[2].example_based: data cleaning objectives, example repairs, requirements
[3].example_sample:  data cleaning objectives, example repairs, sample rows, requirements
[4].profile_example_sample: data cleaning objectives, example repairs, sample rows, profiling results, requirements
- For each type of prompt, log LLM's responses:
-- [zero_shot](llm_res/zero_shot.txt)
-- [example_based](llm_res/exp.txt)
-- [example_sample](llm_res/exp_samp.txt)
-- [profile_example_sample](llm_res/prof_exp_samp.txt)

2. Check the python scripts from LLM's responses
**Question: How does the quality of response reflect the quality of the prompt?**