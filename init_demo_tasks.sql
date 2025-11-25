-- X2C DramaRelayBot - 添加演示任务
-- 在 Railway 数据库控制台中运行此脚本

-- 添加演示任务
INSERT INTO drama_tasks (title, description, duration, node_power_reward, platform_requirements, status)
VALUES 
    ('霸道总裁爱上我 EP01', '都市爱情短剧第一集，讲述霸道总裁与灰姑娘的浪漫邂逅', 15, 10, 'TikTok,YouTube,Instagram', 'active'),
    ('穿越之王妃驾到 EP01', '古装穿越剧，现代女孩穿越成为古代王妃', 20, 15, 'TikTok,YouTube,Instagram,Facebook', 'active'),
    ('重生之商业帝国 EP01', '商战题材，主角重生回到创业初期', 18, 12, 'TikTok,YouTube,Instagram', 'active'),
    ('都市修仙传 EP01', '现代修仙题材，都市中的修仙者', 25, 20, 'TikTok,YouTube,Instagram,Twitter', 'active'),
    ('豪门千金的复仇 EP01', '豪门恩怨，千金小姐的复仇之路', 16, 10, 'TikTok,YouTube,Instagram', 'active')
ON CONFLICT DO NOTHING;

-- 查询所有任务
SELECT task_id, title, description, duration, node_power_reward, platform_requirements, status, created_at
FROM drama_tasks
ORDER BY created_at DESC;
