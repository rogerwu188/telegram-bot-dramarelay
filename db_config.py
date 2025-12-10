"""
数据库表名配置文件
Database Table Names Configuration

用途：统一管理所有数据库表名，便于将来修改和维护
Purpose: Centralized management of all database table names for easy modification and maintenance

使用方法：
    from db_config import TABLE_NAMES
    
    # 在SQL查询中使用
    query = f'SELECT * FROM {TABLE_NAMES["users"]}'
    
    # 或者直接导入
    from db_config import TG_BOT_USER_TABLE
    query = f'SELECT * FROM {TG_BOT_USER_TABLE}'
"""

# ========================================
# 表名常量定义
# Table Name Constants
# ========================================

# TG Bot 用户表
TG_BOT_USER_TABLE = '"TG_Bot_User"'

# 短剧任务表
DRAMA_TASKS_TABLE = 'drama_tasks'

# 用户任务关联表
USER_TASKS_TABLE = 'user_tasks'

# 用户邀请关系表
USER_INVITATIONS_TABLE = 'user_invitations'

# 推荐奖励记录表
REFERRAL_REWARDS_TABLE = 'referral_rewards'

# 提现记录表
WITHDRAWALS_TABLE = 'withdrawals'

# 空投快照表
AIRDROP_SNAPSHOTS_TABLE = 'airdrop_snapshots'

# ========================================
# 表名字典（推荐使用）
# Table Names Dictionary (Recommended)
# ========================================

TABLE_NAMES = {
    'users': TG_BOT_USER_TABLE,  # 注意：为了兼容性，key保持为'users'
    'tg_bot_user': TG_BOT_USER_TABLE,
    'drama_tasks': DRAMA_TASKS_TABLE,
    'user_tasks': USER_TASKS_TABLE,
    'user_invitations': USER_INVITATIONS_TABLE,
    'referral_rewards': REFERRAL_REWARDS_TABLE,
    'withdrawals': WITHDRAWALS_TABLE,
    'airdrop_snapshots': AIRDROP_SNAPSHOTS_TABLE,
}

# ========================================
# 辅助函数
# Helper Functions
# ========================================

def get_table_name(table_key):
    """
    获取表名
    
    Args:
        table_key (str): 表的键名，如 'users', 'drama_tasks'
    
    Returns:
        str: 实际的表名
    
    Example:
        >>> get_table_name('users')
        '"TG_Bot_User"'
    """
    return TABLE_NAMES.get(table_key, table_key)

def format_query(query_template, **table_keys):
    """
    格式化SQL查询，替换表名占位符
    
    Args:
        query_template (str): SQL查询模板
        **table_keys: 表名键值对
    
    Returns:
        str: 格式化后的SQL查询
    
    Example:
        >>> format_query(
        ...     'SELECT * FROM {users} WHERE user_id = %s',
        ...     users='users'
        ... )
        'SELECT * FROM "TG_Bot_User" WHERE user_id = %s'
    """
    replacements = {key: get_table_name(value) for key, value in table_keys.items()}
    return query_template.format(**replacements)

# ========================================
# 向后兼容性支持
# Backward Compatibility Support
# ========================================

# 为了保持向后兼容，提供旧的表名映射
LEGACY_TABLE_NAMES = {
    'users': 'users',  # 旧表名
}

def get_legacy_table_name(table_key):
    """
    获取旧的表名（用于迁移前的兼容）
    
    Args:
        table_key (str): 表的键名
    
    Returns:
        str: 旧的表名
    """
    return LEGACY_TABLE_NAMES.get(table_key, table_key)

# ========================================
# 使用示例
# Usage Examples
# ========================================

if __name__ == '__main__':
    print("=== 数据库表名配置 ===")
    print(f"TG Bot用户表: {TG_BOT_USER_TABLE}")
    print(f"短剧任务表: {DRAMA_TASKS_TABLE}")
    print(f"用户任务关联表: {USER_TASKS_TABLE}")
    print()
    
    print("=== 使用示例 ===")
    query1 = f'SELECT * FROM {TABLE_NAMES["users"]}'
    print(f"查询1: {query1}")
    
    query2 = format_query(
        'SELECT * FROM {users} JOIN {tasks} ON {users}.user_id = {tasks}.user_id',
        users='users',
        tasks='user_tasks'
    )
    print(f"查询2: {query2}")
