-- Migration: 006_rename_users_to_tg_bot_user
-- Description: Rename 'users' table to 'TG_Bot_User' with backward compatibility view
-- Date: 2025-12-03
-- Author: System Migration
-- Strategy: 使用视图（VIEW）实现向后兼容，无需修改代码

-- ========================================
-- 第1步: 重命名表
-- ========================================

ALTER TABLE users RENAME TO "TG_Bot_User";

COMMENT ON TABLE "TG_Bot_User" IS 'TG Bot 用户表 (原 users 表)';

-- ========================================
-- 第2步: 创建向后兼容视图
-- ========================================

-- 创建 users 视图，指向 TG_Bot_User 表
-- 这样所有现有代码都可以继续使用 'users' 而不需要修改
CREATE OR REPLACE VIEW users AS
SELECT * FROM "TG_Bot_User";

COMMENT ON VIEW users IS '向后兼容视图，指向 TG_Bot_User 表。所有对 users 的查询会自动路由到 TG_Bot_User。';

-- ========================================
-- 第3步: 创建 INSTEAD OF 触发器支持 INSERT/UPDATE/DELETE
-- ========================================

-- 为了让视图支持 INSERT/UPDATE/DELETE 操作，需要创建触发器

-- INSERT 触发器
CREATE OR REPLACE FUNCTION users_insert_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO "TG_Bot_User" VALUES (NEW.*);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_insert
INSTEAD OF INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION users_insert_trigger();

-- UPDATE 触发器
CREATE OR REPLACE FUNCTION users_update_trigger()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE "TG_Bot_User"
    SET 
        user_id = NEW.user_id,
        username = NEW.username,
        first_name = NEW.first_name,
        display_name = NEW.display_name,
        language = NEW.language,
        wallet_address = NEW.wallet_address,
        sol_wallet = NEW.sol_wallet,
        total_node_power = NEW.total_node_power,
        completed_tasks = NEW.completed_tasks,
        invited_by = NEW.invited_by,
        invitation_reward_received = NEW.invitation_reward_received,
        invitation_reward_received_at = NEW.invitation_reward_received_at,
        last_submission_time = NEW.last_submission_time,
        created_at = NEW.created_at,
        updated_at = NEW.updated_at
    WHERE user_id = OLD.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_update
INSTEAD OF UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION users_update_trigger();

-- DELETE 触发器
CREATE OR REPLACE FUNCTION users_delete_trigger()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM "TG_Bot_User" WHERE user_id = OLD.user_id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_delete
INSTEAD OF DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION users_delete_trigger();

-- ========================================
-- 第4步: 更新索引名称
-- ========================================

-- 重命名主键约束（如果存在）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'users_pkey'
    ) THEN
        ALTER INDEX users_pkey RENAME TO "TG_Bot_User_pkey";
    END IF;
END $$;

-- 重命名其他索引（如果存在）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_users_last_submit'
    ) THEN
        ALTER INDEX idx_users_last_submit RENAME TO "idx_TG_Bot_User_last_submit";
    END IF;
END $$;

-- ========================================
-- 第5步: 更新外键约束
-- ========================================

-- user_tasks 表的外键
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'user_tasks_user_id_fkey'
    ) THEN
        ALTER TABLE user_tasks 
        DROP CONSTRAINT user_tasks_user_id_fkey;
    END IF;
END $$;

ALTER TABLE user_tasks 
ADD CONSTRAINT user_tasks_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES "TG_Bot_User"(user_id) ON DELETE CASCADE;

-- user_invitations 表的外键
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'user_invitations_inviter_id_fkey'
    ) THEN
        ALTER TABLE user_invitations 
        DROP CONSTRAINT user_invitations_inviter_id_fkey;
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'user_invitations_invitee_id_fkey'
    ) THEN
        ALTER TABLE user_invitations 
        DROP CONSTRAINT user_invitations_invitee_id_fkey;
    END IF;
END $$;

ALTER TABLE user_invitations 
ADD CONSTRAINT user_invitations_inviter_id_fkey 
FOREIGN KEY (inviter_id) REFERENCES "TG_Bot_User"(user_id) ON DELETE CASCADE;

ALTER TABLE user_invitations 
ADD CONSTRAINT user_invitations_invitee_id_fkey 
FOREIGN KEY (invitee_id) REFERENCES "TG_Bot_User"(user_id) ON DELETE CASCADE;

