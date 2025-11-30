-- 添加英文字段到 drama_tasks 表
-- 用于支持多语言显示

ALTER TABLE drama_tasks 
ADD COLUMN IF NOT EXISTS title_en TEXT,
ADD COLUMN IF NOT EXISTS description_en TEXT;

-- 添加注释
COMMENT ON COLUMN drama_tasks.title_en IS '任务标题（英文）';
COMMENT ON COLUMN drama_tasks.description_en IS '任务描述（英文）';

-- 查看表结构
\d drama_tasks
