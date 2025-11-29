-- 重置测试任务 "爱情动作 · 《test x2c pool》" 为未领取状态
-- 删除用户对该任务的领取记录

-- 查找任务ID
SELECT task_id, title FROM drama_tasks WHERE title LIKE '%test x2c pool%';

-- 删除用户领取记录 (假设 task_id 是上面查询的结果)
-- 请将 <task_id> 替换为实际的任务ID
-- 请将 <user_id> 替换为您的用户ID (5156570084)

DELETE FROM user_tasks 
WHERE task_id = (SELECT task_id FROM drama_tasks WHERE title LIKE '%test x2c pool%')
  AND user_id = 5156570084;

-- 验证删除结果
SELECT * FROM user_tasks 
WHERE task_id = (SELECT task_id FROM drama_tasks WHERE title LIKE '%test x2c pool%')
  AND user_id = 5156570084;
