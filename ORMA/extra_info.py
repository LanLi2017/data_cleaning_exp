from pprint import pprint

from ORMA.OpenRefineClientPy3.google_refine.refine import refine


def diff_schemas(schema_init, schemas:list):
    # [{'schema': [,...,...,]}]
    #TODO
    #...
    result = []
    result[0] = schemas[0]['schema']
    pass


def oh_map_history(op):
    '''
        operation history from data.txt
        => include a complete record (single-edit; star/flag rows)
    '''
    oh_list = op.get_operations()

    '''
        history list: 
        history id; time stamp; description [retrospective provenance]
    '''
    histories = op.list_history()  # history id/ time/ desc
    past_histories = histories['past']

    assert len(oh_list) == len(past_histories)
    map_result = [
        {**oh, **history}
        for oh, history in zip(oh_list, past_histories)
    ]
    # description will be overwrite with retrospective info from history list.
    return oh_list, past_histories, map_result


def schema_evolution(op, past_histories, map_result):
    '''
    :param past_histories: history list(id, time_stamp,description)
    :param op: OpenRefine project
    :return: schema information
    '''
    # the temporal shema info
    schema_info = []
    past_id_list = [0] + [his_id['id'] for his_id in past_histories]

    # the initial column ": set history id as 0
    for past_id in past_id_list:
        schema_temp = dict()
        # undo each step
        # fetch column models
        op.undo_redo_project(past_id)
        response = op.get_models()
        column_model = response['columnModel']
        columns = [column['name'] for column in column_model['columns']]
        # print(f'history id: {history_id}; columns: {columns}')
        schema_temp['schema'] = columns
        schema_info.append(schema_temp)

    schema_init, *schema_tail = schema_info
    # schema_diff = []
    # schema_diff[0] = {'schema_change':}
    update_result = [
        {**map_result, **schema_tail}
        for map_result, schema_tail in zip(map_result, schema_tail)
    ]
    #TODO
    # schema change?

    return update_result, schema_info


def generate_recipe(project_id):
    # project_id = 2478996104406
    # project_id = 2486157629041  # 723 rows
    op = refine.RefineProject(refine.RefineServer(), project_id)
    oh_list, past_histories, map_result = oh_map_history(op)
    enhanced_recipe,schema_info = schema_evolution(op, past_histories, map_result)
    return enhanced_recipe, schema_info


def main(project_id=1880722204439):
    enhanced_recipe, schemas = generate_recipe(project_id)
    print(schemas)


if __name__ == '__main__':
    main()
