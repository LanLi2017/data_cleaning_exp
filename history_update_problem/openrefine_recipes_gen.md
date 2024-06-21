**Preparation: History Update Problem**
1. **Run** update_recipe_main.py on menu.csv:
- Generate a random sample data input: 100 rows
- data.in/menu_sp.csv

2. **Load** data.in/menu_sp.csv to _OpenRefine_：
Iteratively:

2.1 Complete a finalized clean version dataset as ground truth: ground.truth.init/menu_gd_init.csv

2.2 method 1, method 2, method 3, ... method 6 reflects the modifying process:
_Note: The differences between each method are documented in trace/doc_step.csv file._
- six versions of data outputs are saved in data.out/*.csv
- six versions of recipes are saved in 
recipes/*.json
- six versions of projects files are saved in:
openrefine.project.files/*.tar.gz

3. **Run** update_recipe_main.py:
_process_dq_matrix_: compare six versions data outputs with ground truth, return data quality matrix: {accuracy, completeness}
- Save the matrix: data.quality.matrix/ev_matrix.csv