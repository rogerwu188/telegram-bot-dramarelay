-- 每日汇总统计系统数据库变更
-- 创建时间: 2024-12-10
-- 用途: 支持每日汇总数据回传功能

-- 1. 在 users 表增加 agent_node 字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS agent_node VARCHAR(255);
COMMENT ON COLUMN users.agent_node IS '代理节点标识，用于X2C平台分账';

-- 2. 创建 task_daily_stats 表
CREATE TABLE IF NOT EXISTS task_daily_stats (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES drama_tasks(task_id) ON DELETE CASCADE,
    project_id VARCHAR(255),
    external_task_id INTEGER,
    stats_date DATE NOT NULL,
    
    -- 总体统计
    total_account_count INTEGER DEFAULT 0,
    total_completion_count INTEGER DEFAULT 0,
    
    -- YouTube 统计
    yt_account_count INTEGER DEFAULT 0,
    yt_view_count BIGINT DEFAULT 0,
    yt_like_count BIGINT DEFAULT 0,
    yt_comment_count BIGINT DEFAULT 0,
    
    -- TikTok 统计
    tt_account_count INTEGER DEFAULT 0,
    tt_view_count BIGINT DEFAULT 0,
    tt_like_count BIGINT DEFAULT 0,
    tt_comment_count BIGINT DEFAULT 0,
    
    -- 抖音 统计
    dy_account_count INTEGER DEFAULT 0,
    dy_view_count BIGINT DEFAULT 0,
    dy_like_count BIGINT DEFAULT 0,
    dy_comment_count BIGINT DEFAULT 0,
    dy_share_count BIGINT DEFAULT 0,
    dy_collect_count BIGINT DEFAULT 0,
    
    -- 回传状态
    webhook_sent BOOLEAN DEFAULT FALSE,
    webhook_sent_at TIMESTAMP,
    webhook_response TEXT,
    webhook_retry_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束：每个任务每天只有一条记录
    UNIQUE(task_id, stats_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_task_daily_stats_task_id ON task_daily_stats(task_id);
CREATE INDEX IF NOT EXISTS idx_task_daily_stats_project_id ON task_daily_stats(project_id);
CREATE INDEX IF NOT EXISTS idx_task_daily_stats_date ON task_daily_stats(stats_date);
CREATE INDEX IF NOT EXISTS idx_task_daily_stats_webhook_sent ON task_daily_stats(webhook_sent);

-- 添加注释
COMMENT ON TABLE task_daily_stats IS '任务每日汇总统计表';
COMMENT ON COLUMN task_daily_stats.task_id IS 'Bot内部任务ID';
COMMENT ON COLUMN task_daily_stats.project_id IS 'X2C项目ID';
COMMENT ON COLUMN task_daily_stats.external_task_id IS 'X2C任务ID';
COMMENT ON COLUMN task_daily_stats.stats_date IS '统计日期';
COMMENT ON COLUMN task_daily_stats.total_account_count IS '当日完成账号总数';
COMMENT ON COLUMN task_daily_stats.total_completion_count IS '当日完成次数';
COMMENT ON COLUMN task_daily_stats.webhook_sent IS '是否已回传';
COMMENT ON COLUMN task_daily_stats.webhook_sent_at IS '回传时间';
