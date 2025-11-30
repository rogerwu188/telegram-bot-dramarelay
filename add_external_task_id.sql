-- 添加 external_task_id 字段到 drama_tasks 表
ALTER TABLE drama_tasks ADD COLUMN IF NOT EXISTS external_task_id INTEGER;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_external_task_id ON drama_tasks(external_task_id);

-- 验证字段是否添加成功
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'drama_tasks' 
ORDER BY ordinal_position;
