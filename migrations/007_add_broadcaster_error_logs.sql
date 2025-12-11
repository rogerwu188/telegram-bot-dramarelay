-- 创建回传错误日志表
CREATE TABLE IF NOT EXISTS broadcaster_error_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER,
    task_title VARCHAR(500),
    project_id VARCHAR(100),
    video_url TEXT,
    platform VARCHAR(50),
    error_type VARCHAR(100),
    error_message TEXT,
    callback_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_broadcaster_error_logs_task_id ON broadcaster_error_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_broadcaster_error_logs_created_at ON broadcaster_error_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_broadcaster_error_logs_error_type ON broadcaster_error_logs(error_type);
