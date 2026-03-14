#!/usr/bin/env python3
"""管理命令行工具"""

import argparse
import sys
from pathlib import Path

# 添加后端路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import SessionLocal, init_db
from app.models import APIKey


def create_key(args):
    """创建 API Key"""
    db = SessionLocal()
    try:
        key = APIKey(name=args.name, balance=args.balance)
        db.add(key)
        db.commit()
        print(f"✅ 创建成功!")
        print(f"   Key: {key.key}")
        print(f"   名称: {key.name}")
        print(f"   余额: {key.balance} 次")
    finally:
        db.close()


def recharge(args):
    """充值"""
    db = SessionLocal()
    try:
        key = db.query(APIKey).filter(APIKey.key == args.key).first()
        if not key:
            print(f"❌ API Key 不存在: {args.key}")
            return
        
        key.balance += args.amount
        db.commit()
        print(f"✅ 充值成功!")
        print(f"   Key: {key.key}")
        print(f"   充值: {args.amount} 次")
        print(f"   余额: {key.balance} 次")
    finally:
        db.close()


def balance(args):
    """查询余额"""
    db = SessionLocal()
    try:
        key = db.query(APIKey).filter(APIKey.key == args.key).first()
        if not key:
            print(f"❌ API Key 不存在: {args.key}")
            return
        
        print(f"📊 账户信息")
        print(f"   Key: {key.key}")
        print(f"   名称: {key.name}")
        print(f"   余额: {key.balance} 次")
        print(f"   已用: {key.total_used} 次")
        print(f"   状态: {'✅ 活跃' if key.is_active else '❌ 禁用'}")
    finally:
        db.close()


def list_keys(args):
    """列出所有 API Key"""
    db = SessionLocal()
    try:
        keys = db.query(APIKey).all()
        print(f"📋 共 {len(keys)} 个 API Key:\n")
        print(f"{'Key':<36} {'名称':<15} {'余额':>8} {'已用':>8} {'状态':<6}")
        print("-" * 80)
        for key in keys:
            status = "✅" if key.is_active else "❌"
            print(f"{key.key:<36} {key.name or '-':<15} {key.balance:>8} {key.total_used:>8} {status:<6}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="枕边书管理工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # create-key
    p_create = subparsers.add_parser("create-key", help="创建 API Key")
    p_create.add_argument("--name", default="默认", help="名称")
    p_create.add_argument("--balance", type=int, default=10, help="初始余额")
    p_create.set_defaults(func=create_key)
    
    # recharge
    p_recharge = subparsers.add_parser("recharge", help="充值")
    p_recharge.add_argument("--key", required=True, help="API Key")
    p_recharge.add_argument("--amount", type=int, required=True, help="充值次数")
    p_recharge.set_defaults(func=recharge)
    
    # balance
    p_balance = subparsers.add_parser("balance", help="查询余额")
    p_balance.add_argument("--key", required=True, help="API Key")
    p_balance.set_defaults(func=balance)
    
    # list
    p_list = subparsers.add_parser("list", help="列出所有 API Key")
    p_list.set_defaults(func=list_keys)
    
    args = parser.parse_args()
    
    if args.command:
        # 初始化数据库
        init_db()
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()