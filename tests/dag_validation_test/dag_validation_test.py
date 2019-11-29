"""
test for 'Extract_Keywords_From_Corpus'
"""

DAG_ID = 'Extract_Keywords_From_Corpus'


def test_task_count(dagbag):
    """
    :return:
    """
    dag = dagbag.get_dag(DAG_ID)
    assert len(dag.tasks) == 1


def test_contain_all_tasks(dagbag):
    """
    :return:
    """
    dag = dagbag.get_dag(DAG_ID)

    tasks = dag.tasks
    task_ids = list(map(lambda task: task.task_id, tasks))
    task_ids.sort()
    expected_ids = ['etl_keyword_extraction_task']

    expected_ids.sort()

    assert task_ids == expected_ids
