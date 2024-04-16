# ORMA is a model analysis based on OpenRefine JSON recipe
# It reveal dependencies between operations
# levels of operations based on affect :
'''
level 0: no change
level 1: only change content
level 2: only change dependency
level 3: both change dependency and content
'''
# version of data flow
import argparse
import json

# from extra_info import generate_recipe as gen_recipe
from graphviz import Digraph

from ORMA.extra_info import generate_recipe as gen_recipe
# from extra_info import generate_recipe as gen_recipe
# import all library needed for this class
import re
from collections import Counter
from pprint import pprint

_color_ = '#FFFFCC'  # default color for output node
_inNodeColor_ = '#FAFAF0'  # default color for input node
_process_color_ = '#CCFFCC'
# _level3_color_ = '#ffc04d'  # if the transformation is column-level
# _level0_color = '#D0D0D0'  # if the transformation is single-edit/ star row
_edge_color_ = '#000000'  # default edge color: black
_gen_val_color_ = '#f7ce8d'  # generic + value changed
_type_con_color_ = '#d4eafa'  # type convert color
_type_label_color_ = '#14697e'  # type convert label color
_custome_v_color = '#fbb8b8'  # customized value color
_gen_label_color_ = '#b06e04'  # generic + value label color
_remove_color_ = '#D0D0D0'  # color for removing cells

'''
if style: must label & edge color
if label: must edge color

'''


# output_color = '#CCFFCC'


class ORMAGraph:
    def __init__(self):
        # SQL
        self.history_id = 0
        self.step_index = 0
        self.out_node_names = []
        self.in_node_names = []
        self.process = []
        self.raw_operator = None
        self.edge = []  # from in_node_names -to-> process from process -to-> out_not_name
        self.level = None  # according to effect of operations, classify into three levels
        self.derived_columns = []
        self.d_edge = []  # save edges for derived columns


def extract_facet(operation):
    '''
    distinguish depends on & derived from
    find soft derivation from facet
    "engineConfig": {
      "facets": [
        {
          "type": "list",
          "name": "Zip",
          "expression": "value",
          "columnName": "Zip",
          "invert": false,
          "omitBlank": false,
          "omitError": false,
          "selection": [
            {
              "v": {
                "v": "96701",
                "l": "96701"
              }
            }
          ],
          "selectBlank": false,
          "selectError": false
        }
      ],
    :return: edge_type: use facet: True; without facet: False
    derived_columns: columns from facet [soft derivation]
    '''
    if 'engineConfig' in [*operation]:
        engineConfig = operation['engineConfig']
        facets = engineConfig['facets']
        derived_columns = []
        # if facets not empty => soft derivation exists
        if not facets:
            edge_type = False
            derived_columns = []
        else:
            # no soft derivation; type=False; default setting
            edge_type = True
            for facet in facets:
                derived_columns.append(facet['name'])
    else:
        edge_type = False
        derived_columns = []
    return edge_type, derived_columns


def deduplicate_d_columns(in_node_name: list, derived_columns: list):
    # delete the column name which is also the input nodes
    for in_node in in_node_name:
        in_col_name = in_node.split('.')[0]
        if in_col_name in derived_columns:
            # we need to delete this from derived columns
            derived_columns.remove(in_col_name)
        else:
            pass
    return derived_columns


def Update_columns(orma_data, derived_columns: list):
    # update derived column names with latest versions
    current_in_nodes = []
    for graph in orma_data:
        input_node_name = graph.in_node_names
        current_in_nodes.extend(input_node_name)  # includes all the input nodes with different version

    max_version_no = 0
    input_nodename_wo_version = []
    for input_node in current_in_nodes:
        col_name = input_node.split('.')[0]
        input_nodename_wo_version.append(col_name)
        if col_name in derived_columns:
            idx = derived_columns.index(col_name)
            # need to find the latest version of this column
            # and replace the one in derived columns list
            version_no = input_node.split('.')[1].split('v')[1]
            if version_no > max_version_no:
                max_version_no = version_no
                derived_columns[idx] = input_node
        else:
            pass

    # add version 0 if all columns are not in current input node names
    for d_col in derived_columns:
        if d_col not in input_nodename_wo_version:
            idx_ = derived_columns.index(d_col)
            derived_columns[idx_] = f'{d_col}.v0'
    return derived_columns


def merge_basename(operator):
    # two kinds of expressions :
    # 1. the column name has space: "grel:cells[\"Sponsor 2\"].value + cells[\"Sponsor 7\"].value"  : [A-Z]\w+ \d
    # 2. the column name does not have space: "grel:cells.name.value + cells.event.value" :   \.\w+\.
    #  normal one: "grel:value"
    exp = operator['expression']
    res = operator['baseColumnName']
    # if exp == 'grel:value':
    #     #      missing information here: if no merge other columns, we still do not know if the new column is set
    #     # --------dependency as basecolumnName
    #     result = res
    #     # print('value: {}'.format(result))
    #     return result
    if 'grel:if' in exp:
        try:
            exp = exp.split('grel:if')[-1].split('(')[-1].split(',')
            input_cols = []
            for pieces in exp:
                if re.findall('\.\w+\.', pieces):
                    result = re.findall('\.\w+\.', pieces)
                    for col in result:
                        input_cols.append(col[1:len(col) - 1])
                elif re.findall('[A-Z]\w+ \d', pieces):
                    result = re.findall('[A-Z]\w+ \d', pieces)
                    for col in result:
                        input_cols.append(col)
                else:
                    input_cols.append(res)
            return list(set(input_cols))
        except:
            return res
    else:
        if re.findall('\.\w+\.', exp):
            result = re.findall('\.\w+\.', exp)
            newm = []
            for col in result:
                newm.append(col[1:len(col) - 1])
            result = newm
            return result
        elif re.findall(r"(?<=cells\[')([^']+)(?='\]\.value)", exp):
            result = re.findall(r"(?<=cells\[')([^']+)(?='\]\.value)", exp)
            newm = []
            for col in result:
                newm.append(col)
            result = newm
            return result
        else:
            return res


