#!/usr/bin/env python3
"""
RAG 知识库助手 - 数据库初始化脚本

用于初始化 SQLite 数据库，创建必要的表结构。

使用方法:
    python scripts/init_db.py

可选参数:
    --db-path: 指定数据库文件路径（默认从配置读取）
    --drop: 先删除现有表再重新创建（危险操作，仅用于开发）
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.db.database import Database, init_database


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="初始化 RAG 知识库助手数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/init_db.py                    # 初始化数据库
  python scripts/init_db.py --drop             # 删除并重新创建表
  python scripts/init_db.py --db-path ./my.db  # 指定数据库路径
        """,
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="数据库文件路径（默认从配置读取）",
    )
    
    parser.add_argument(
        "--drop",
        action="store_true",
        help="先删除现有表再重新创建（危险操作）",
    )
    
    args = parser.parse_args()
    
    # 转换路径
    db_path = Path(args.db_path) if args.db_path else None
    
    try:
        # 创建 Database 实例
        if db_path:
            db = Database(db_path)
        else:
            db = Database()
        
        print(f"数据库路径: {db.db_path}")
        
        # 如果需要，先删除现有表
        if args.drop:
            print("⚠️  正在删除现有表...")
            db.drop_tables()
            print("✅ 现有表已删除")
        
        # 初始化表结构
        print("正在创建表结构...")
        db.init_tables()
        
        print("✅ 数据库初始化成功！")
        print("\n已创建以下表：")
        print("  - documents: 文档元信息")
        print("  - conversations: 对话记录")
        print("  - messages: 消息记录")
        
        # 显示数据库统计信息
        stats = db.get_document_stats()
        print(f"\n当前统计：")
        print(f"  文档数: {stats['total_documents']}")
        print(f"  分块数: {stats['total_chunks']}")
        print(f"  总大小: {stats['total_size'] / 1024 / 1024:.2f} MB")
        
        db.close()
        return 0
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
