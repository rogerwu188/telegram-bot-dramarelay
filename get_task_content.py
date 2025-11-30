def get_task_title(task, user_lang):
    """根据用户语言获取任务标题"""
    if user_lang == 'en' and task.get('title_en'):
        return task['title_en']
    return task['title']

def get_task_description(task, user_lang):
    """根据用户语言获取任务描述"""
    if user_lang == 'en' and task.get('description_en'):
        return task['description_en']
    return task.get('description', '')