# TASK 1: Create a modular_views of data cleaning workflow
# column-dependency view
def translate_operator_json_to_graph(json_data, schemas):
    orma_data = []
    nodes_num_about_column = Counter()

    def get_column_current_node(column_name):
        if column_name not in nodes_num_about_column:
            node_name = f'{column_name}.v0'
            nodes_num_about_column[column_name] += 1
            return node_name
        else:
            node_id = nodes_num_about_column[column_name]

            return f"{column_name}.v{node_id - 1}"

    def create_new_node_of_column(column_name):
        nodes_num_about_column[column_name] += 1
        return get_column_current_node(column_name)

    for i, operator in enumerate(json_data, start=1):
        graph = ORMAGraph()  # graph includes nodes and edges
        graph.raw_operator = operator
        graph.step_index = i
        graph.history_id = operator['id']
        # Type convert: toNumber/toDate
        # customize : cell-level/mass-edit
        # single-col: rename/remove
        # generic and multi-col/single-col: addition/split/transform
        if 'op' in [*operator]:
            if operator['op'] == 'core/column-addition':  # merge operation
                graph.process = [f'({i}) column-addition']
                basename = merge_basename(operator)

                # trap for basename
                # if len(basename) != 2:
                #     continue
                if isinstance(basename, list):
                    for col in basename:
                        graph.in_node_names += [
                            {'col_name': col, 'label': f'{get_column_current_node(col)}'}  # column name: label[unique]
                        ]

                else:
                    graph.in_node_names += [
                        {'col_name': basename, 'label': f'{get_column_current_node(basename)}'}
                    ]

                newcolumnName = operator['newColumnName']
                graph.out_node_names += [
                    {'col_name': newcolumnName, 'label': f'{create_new_node_of_column(newcolumnName)}',
                     'color': _gen_val_color_}
                ]

            elif operator['op'] == 'core/column-split':  # split operation
                column_name = operator['columnName']
                graph.process = [f'({i}) column-split']
                remove_original_col = operator['removeOriginalColumn']
                graph.in_node_names += [
                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                ]
                cur_schema = schemas[i]
                prev_schema = schemas[i - 1]
                new_cols = list(set(cur_schema) - set(prev_schema))
                for col in new_cols:
                    graph.out_node_names += [
                        {'col_name': col, 'label': f'{create_new_node_of_column(col)}', 'color': _gen_val_color_}
                    ]
                if remove_original_col:
                    remove_col = f'remove-{column_name}'
                    graph.out_node_names += [
                        {'col_name': remove_col, 'label': f'{create_new_node_of_column(remove_col)}',
                         'color': _remove_color_}
                    ]
                else:
                    pass
                    # graph.out_node_names += [
                    #     {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                    #      'color': _color_}
                    # ]

            elif operator['op'] == 'core/column-rename':  # split operation
                old = operator['oldColumnName']
                new = operator['newColumnName']
                graph.process = [f'({i}) column-rename']
                graph.in_node_names += [
                    {'col_name': old, 'label': f'{get_column_current_node(old)}'}
                ]
                graph.out_node_names += [
                    {'col_name': new, 'label': f'{create_new_node_of_column(new)}', 'color': _color_}
                ]

            elif operator['op'] == 'core/column-removal':
                graph.process = [f'({i}) removal']
                col = operator['columnName']
                lb_col = get_column_current_node(col)
                graph.in_node_names += [
                    {'col_name': col, 'label': f'{lb_col}'}
                ]
                # TODO which color?
                # port is needed to represent null
                new_col = f'remove-{col}'
                lb_new = create_new_node_of_column(new_col)
                graph.out_node_names += [
                    {'col_name': f'remove-{col}', 'label': f'{lb_new}', 'color': _remove_color_}
                ]

            elif operator['op'] == 'core/column-addition-by-fetching-urls':
                graph.process = [f'({i}) column addition-by-fetching-urls']
                base = operator['baseColumnName']
                new = operator['newColumnName']
                lb_base = get_column_current_node(base)
                lb_new = create_new_node_of_column(new)
                graph.in_node_names += [
                    {'col_name': base, 'label': f'{lb_base}'}
                ]
                graph.out_node_names += [
                    {'col_name': new, 'label': f'{lb_new}', 'color': _gen_val_color_}
                ]

            elif operator['op'] == 'core/multivalued-cell-join':
                graph.process = [f'({i}) multivalued-cell-join']
                col = operator['columnName']
                lb_col = get_column_current_node(col)
                graph.in_node_names += [
                    {'col_name': col, 'label': f'{lb_col}'}
                ]
                graph.out_node_names += [
                    {'col_name': col, 'label': f'{create_new_node_of_column(col)}', 'color': _color_}
                ]

            elif operator['op'] == 'core/transpose-columns-into-rows':
                graph.process = [f'({i}) transpose-columns-into-rows']
                start = operator['startColumnName']
                combine = operator['combinedColumnName']
                graph.in_node_names += [
                    {'col_name': start, 'label': f'{get_column_current_node(start)}'}
                ]
                graph.out_node_names += [
                    {'col_name': combine, 'label': f'{create_new_node_of_column(combine)}', 'color': _gen_val_color_}
                ]

            elif operator['op'] == 'core/row-removal':
                # row-level manipulation: 
                # The input should be the current column schema 
                # The output should be all the updated versions of columns
                # graph.process = [f'({i}) row-removal']
                cur_schema = schemas[i]
                for col in cur_schema:
                    graph.in_node_names += [
                        {'col_name': col, 'label': f'{get_column_current_node(col)}'}  # column name: label[unique]
                    ] 
                    graph.process.append([f'({i}) row-removal {col}']) 
                    graph.out_node_names += [
                         {'col_name': col, 'label': f'{create_new_node_of_column(col)}', 'color': _color_}
                    ]
                    # print(f"current operation is {sub_graph.process}")
                    # print(sub_graph.in_node_names)
                    # print(sub_graph.out_node_names)
            elif operator['op'] == 'core/column-move':
                index = operator['index']
                graph.process = [f'({i}) Move_to #{index}']
                column_name = operator['columnName']
                graph.in_node_names += [
                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                ]
                graph.out_node_names += [
                    {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}', 'color': _color_}
                ]
            elif operator['op'] == 'core/mass-edit':
                graph.process = [f'({i}) mass-edit']
                column_name = operator['columnName']
                graph.in_node_names += [
                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                ]
                graph.out_node_names += [
                    {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                     'color': _custome_v_color}
                ]
            elif operator['op'] == 'single_cell_edit':
                column_name = operator['columnName']
                desc = operator['description']
                row_number = operator['row']
                process = f'single_cell_edit row #{row_number}'
                graph.process = [f'({i}) {process}']
                graph.in_node_names += [
                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                ]
                graph.out_node_names += [
                    {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                     'color': _custome_v_color}
                ]
            elif operator['op'] == 'core/recon':
                graph.process = [f'({i}) reconciliation']
                column_name = operator['columnName']
                graph.in_node_names += [
                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                ]
                graph.out_node_names += [
                    {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                     'color': _custome_v_color}
                ]
            else:  # normal unary operation
                try:
                    column_name = operator['columnName']
                    if 'expression' in operator:
                        expression = operator['expression']
                        exp_preprocess = expression.split(".")[0]
                        if exp_preprocess == 'value':
                            graph.process = [f'({i}) .{expression.split(".")[-1]}']
                            if expression == 'value.toDate()':
                                graph.in_node_names += [
                                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                                ]
                                graph.out_node_names += [
                                    {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                                     'color': _type_con_color_}
                                ]
                            elif expression == 'value.toNumber()':
                                graph.in_node_names += [
                                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                                ]
                                graph.out_node_names += [
                                    {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                                     'color': _type_con_color_}
                                ]
                            else:

                                graph.in_node_names += [
                                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                                ]
                                graph.out_node_names += [
                                    {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                                     'color': _gen_val_color_}
                                ]
                        else:
                            # value change
                            exp = expression.split(':')[-1]
                            graph.process = [f'({i}) {exp}']
                            graph.in_node_names += [
                                {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                            ]
                            graph.out_node_names += [
                                {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                                 'color': _gen_val_color_}
                            ]
                    else:
                        opname = operator['op'].split('/')[-1]
                        graph.process = [f'({i}) {opname}']
                        graph.in_node_names += [
                            {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                        ]
                        graph.out_node_names += [
                            {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                             'color': _gen_val_color_}
                        ]
                        pass
                except KeyError:
                    continue
        else:
            description = operator['description'].split(' ')
            if 'column' in description:
                # single edit
                column_name = description[-1]
                desc = operator['description']
                row_number = desc.split(",")[0].split(" ")[-1]
                process = f'single_cell_edit row #{row_number}'
                graph.process = [f'({i}) {process}']
                graph.in_node_names += [
                    {'col_name': column_name, 'label': f'{get_column_current_node(column_name)}'}
                ]
                graph.out_node_names += [
                    {'col_name': column_name, 'label': f'{create_new_node_of_column(column_name)}',
                     'color': _custome_v_color}
                ]
            else:
                pass
        
        if len(graph.process) == 1:
            print(f'check input node: {graph.in_node_names}')
            graph.edge += [{'from': graph.in_node_names, 'to': graph.process},
                        {'from': graph.process, 'to': graph.out_node_names}]
            orma_data.append(graph)
        elif len(graph.process) > 1:
            processes = graph.process
            print(graph.in_node_names)
            # print(f'current processes: {processes}')
            # print(f'current in node names: {graph.in_node_names}')
            for sub_id, sub_process in enumerate(processes):
                print(f'check input node: {graph.in_node_names[sub_id]}')
                graph.edge += [
                    {'from': [graph.in_node_names[sub_id]], 'to': sub_process},
                    {'from': sub_process, 'to': [graph.out_node_names[sub_id]]}
                ]
            orma_data.append(graph)
        
    return orma_data


def get_node_from_ormadata(orma_data):
    data_nodes = []  # nodes include data node
    for graph in orma_data:
        data_nodes += graph.in_node_names
        data_nodes += graph.out_node_names

    return data_nodes


def get_edge_from_ormadata(orma_data):
    edges = []
    # edge [color=red]; // so is this
    # main -> init [style=dotted];
    for graph in orma_data:
        edges += graph.edge
    return edges


def draw_edges(edges, orma_graph):
    # read and refine into edges in graph
    for i, edge in enumerate(edges):
        if not edge['from']:
            pass
        else:
            edge_from, edge_to = edge['from'], edge['to']
            # edge_from, edge_to, color_type = edge
            edge_from_update = ''
            edge_to_update = ''

            if isinstance(edge_from, dict):
                for key, value in edge_from.items():
                    if key == 'col_name':
                        pass
                    elif key == 'color':
                        pass
                    else:
                        edge_from_update = edge_from[key]
                assert isinstance(edge_to, str)
                edge_to_update = edge_to
                orma_graph.edge(edge_from_update, edge_to_update)
            elif isinstance(edge_to, dict):
                for key, value in edge_to.items():
                    if key == 'col_name':
                        pass
                    elif key == 'color':
                        pass
                    else:
                        edge_to_update = edge_to[key]
                assert isinstance(edge_from, str)
                edge_from_update = edge_from
                orma_graph.edge(edge_from_update, edge_to_update)
    return orma_graph


def refine_dot_name(node_name):
    return f'"{node_name}"'


def process_feature_orma(orma_data, orma_dot):
    feature = {'shape': 'box', 'color': _process_color_, 'style': 'filled', 'peripheries': '1',
               'fontname': 'Helvetica'}  # label/size/font/...
    for graph in orma_data:
        if not graph.process:
            pass
        else:
            if len(graph.process) == 1:
                process_node = graph.process[0]
                orma_dot.attr('node', shape=feature['shape'], style=feature['style'], fillcolor=feature['color'],
                            peripheries=feature['peripheries'], fontname=feature['fontname'])
                orma_dot.node(process_node)
            else:
                # [[],...]
                for sub_process in graph.process:
                    process_node = sub_process[0]
                    orma_dot.attr('node', shape=feature['shape'], style=feature['style'], fillcolor=feature['color'],
                                peripheries=feature['peripheries'], fontname=feature['fontname'])
                    orma_dot.node(process_node)
    return orma_dot


def generate_dot(json_data, schemas, output):
    # default feature setting for data node
    orma_data = translate_operator_json_to_graph(json_data, schemas)
    feature_data = {'shape': 'box', 'style': 'rounded,filled', 'fillcolor': '#FFFFCC', 'peripheries': 1,
                    'fontname': "Helvetica-BoldOblique"}
    orma_dot = Digraph('ORMA', filename=output)

    data_nodes = get_node_from_ormadata(orma_data)
    edges = get_edge_from_ormadata(orma_data)
    orma_dot.attr('node', shape=feature_data['shape'], style=feature_data['style'], fillcolor=feature_data['fillcolor'])

    # how to represent different node in the same graph
    # label is same, but node name is not
    for node_item in data_nodes:
        node_name = node_item['col_name']
        node_label = node_item['label']
        orma_dot.node(node_label, label=node_name)  # same label but different node name
    orma_dot = process_feature_orma(orma_data, orma_dot)

    res_edges = []
    for edge in edges:
        from_node = edge['from']
        to_node = edge['to']
        print(f'from: {from_node}')
        print(f'to: {to_node}')
        if len(from_node) == 1 and len(to_node) == 1:
            res_edges.append({
                'from': from_node[0],
                'to': to_node[0],
            })

        if len(from_node) == 1 and len(to_node) > 1:
            for to_item in to_node:
                res_edges.append({
                    'from': from_node[0],
                    'to': to_item,
                })

        if len(from_node) > 1 and len(to_node) == 1:
            for from_item in from_node:
                res_edges.append({
                    'from': from_item,
                    'to': to_node[0],
                })

    # color the data nodes
    # if it appear in 'to'; don't change
    for node_item in data_nodes:
        node_label = node_item['col_name']
        node_name = node_item['label']
        occurred_v = []
        port_v = ''
        node_color = {}
        for idx, edge in enumerate(res_edges):
            # edge_from, edge_to, color_type = edge
            edge_from, edge_to = edge['from'], edge['to']
            if isinstance(edge_from, str):
                pass
            elif isinstance(edge_from, dict):
                if edge_from['label'] == node_name:
                    port_v = edge_from['label']  # what's/re the from column(s)
                    if port_v in occurred_v:
                        pass
                    else:
                        node_color.update({port_v: _color_})
                        # orma_dot.node(node_name, label=node_label, fillcolor=node_color[f'{port_v}'])

            if isinstance(edge_to, str):
                pass
            elif isinstance(edge_to, dict):
                if edge_to['label'] == node_name:
                    port_v = edge_to['label']  # what's/re the to column(s)
                    node_color.update({port_v: edge_to['color']})
                    occurred_v.append(port_v)
        if not port_v:
            pass
        else:
            orma_dot.node(node_name, label=node_label, fillcolor=node_color[port_v])

    draw_edges(res_edges, orma_dot)
    # orma_dot.view()
    return orma_dot


# TASK 2; Create a summary view of data cleaning workflow
def schema_analysis(json_data, schema_info):
    edges = []
    # analyze schema change and define the edges
    for i, operator in enumerate(json_data, start=1):
        if 'op' in [*operator]:
            if operator['op'] == 'core/column-addition':  # merge operation
                basename = merge_basename(operator)
                edge_to = {f'schema{i}': operator['newColumnName'], 'color': _gen_val_color_}
                if isinstance(basename, list):
                    for idx, col_name in enumerate(basename):
                        if idx == len(basename) - 1:
                            edge_from = {f'schema{i - 1}': col_name, 'label': ' column-addition',
                                         'edge_color': _gen_label_color_}
                        else:
                            edge_from = {f'schema{i - 1}': col_name, 'label': ' ',
                                         'edge_color': _gen_label_color_}
                        edges.append([edge_from, edge_to])
                else:
                    edge_from = {f'schema{i - 1}': basename, 'label': ' column-addition',
                                 'edge_color': _gen_label_color_}
                    edges.append([edge_from, edge_to])

            elif operator['op'] == 'core/column-split':  # split operation
                cur_schema = schema_info[i]
                prev_schema = schema_info[i - 1]
                new_cols = list(set(cur_schema) - set(prev_schema))
                # label_name = operator['op'].split('-')[-1]

                for idx, cols in enumerate(new_cols):
                    # edge_label = f'_{cols.split(" ")[-1]}
                    if idx == 0:
                        edge_from = {f'schema{i - 1}': operator['columnName'], 'label': ' column-split',
                                     'edge_color': _gen_label_color_}
                    else:
                        edge_from = {f'schema{i - 1}': operator['columnName'], 'label': ' ',
                                     'edge_color': _gen_label_color_}
                    edge_to = {f'schema{i}': cols, 'color': _gen_val_color_}
                    edges.append([edge_from, edge_to])
                # original_col = operator['columnName']
                # flag_original = original_col in cur_schema
                # if flag_original:
                #     edge_from = {f'schema{i - 1}': operator['columnName'], 'label': ' ',
                #                  'edge_color': _gen_label_color_}
                #     edge_to = {f'schema{i}': original_col, 'color': _color_}
                #     # not remove the original column
                #     edges.append([edge_from, edge_to])
                # else:
                #     # remove the original column
                #     pass

            elif operator['op'] == 'core/column-rename':  # split operation
                edge_from = {f'schema{i - 1}': operator['oldColumnName'], 'label': ' column-rename',
                             'edge_color': _edge_color_}
                edge_to = {f'schema{i}': operator['newColumnName'], 'color': _color_}
                edges.append([edge_from, edge_to])

            elif operator['op'] == 'core/column-removal':
                edge_from = {f'schema{i - 1}': operator['columnName'], 'label': ' column-removal',
                             'style': 'dashed', 'edge_color': _gen_label_color_}
                prev_schema = schema_info[i - 1]
                old_idx = prev_schema.index(operator['columnName'])
                prev_idx = old_idx - 1
                edge_to = {f'schema{i}': f"{prev_schema[prev_idx]}",
                           'color': _remove_color_,
                           }
                # edge_to 'label': edge_label, 'style': 'dashed',
                #                              'edge_color': '#000000'}
                edges.append([edge_from, edge_to])

            elif operator['op'] == 'core/column-addition-by-fetching-urls':
                edge_from = {f'schema{i - 1}': operator['baseColumnName']}
                edge_to = {f'schema{i}': f"{operator['newColumnName']}", 'color': _gen_val_color_}
                edges.append([edge_from, edge_to])

            elif operator['op'] == 'core/multivalued-cell-join':
                edge_from = {f'schema{i - 1}': operator['columnName']}
                edge_to = {f'schema{i}': f"{operator['columnName']}", 'color': _gen_val_color_}
                edges.append([edge_from, edge_to])

            elif operator['op'] == 'core/transpose-columns-into-rows':
                new_cols = [operator['keyColumnName'], operator['valueColumnName']]
                for index, new_col in enumerate(new_cols):
                    if index == 0:
                        edge_from = {f'schema{i - 1}': operator['startColumnName'],
                                     'label': ' ', 'edge_color': _gen_label_color_}
                    else:
                        edge_from = {f'schema{i - 1}': operator['startColumnName'],
                                     'label': ' transpose-columns-into-rows', 'edge_color': _gen_label_color_}
                    edge_to = {f'schema{i}': f"{new_col}", 'color': _gen_val_color_}
                    edges.append([edge_from, edge_to])

            elif operator['op'] == 'core/row-removal':
                edge_from = {f'schema{i - 1}': operator['engineConfig']['facets'][0]['name']}
                edge_to = {f'schema{i - 1}': operator['engineConfig']['facets'][0]['name'], 'color': _color_}
                edges.append([edge_from, edge_to])

            elif operator['op'] == 'core/column-move':
                cur_schema = schema_info[i]  # after applying this transformation
                # column_to #5
                old_schema = schema_info[i - 1]  # before applying this transformation

                col_name = operator['columnName']
                old_idx = old_schema.index(col_name)
                new_idx = operator['index']
                edge_from = {f'schema{i - 1}': col_name, 'style': 'dashed',
                             'label': f' Move_to #{new_idx}',
                             'edge_color': _edge_color_}
                edge_to = {f'schema{i}': col_name, 'color': _color_}
                edges.append([edge_from, edge_to])  # for now consider it as change structure level

                old_col_name = old_schema[new_idx]
                # define invisible node: from and to
                iv_edge_from = {f'schema{i - 1}': old_col_name, 'style': 'invisible',
                                'label': '',
                                'dir': 'none',
                                'edge_color': _edge_color_}
                iv_edge_to = {f'schema{i}': old_col_name, 'color': _inNodeColor_}
                edges.append([iv_edge_from, iv_edge_to])

                # add start to start
                start_col_name = old_schema[0]
                start_edge_from = {f'schema{i - 1}': start_col_name, 'style': 'invisible',
                                   'label': '',
                                   'dir': 'none',
                                   'edge_color': _edge_color_}
                start_edge_to = {f'schema{i}': start_col_name, 'color': _inNodeColor_}
                edges.append([start_edge_from, start_edge_to])

                # add end to end
                end_col_name = old_schema[-1]
                end_edge_from = {f'schema{i - 1}': end_col_name, 'style': 'invisible',
                                 'label': '',
                                 'dir': 'none',
                                 'edge_color': _edge_color_}
                end_edge_to = {f'schema{i}': end_col_name, 'color': _inNodeColor_}
                edges.append([end_edge_from, end_edge_to])

            elif operator['op'] == 'core/mass-edit':
                edge_from = {f'schema{i - 1}': operator['columnName'], 'label': ' mass-edit', 'edge_color': '#BB0000'}
                edge_to = {f'schema{i}': operator['columnName'], 'color': _custome_v_color}
                edges.append([edge_from, edge_to])

            # TODO
            # reconciliation
            elif operator['op'] == 'core/recon':
                edge_from = {f'schema{i - 1}': operator['columnName'], 'label': ' reconciliation',
                             'edge_color': '#BB0000'}
                edge_to = {f'schema{i}': operator['columnName'], 'color': _custome_v_color}
                edges.append([edge_from, edge_to])
            else:  # normal unary operation
                try:
                    column_name = operator['columnName']
                    if 'expression' in operator:
                        expression = operator['expression']
                        exp_preprocess = expression.split(".")[0]
                        if exp_preprocess == 'value':
                            label = f' .{expression.split(".")[-1]}'
                            if expression == 'value.toDate()':
                                # schema change
                                edge_color = _type_label_color_
                                edge_to = {f'schema{i}': operator['columnName'], 'color': _type_con_color_}
                            elif expression == 'value.toNumber()':
                                # schema change
                                edge_color = _type_label_color_
                                edge_to = {f'schema{i}': operator['columnName'], 'color': _type_con_color_}
                            else:
                                edge_color = _gen_label_color_
                                edge_to = {f'schema{i}': operator['columnName'], 'color': _gen_val_color_}

                        else:
                            # value change
                            label = f' {expression}'
                            edge_color = _gen_label_color_
                            edge_to = {f'schema{i}': operator['columnName'], 'color': _gen_val_color_}
                        edge_from = {f'schema{i - 1}': operator['columnName'], 'label': label, 'edge_color': edge_color}
                        edges.append([edge_from, edge_to])
                    else:
                        label = operator['op'].split('/')
                        edge_from = {f'schema{i - 1}': column_name, 'label': f' {label}',
                                     'edge_color': _gen_label_color_}
                        edge_to = {f'schema{i}': column_name, 'color': _gen_val_color_}
                        edges.append([edge_from, edge_to])
                except KeyError:
                    continue
        else:
            prev_schema = schema_info[i - 1]
            cur_schema = schema_info[i]
            assert len(cur_schema) == len(prev_schema)
            description = operator['description'].split(' ')
            if 'column' in description:
                # single edit
                # take care of this transformation!
                column_name = description[-1]
                desc = operator['description']
                edge_label = f' single_cell_edit row #{desc.split(",")[0].split(" ")[-1]}'
                edge_from = {f'schema{i - 1}': column_name, 'label': edge_label, 'edge_color': '#BB0000'}
                edge_to = {f'schema{i}': column_name, 'color': _custome_v_color}
                edges.append([edge_from, edge_to])
            else:
                # Star/flag row 1
                desc = operator['description']
                edge_label = f' {"_".join(desc.split(" ")[:2])} #{desc.split(" ")[-1]}'
                edge_from = {f'schema{i - 1}': cur_schema[0], 'label': edge_label, 'style': 'dashed',
                             'edge_color': '#000000'}
                edge_to = {f'schema{i}': cur_schema[0], 'color': '#D0D0D0'}
                edges.append([edge_from, edge_to])

    return edges


def get_schema_list(schema_info):
    schemas = []
    for schema in schema_info:
        schemas.append(schema['schema'])
    return schemas


def get_edge_ports(key, value, schemas):
    schema_no = int(key.split('schema')[-1])
    cur_schema = schemas[schema_no]
    from_idx = cur_schema.index(value)
    update_name = f'{key}:f{from_idx}'
    return update_name


def get_edges(edges, schemas, schema_graph):
    # read and refine into edges in graph
    for i, edge in enumerate(edges):
        edge_from, edge_to = edge
        # edge_from, edge_to, color_type = edge
        edge_from_update = ''
        edge_to_update = ''
        if 'dir' in [*edge_from]:
            for key, value in edge_from.items():
                if key == 'label':
                    pass
                elif key == 'style':
                    pass
                elif key == 'edge_color':
                    pass
                elif key == 'dir':
                    pass
                else:
                    edge_from_update = get_edge_ports(key, value, schemas)
            for key1, value1 in edge_to.items():
                if key1 == 'color':
                    pass
                else:
                    edge_to_update = get_edge_ports(key1, value1, schemas)
            schema_graph.edge(edge_from_update, edge_to_update, label=edge_from['label'], style=edge_from['style'],
                              dir=edge_from['dir'],
                              color=edge_from['edge_color'], fontcolor=edge_from['edge_color'])
        else:
            if 'style' in [*edge_from]:
                # specific transformation
                # label stands for edge's label
                for key, value in edge_from.items():
                    if key == 'label':
                        pass
                    elif key == 'style':
                        pass
                    elif key == 'edge_color':
                        pass
                    else:
                        edge_from_update = get_edge_ports(key, value, schemas)
                for key1, value1 in edge_to.items():
                    if key1 == 'color':
                        pass
                    else:
                        edge_to_update = get_edge_ports(key1, value1, schemas)
                schema_graph.edge(edge_from_update, edge_to_update, label=edge_from['label'], style=edge_from['style'],
                                  color=edge_from['edge_color'], fontcolor=edge_from['edge_color'])
            else:
                if 'label' in [*edge_from]:
                    # has label --> must have edge_color
                    for key, value in edge_from.items():
                        if key == 'label':
                            pass
                        elif key == 'edge_color':
                            pass
                        else:
                            edge_from_update = get_edge_ports(key, value, schemas)
                    for key1, value1 in edge_to.items():
                        if key1 == 'color':
                            pass
                        else:
                            edge_to_update = get_edge_ports(key1, value1, schemas)
                    schema_graph.edge(edge_from_update, edge_to_update, label=edge_from['label'],
                                      color=edge_from['edge_color'], fontcolor=edge_from['edge_color'])
                else:
                    for key, value in edge_from.items():
                        edge_from_update = get_edge_ports(key, value, schemas)
                    for key1, value1 in edge_to.items():
                        if key1 == 'color':
                            pass
                        else:
                            edge_to_update = get_edge_ports(key1, value1, schemas)
                    schema_graph.edge(edge_from_update, edge_to_update)
        # edges_list.append((edge_from_update, edge_to_update))
    return schema_graph


def color_ports(schema, color_idx: list, color_type: dict):
    # html like label
    '''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR>
    <TD PORT="f0">one</TD>
    <TD>two</TD>
  </TR>
</TABLE>>'''
    res = '<<table align="left" border="0" cellspacing="0">'
    res += '<tr>'
    for i, column in enumerate(schema):
        if i in color_idx:
            color = color_type[column]
            res += f'<td port="f{i}" border="1" bgcolor="{color}" >{column}</td>'
        else:
            res += f'<td port="f{i}" border="1">{column}</td>'
    res += '</tr>'
    res += '</table>>'
    return res


def draw_schema_evolution(json_data, schemas, output):
    # use Data structure from graphviz
    feature_data = {'shape': 'box', 'style': 'rounded,filled', 'fillcolor': '#FAFAF0',
                    'fontname': "Symbol", 'fontsize': "12"}  # should be string!!!
    schema_graph = Digraph('Schema_Evolution', filename=output)
    schema_graph.graph_attr['ranksep'] = '0.5'
    schema_graph.attr('node', shape=feature_data['shape'], style=feature_data['style'],
                      fillcolor=feature_data['fillcolor'],
                      fontname=feature_data['fontname'], fontsize=feature_data['fontsize'])
    schema_graph.attr('edge', fontname="Helvetica-BoldOblique", fontsize="12")

    # schema_graph.attr('node', fontsize="16", shape="ellipse")

    # [[{'schema0': 'date'}, {'schema1': 'date 2'}],...]
    # [from, to]
    edges = schema_analysis(json_data, schemas)

    for i, schema in enumerate(schemas):
        node_name = f'schema{i}'
        occurred_v = []
        port_values = []
        port_idx = []
        node_color = {}
        for idx, edge in enumerate(edges):
            # edge_from, edge_to, color_type = edge
            edge_from, edge_to = edge
            if node_name in [*edge_from]:
                port_v = edge_from[node_name]  # what's/re the from column(s)
                port_id = schema.index(port_v)  # what's/re the port index(es)
                if port_v in occurred_v:
                    pass
                else:
                    port_values.append(port_v)
                    port_idx.append(port_id)
                    if 'style' in [*edge_from]:
                        if edge_from['style'] == 'invisible':
                            node_color.update({port_v: _inNodeColor_})
                        else:
                            node_color.update({port_v: _color_})
                    else:
                        node_color.update({port_v: _color_})

            if node_name in [*edge_to]:
                port_v = edge_to[node_name]  # what's/re the to column(s)
                port_id = schema.index(port_v)  # what's/re the port index(es)
                port_idx.append(port_id)
                port_values.append(port_v)
                node_color.update({port_v: edge_to['color']})
                occurred_v.append(port_v)

        label = color_ports(schema, port_idx, color_type=node_color)
        schema_graph.node(node_name, label=f'''{label}''')

    schema_graph = get_edges(edges, schemas, schema_graph)
    # schema_graph.edges(edges_list)

    return schema_graph


def model_schema_evolution(json_data, schema_info, output_gv):
    schemas = get_schema_list(schema_info)
    # output_gv = 'output/schema_evo.gv'
    schema_graph = draw_schema_evolution(json_data, schemas, output_gv)
    schema_graph.view()


# TASK 3: Create a table_view of data cleaing workflow
def table_view(json_data, combined=False):
    table_view_data = []
    for i, operator in enumerate(json_data, start=1):
        graph = ORMAGraph()  # graph includes nodes and edges
        graph.raw_operator = operator
        graph.step_index = i
        graph.history_id = operator['id']
        prev_table = f'table{i - 1}'
        cur_table = f'table{i}'

        if 'op' in [*operator]:
            if operator['op'] == 'core/column-addition':  # merge operation
                colname = f'col-name "{operator["baseColumnName"]}"'
                newColumnName = f'newColumnName "{operator["newColumnName"]}"'
                grelexp = f'expression "{operator["expression"].split(":")[-1]}"'

                insertpos = f'InsertPosition "{operator["columnInsertIndex"]}"'  # physical position
                graph.process = [f'({i}) column-addition']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                        newColumnName,
                        grelexp,
                        insertpos
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/column-split':  # split operation
                colname = f'col-name  "{operator["columnName"]}"'
                separator = f'separator "{operator["separator"]}"'
                remove = f'removeOriginalColumn "{operator["removeOriginalColumn"]}"'
                graph.process = [f'({i}) column-split']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                        separator,
                        remove
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/column-rename':  # split operation
                oldColumnName = f'oldColumnName "{operator["oldColumnName"]}"'
                newColumnName = f'newColumnName "{operator["newColumnName"]}"'
                graph.process = [f'({i}) column-rename']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        oldColumnName,
                        newColumnName
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/column-removal':
                colname = f'col-name "{operator["columnName"]}"'
                graph.process = [f'({i}) column-removal']

                if not combined:
                    graph.in_node_names += [
                        prev_table,
                    ]
                    # TODO
                    # port is needed to represent null
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/column-addition-by-fetching-urls':
                colname = f'col-name "{operator["baseColumName"]}"'
                newColumnName = f'newColumnName "{operator["newColumName"]}"'
                urlExpression = f'urlExpression "{operator["urlExpression"].split(":")[-1]}"'
                graph.process = [f'({i}) column addition-by-fetching-urls']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                        newColumnName,
                        urlExpression
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/multivalued-cell-join':
                colname = f'col-name "{operator["columName"]}"'
                keyColumnName = f'keyColumnName "{operator["keyColumnName"]}"'
                separator = f'separator "{operator["separator"]}"'

                graph.process = [f'({i}) multivalued-cell-join']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                        keyColumnName,
                        separator
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/transpose-columns-into-rows':
                colname = f'col-name "{operator["startColumnName"]}"'
                columnCount = f'columnCount "{operator["columnCount"]}"'
                combinedColumnName = f'combinedColumnName "{operator["combinedColumnName"]}"'
                separator = f'separator "{operator["separator"]}"'

                graph.process = [f'({i}) transpose-columns-into-rows']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                        columnCount,
                        combinedColumnName,
                        separator
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/row-removal':
                # colname = f'col-name "{operator["engineConfig"]["facets"][0]["columnName"]}"'
                expression = f'expression "{operator["engineConfig"]["facets"][0]["expression"].split(":")[-1]}"'

                graph.process = [f'({i}) row-removal']

                if not combined:
                    graph.in_node_names += [
                        prev_table,
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        # colname,
                        expression
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/column-move':
                colname = f'col-name "{operator["columnName"]}"'
                index = operator["index"]

                graph.process = [f'({i}) Move_to #{index}']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                        index
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            elif operator['op'] == 'core/mass-edit':
                colname = f'col-name "{operator["columnName"]}"'
                graph.process = [f'({i}) mass-edit']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
            elif operator['op'] == 'core/multivalued-cell-split':
                colname = f'col-name "{operator["columnName"]}"'
                keyColumnName = f'keyColumnName {operator["keyColumnName"]}'
                mode = f"mode {operator['separator']}"
                separator = f'separator "{operator["separator"]}"'
                regex = f'"regex {operator["regex"]}"'
                graph.process = [f'({i}) multivalued-cell-split']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                        keyColumnName,
                        mode,
                        separator,
                        regex
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
            elif operator['op'] == 'core/recon':
                colname = operator['columnName']
                graph.process = [f'({i}) reconciliation']
                recon_id = operator['config']['type']['id']
                columns = []
                mode = operator['config']['mode']
                if operator['config']['columnDetails']:
                    columns = operator['config']['columnDetails'][0]['column']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        colname,
                        recon_id,
                        columns,
                        mode
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]

            else:  # normal unary operation
                try:
                    expression = operator['expression']
                    exp_preprocess = expression.split(".")[0]
                    column_name = operator['columnName']
                    if exp_preprocess == 'value':
                        graph.process = [f'({i}) .{expression.split(".")[-1]}']
                    else:
                        # value change
                        graph.process = [f'({i}) {expression.split(":")[-1]}']
                    colname = f'col-name "{column_name}"'
                    if not combined:
                        graph.in_node_names += [
                            prev_table
                        ]
                        graph.out_node_names += [
                            cur_table
                        ]
                    else:
                        graph.in_node_names += [
                            prev_table,
                            colname
                        ]
                        graph.out_node_names += [
                            cur_table
                        ]

                except KeyError:
                    graph.process = [f'({i}) {operator["op"].split("/")[-1]}']
                    graph.in_node_names += [
                        prev_table,
                        # colname,
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
            # graph.edge += [{'from': graph.in_node_names, 'to': graph.process},
            #                {'from': graph.process, 'to': graph.out_node_names}]
            # table_view_data.append(graph)

        else:
            description = operator['description'].split(' ')
            if 'column' in description:
                # single edit
                column_name = f'col-name "{description[-1]}"'
                desc = operator['description']
                row_number = desc.split(",")[0].split(" ")[-1]
                process = f'single_cell_edit row #{row_number}'
                graph.process = [f'({i}) {process}']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        column_name,
                        row_number
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
            else:
                # Star/flag row 1
                desc = operator['description']
                row_number = desc.split(" ")[-1]
                process = f'{"_".join(desc.split(" ")[:2])} #{row_number}'
                graph.process = [f'({i}) {process}']
                if not combined:
                    graph.in_node_names += [
                        prev_table
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
                else:
                    graph.in_node_names += [
                        prev_table,
                        row_number
                    ]
                    graph.out_node_names += [
                        cur_table
                    ]
        graph.edge += [{'from': graph.in_node_names, 'to': graph.process},
                       {'from': graph.process, 'to': graph.out_node_names}]
        table_view_data.append(graph)

    return table_view_data


def get_node_from_table_view(orma_data):
    mixed_nodes = []
    data_nodes = []  # nodes include data node
    params_nodes = []
    for graph in orma_data:
        mixed_nodes += graph.in_node_names
        mixed_nodes += graph.out_node_names

    pattern = re.compile(r'(table)\d+')
    for nodes in mixed_nodes:
        if pattern.match(nodes):
            data_nodes.append(nodes)
        else:
            params_nodes.append(nodes)
    return data_nodes, params_nodes


def generate_table_dot(json_data, output='output/table_view.gv', combined=False):
    # data node: #FFFFCC
    # process: #CCFFCC
    table_view_data = table_view(json_data, combined)
    feature_data = {'shape': 'box', 'style': 'rounded,filled', 'fillcolor': _color_, 'peripheries': '1',
                    'fontname': 'Helvetica'}
    tableview_dot = Digraph('ORMA-Table-View', filename=output)
    tableview_dot.graph_attr['ranksep'] = '0.2'
    data_nodes, params_nodes = get_node_from_table_view(table_view_data)
    edges = get_edge_from_ormadata(table_view_data)
    tableview_dot.attr('node', shape=feature_data['shape'], style=feature_data['style'],
                       fillcolor=feature_data['fillcolor'])
    for node_item in data_nodes:
        # data node: in_node & out_node
        tableview_dot.node(node_item)

    # parameter nodes
    tableview_dot.attr('node', shape=feature_data['shape'], style=feature_data['style'],
                       fillcolor=_inNodeColor_)
    for params in params_nodes:
        tableview_dot.node(params)

    tableview_dot.attr('node', shape=feature_data['shape'], style='filled', fillcolor=_process_color_,
                       peripheries='1', fontname='Helvetica')
    for graph in table_view_data:
        # process node
        process_node = graph.process[0]
        tableview_dot.node(process_node)  # update process node

    for edge in edges:
        from_node = edge['from']
        to_node = edge['to']
        if len(from_node) == 1 and len(to_node) == 1:
            tableview_dot.edge(from_node[0], to_node[0])

        if len(from_node) == 1 and len(to_node) > 1:
            for to_item in to_node:
                tableview_dot.edge(from_node[0], to_item)

        if len(from_node) > 1 and len(to_node) == 1:
            for from_item in from_node:
                tableview_dot.edge(from_item, to_node[0])

    tableview_dot.view()
    return tableview_dot


def parallel_view_main(json_data, schema_info, output_gv):
    '''Run parallel view'''
    # TODO
    # facet edge rendering
    # output_gv = 'output/parallel_view.gv'
    schemas = get_schema_list(schema_info)
    orma_g = generate_dot(json_data, schemas, output_gv)
    orma_g.view()


# decomposition
# serial - parallel
def write_linked_dep(edges):
    # this will return dictionary: {node: [dependent nodes]}
    # we only care the nodes with different name but linked together
    neighbors_of = {}
    nodes = set()
    for edge in edges:
        u = edge['from']
        len_u = len(u)
        v = edge['to']
        len_v = len(v)
        if len_u == 1 and len_v == 1:
            u = u[0]['col_name']
            v = v[0]['col_name']
            nodes.add(u)
            nodes.add(v)
            # if u != v:
            # Add edge u->v and u->v
            neighbors_of.setdefault(u, []).append(v)
            neighbors_of.setdefault(v, []).append(u)

        elif len_v > 1:
            u = u[0]['col_name']
            nodes.add(u)
            for output in v:
                nodes.add(output['col_name'])
                # if output['col_name'] != u:
                neighbors_of.setdefault(u, []).append(output['col_name'])
                neighbors_of.setdefault(output['col_name'], []).append(u)
        elif len_u > 1:
            v = v[0]['col_name']
            nodes.add(v)
            for input_node in u:
                nodes.add(input_node['col_name'])
                # if input_node['col_name'] != v:
                neighbors_of.setdefault(input_node['col_name'], []).append(v)
                neighbors_of.setdefault(v, []).append(input_node['col_name'])
    return neighbors_of, nodes


def find_component(neighbors_of, u, component=None):
    if component is None:
        component = {u}
    for v in neighbors_of[u]:
        if v in component:
            continue
        component.add(v)
        find_component(neighbors_of, v, component)
    return component


def cluster_main(json_data, schema_info):
    schemas = get_schema_list(schema_info)
    orma_data = translate_operator_json_to_graph(json_data, schemas)
    new_edges = []
    for graph in orma_data:
        new_edges += [{'from': graph.in_node_names, 'to': graph.out_node_names}]

    neighbors_of, nodes = write_linked_dep(new_edges)
    components = []
    visited_nodes = set()
    for u in nodes:
        if u in visited_nodes:
            continue
        component = find_component(neighbors_of, u)
        components.append(component)
        visited_nodes |= component
    del visited_nodes

    return components


def split_recipe(json_data, schema_info, output_gv='modular_views/module_view'):
    # how to define subworkflow:
    # same input or same output
    components = cluster_main(json_data, schema_info)
    schemas = get_schema_list(schema_info)
    orma_data = translate_operator_json_to_graph(json_data, schemas)

    clusters = []
    for component in components:
        cluster = []
        for i, graph in enumerate(orma_data):
            in_nodes = []
            for in_node in graph.in_node_names:
                in_nodes.append(in_node['col_name'])
            in_nodes_set = set(in_nodes)
            common_flag = in_nodes_set.intersection(set(component))
            if common_flag:
                cluster.append(i)
            else:
                pass
        clusters.append(cluster)

    operators = [graph.raw_operator for graph in orma_data]
    counter = 0
    for cluster_list in clusters:
        json_res = []
        cluster_schemas = []
        if not cluster_list:
            pass
        else:
            for index in cluster_list:
                json_res.append(operators[index])
                cluster_schemas.append(schemas[index])
        if json_res:
            with open(f'{output_gv}_{counter}.json', 'w')as f:
                json.dump(json_res, f, indent=4)
            # output_gv = f'{output_gv}_{counter}'
            orma_g = generate_dot(json_res, cluster_schemas, f'{output_gv}_{counter}')
            orma_g.view()
            counter += 1
        else:
            pass


class ORMA:
    def __init__(self):
        """
          Init functions for this class, put any initialization attributes
          that you need here
          """
        pass

    @staticmethod
    def generate_table_view(json_data, output, combined):
        generate_table_dot(json_data, output, combined)

    @staticmethod
    def generate_parallel_view(json_data, schema_info, output_gv):
        parallel_view_main(json_data, schema_info, output_gv)

    @staticmethod
    def generate_schema_view(json_data, schema_info, output_gv):
        model_schema_evolution(json_data, schema_info, output_gv=output_gv)

    @staticmethod
    def generate_module_views(json_data, schema_info, output_gv):
        split_recipe(json_data, schema_info, output_gv=output_gv)


class ORMAProcessor:
    def __init__(self):
        pass

    def generate_views(self, output, project_id=None, type="table_view", **kwargs):
        if project_id:
            json_data, schema_info = gen_recipe(project_id)
        else:
            json_data, schema_info = kwargs['json_data'], kwargs['schema_info']
        if type == "table_view":
            combined = kwargs['combined']
            ORMA.generate_table_view(json_data, output, combined)
        elif type == "schema_view":
            return ORMA.generate_schema_view(json_data, schema_info, output)
        elif type == "parallel_view":
            return ORMA.generate_parallel_view(json_data, schema_info, output)
        elif type == 'modular_views':
            return ORMA.generate_module_views(json_data, schema_info, output)
        else:
            raise BaseException("Workflow type Only Serial, Parallel or Merge")


def main():
    FUNCTION_MAP = {
        'parallel_view': parallel_view_main,
        'schema_view': model_schema_evolution,
        'table_view': generate_table_dot,
        'modular_views': split_recipe
    }

    parser = argparse.ArgumentParser(description='OpenRefine Model Analysis')
    # parser.add_argument('command', choices=FUNCTION_MAP.keys() )
    parser.add_argument(
        "--project_id",
        type=int,
        default=None,
        help='Input Project ID'
    )
    parser.add_argument(
        "--output",
        type=str,
        default='output/orma_exp.gv',
        help='path of the output gv file'
    )
    parser.add_argument(
        'command', choices=FUNCTION_MAP.keys()
    )
    parser.add_argument(
        "--combined",
        type=bool,
        default=False,
        help='Only input when you choose Table view. [with/without Parameters] Default: False'
    )

    parser.add_argument(
        "--json_data",
        type=list,
        default=None,
        help='recipe JSON data[required]: orma on existing enhanced recipe'
    )
    parser.add_argument(
        "--schema_info",
        type=list,
        default=None,
        help='schema info [required]:orma on existing enhanced recipe'
    )

    args = parser.parse_args()
    func = FUNCTION_MAP[args.command]

    func(args.project_id, args.output)

# this is for test
# if __name__ == '__main__':
    # ORMAProcessor().generate_views(2494992270641, 'usecase2/table_view/table_view.gv',
    #                                'table_view')
    # ORMAProcessor().generate_views(2494992270641, 'usecase2/schema_view/schema_view.gv',
    #                                'schema_view')
    # ORMAProcessor().generate_views(2494992270641, 'usecase2/parallel_view/parallel_view.gv',
    #                                'parallel_view')
    # project_id = 1880722204439
    # ORMAProcessor().generate_views(project_id, '../usecase2/modular_views/module_view',
    #                                'modular_views')
    # split_recipe(project_id=2494992270641)
    # cluster_main(project_id=2494992270641) usecase2/modular_views/parallel_view
    # split_recipe()
    # generate_table_dot()  # table_view
    # model_schema_evolution(project_id=2124203262743, output_gv='output/schema_view.gv') # summary view
    # main1()  # modular_views
    # main()
    # temp(2124203262743)
