-- 005_add_anti_fraud_fields.sql
-- 添加反刷量相关字段

-- 在 users 表添加最后提交时间字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_submit_time TIMESTAMP;

-- 在 submissions 表添加验证状态字段
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS link_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS verification_time TIMESTAMP;

-- 创建每日提交统计视图(用于快速查询)
CREATE OR REPLACE VIEW daily_submission_stats AS
SELECT 
    user_id,
    DATE(created_at) as submit_date,
    COUNT(*) as submit_count
FROM submissions
GROUP BY user_id, DATE(created_at);

-- 添加索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_submissions_user_created ON submissions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_submit ON users(last_submit_time);
