#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分发数据回传功能测试脚本
"""

import asyncio
import sys

async def test_broadcast():
    """测试分发数据回传功能"""
    print("="*70)
    print("📡 分发数据回传功能测试")
    print("="*70)
    
    try:
        from stats_broadcaster import broadcast_all_tasks
        
        print("\n🚀 开始测试回传功能...")
        result = await broadcast_all_tasks()
        
        print("\n" + "="*70)
        print("📊 测试结果:")
        print("="*70)
        
        if result['success']:
            print(f"✅ 测试成功")
            print(f"📝 总任务数: {result['total']}")
            print(f"✅ 成功: {result['success_count']}")
            print(f"❌ 失败: {result['failed_count']}")
            print(f"⏰ 时间: {result['timestamp']}")
        else:
            print(f"❌ 测试失败")
            print(f"错误: {result.get('error', '未知错误')}")
        
        print("="*70)
        
        return result['success']
        
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_broadcast())
    sys.exit(0 if success else 1)
