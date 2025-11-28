-- 数据库迁移脚本: 添加 Webhook 回调字段
-- 版本: v1.1.0
-- 日期: 2025-11-27
-- 说明: 为 drama_tasks 表添加 callback_url 和 callback_secret 字段

-- 1. 添加 callback_url 字段 (可选,用于任务完成后的回调通知)
ALTER TABLE drama_tasks
ADD COLUMN IF NOT EXISTS callback_url TEXT;

-- 2. 添加 callback_secret 字段 (可选,用于验证回调请求)
ALTER TABLE drama_tasks
ADD COLUMN IF NOT EXISTS callback_secret TEXT;

-- 3. 添加 callback_retry_count 字段 (记录回调重试次数)
ALTER TABLE drama_tasks
ADD COLUMN IF NOT EXISTS callback_retry_count INTEGER DEFAULT 0;

-- 4. 添加 callback_last_attempt 字段 (记录最后一次回调尝试时间)
ALTER TABLE drama_tasks
ADD COLUMN IF NOT EXISTS callback_last_attempt TIMESTAMP;

-- 5. 添加 callback_status 字段 (记录回调状态: pending, success, failed)
ALTER TABLE drama_tasks
ADD COLUMN IF NOT EXISTS callback_status TEXT DEFAULT 'pending';

-- 6. 添加索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_drama_tasks_callback_status 
ON drama_tasks(callback_status);

-- 7. 添加注释
COMMENT ON COLUMN drama_tasks.callback_url IS 'Webhook 回调 URL,任务完成后会向此 URL 发送 POST 请求';
COMMENT ON COLUMN drama_tasks.callback_secret IS 'Webhook 回调密钥,用于验证请求来源';
COMMENT ON COLUMN drama_tasks.callback_retry_count IS '回调重试次数,最多重试 3 次';
COMMENT ON COLUMN drama_tasks.callback_last_attempt IS '最后一次回调尝试时间';
COMMENT ON COLUMN drama_tasks.callback_status IS '回调状态: pending(待回调), success(成功), failed(失败)';

-- 完成
SELECT '✅ Webhook 字段添加完成!' AS status;