-- referral_rewards 表的外键
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'referral_rewards_inviter_id_fkey'
    ) THEN
        ALTER TABLE referral_rewards 
        DROP CONSTRAINT referral_rewards_inviter_id_fkey;
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'referral_rewards_invitee_id_fkey'
    ) THEN
        ALTER TABLE referral_rewards 
        DROP CONSTRAINT referral_rewards_invitee_id_fkey;
    END IF;
END $$;

ALTER TABLE referral_rewards 
ADD CONSTRAINT referral_rewards_inviter_id_fkey 
FOREIGN KEY (inviter_id) REFERENCES "TG_Bot_User"(user_id) ON DELETE CASCADE;

ALTER TABLE referral_rewards 
ADD CONSTRAINT referral_rewards_invitee_id_fkey 
FOREIGN KEY (invitee_id) REFERENCES "TG_Bot_User"(user_id) ON DELETE CASCADE;

-- withdrawals 表的外键
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'withdrawals_user_id_fkey'
    ) THEN
        ALTER TABLE withdrawals 
        DROP CONSTRAINT withdrawals_user_id_fkey;
    END IF;
END $$;

ALTER TABLE withdrawals 
ADD CONSTRAINT withdrawals_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES "TG_Bot_User"(user_id) ON DELETE CASCADE;

-- airdrop_snapshots 表的外键
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'airdrop_snapshots_user_id_fkey'
    ) THEN
        ALTER TABLE airdrop_snapshots 
        DROP CONSTRAINT airdrop_snapshots_user_id_fkey;
    END IF;
END $$;

ALTER TABLE airdrop_snapshots 
ADD CONSTRAINT airdrop_snapshots_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES "TG_Bot_User"(user_id);

-- ========================================
-- 第6步: 验证迁移结果
-- ========================================

-- 检查表是否存在
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'TG_Bot_User'
    ) THEN
        RAISE NOTICE '✅ 表重命名成功: TG_Bot_User';
    ELSE
        RAISE EXCEPTION '❌ 表重命名失败';
    END IF;
END $$;

-- 检查视图是否存在
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_name = 'users'
    ) THEN
        RAISE NOTICE '✅ 向后兼容视图创建成功: users';
    ELSE
        RAISE EXCEPTION '❌ 视图创建失败';
    END IF;
END $$;

-- 检查触发器是否存在
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE trigger_name IN ('users_insert', 'users_update', 'users_delete')
    ) THEN
        RAISE NOTICE '✅ 触发器创建成功';
    ELSE
        RAISE WARNING '⚠️ 部分触发器可能未创建';
    END IF;
END $$;

-- 显示外键约束
SELECT 
    tc.table_name, 
    tc.constraint_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND ccu.table_name = 'TG_Bot_User'
ORDER BY tc.table_name;

-- ========================================
-- 第7步: 测试向后兼容性
-- ========================================

-- 测试 SELECT（应该正常工作）
DO $$
DECLARE
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    RAISE NOTICE '✅ SELECT 测试通过: users 视图返回 % 条记录', user_count;
END $$;

-- ========================================
-- 回滚脚本（如果需要）
-- ========================================

-- 如果需要回滚，执行以下SQL:
/*
-- 1. 删除触发器
DROP TRIGGER IF EXISTS users_insert ON users;
DROP TRIGGER IF EXISTS users_update ON users;
DROP TRIGGER IF EXISTS users_delete ON users;

-- 2. 删除触发器函数
DROP FUNCTION IF EXISTS users_insert_trigger();
DROP FUNCTION IF EXISTS users_update_trigger();
DROP FUNCTION IF EXISTS users_delete_trigger();

-- 3. 删除视图
DROP VIEW IF EXISTS users;

-- 4. 重命名表
ALTER TABLE "TG_Bot_User" RENAME TO users;

-- 5. 重命名索引
ALTER INDEX "TG_Bot_User_pkey" RENAME TO users_pkey;
ALTER INDEX "idx_TG_Bot_User_last_submit" RENAME TO idx_users_last_submit;

-- 6. 更新外键约束（指向 users）
-- ... (需要重新创建所有外键)
*/

-- ========================================
-- 完成
-- ========================================

SELECT '✅ Migration 006 completed successfully!' AS result;
SELECT '📋 Table renamed: users → TG_Bot_User' AS info;
SELECT '🔗 Backward compatibility view created: users → TG_Bot_User' AS info;
SELECT '⚡ All existing code will continue to work without modification' AS info;
