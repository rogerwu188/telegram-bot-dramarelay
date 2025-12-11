-- 创建webhook成功日志表
CREATE TABLE IF NOT EXISTS webhook_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER,
    task_title VARCHAR(500),
    project_id VARCHAR(100),
    callback_url TEXT,
    callback_status VARCHAR(50) DEFAULT 'success',
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_webhook_logs_task_id ON webhook_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_callback_status ON webhook_logs(callback_status);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_project_id ON webhook_logs(project_id);
