import argparse
from pprint import pprint

from ORMA.extra_info import generate_recipe
from ORMA.orma import cluster_main, get_schema_list, split_recipe, translate_operator_json_to_graph
from metadata_ops import exe_enhanced_recipe


# Given step id, return the edge_in, edge_out pairs
def find_edges(graph:dict, step_id):
    res = []
    for k,v in graph.items():
        if step_id == v:
            res.append(k)
    return res 


# Given dependent columns, find corresponding probamatic step id(s)
def find_prob_steps(step_edge, log_w, dependents:list):
    step_ids = []
    for dependent in dependents:
        par_col, *chi_cols = dependent
        for child in chi_cols:
            log_w.write(f'Column {child} depends on Column {par_col} \n')
            for k,v in step_edge.items():
                if child in k:
                    step_ids.append(v)
                    log_w.write(f'Probamatic steps: {v}--{k} \n')
    res = list(set(step_ids))
    return res

# Detect linked nodes
def dfs(graph, u):
    visited_nodes = [u]
    try:
        for v in graph[u]:
            visited_nodes += dfs(graph, v)
    except KeyError:
        pass
    return visited_nodes

    
def refine_graph(edges):
    new_graph = {}
    step_id_of_edge = {}
    for edge in edges:
        u = edge['from']
        len_u = len(u)
        v = edge['to']
        len_v = len(v)
        if len_u == 1 and len_v == 1:
            u = u[0]['label']
            v = v[0]['label']
            new_graph.setdefault(u, []).append(v)
            k = {(u,v): edge['step_id']}
            step_id_of_edge.update(k)
        elif len_v > 1:
            u = u[0]['label']
            for output in v:
                new_graph.setdefault(u, []).append(output['label'])
                k = {(u, output['label']): edge['step_id']}
                step_id_of_edge.update(k)
        elif len_u > 1:
            v = v[0]['label']
            for input_node in u:
                new_graph.setdefault(input_node['label'], []).append(v)
                k = {(input_node['label'], v): edge['step_id']}
                step_id_of_edge.update(k)

    step_edge = dict(sorted(step_id_of_edge.items(), key=lambda item: item[1]))
    return new_graph, step_edge


def update_ops():
    pass


def delete_ops(del_id, graph, step_edge, f):
    f.write(f"\n Delete step {del_id} \n")
    edges = find_edges(step_edge, del_id)
    flag_cols = []
    col_input = []
    for edge in edges:
        col_input.append(edge[0])
        flag_cols.append(edge[1])
    f.write(f'Column input on step {del_id} -- {list(set(col_input))} \n')
    f.write(f"Affected columns on step {del_id} -- {flag_cols} \n")
    # Principle-of-Deletion: remove all downstream operations that depend on flag_cols
    dependent_cols = []
    for col in flag_cols:
        dependent_cols.append(dfs(graph, col))
    steps = find_prob_steps(step_edge, f, dependent_cols)
    f.write(f'As a result, the affected steps: {steps}')
    return steps 


def insert_ops():
    pass


def locate_ops(clusters:list, step_id: int):
    # Split the recipe into modules
    # Locate the changed operations in the module 
    for cluster in clusters:
        if step_id in cluster:
            return cluster, cluster.index(step_id)


def prep_graph(project_id, recipe_path=None):
    # process(2406142890441, 5, cmd='delete')
    """
    use edge information to represent the purpose...
    """
    recipe, schema_info = exe_enhanced_recipe(project_id, recipe_path)
    schemas = get_schema_list(schema_info)
    orma_data = translate_operator_json_to_graph(recipe, schemas)
    new_edges = []
    steps = []
    for graph in orma_data:
        steps.append(graph.step_index)
        new_edges += [{'from': graph.in_node_names, 
                        'to': graph.out_node_names,
                        'step_id': graph.step_index}]
    recipe_length = max(steps)
    seq_list = [i + 1 for i in range(recipe_length)]
    invalid_steps = [x for x in seq_list if x not in steps]
    new_graph, step_edge = refine_graph(new_edges)
    return new_graph, step_edge, recipe_length, invalid_steps


def process(mod_id, project_id=2221256614441, cmd=None, 
            recipe_path = "recipes/enhanced_orma/alice.json"):
    """
    #@params step id: operation in a recipe
    #@params mod id: operation in a modular 
    """

    FUNCTION_MAP = {
        'delete': delete_ops,
        'update': update_ops,
        'insert': insert_ops
    }
    # User input step idx they want to modify
    # Return Failed Operations 
    func = FUNCTION_MAP[cmd]
    refine_graph, step_edge, rep_len, invalid_ids = prep_graph(project_id, recipe_path)
    # clusters = split_recipe(enhanced_recipe, schemas)
    # modular, mod_id = locate_ops(clusters, step_id) # return component and step id in component
    logging_f = open('log.txt', 'a')
    if mod_id == rep_len:
        logging_f.write(f'\n\n Removing the last step: step-{mod_id} \n')
    elif mod_id > rep_len:
        print("\n\n Modify Step Id is over than the operation history length", IndexError)
    elif mod_id in invalid_ids:
        logging_f.write(f"\n\n Removing step-{mod_id}: not recorded in the recipe; \n")
    else:
        func(mod_id, refine_graph, step_edge, logging_f)


if __name__ == '__main__':
    # prep_graph()
    process(mod_id=8, cmd='delete')