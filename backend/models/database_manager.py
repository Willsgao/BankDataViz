#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
@Project    ：DocuVista
@File       ：database_manager.py
@Author     ：IronmanJay
@Date       ：2025/7/28 13:30
@Describe   ：数据库管理工具
"""

import sqlite3
import os
from datetime import datetime
import sys
from backend.configs.config import config



class OldDatabaseManager:
    def __init__(self, db_path='data/database.db'):
        self.db_path = db_path or config.DATABASE_PATH
        self.uploads_dir = '../static/uploads'
        print("self.uploads_dir>>>>>>>:", self.uploads_dir)

        # 确保所有目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)

    def connect(self):
        """
        链接数据库
        :return: 是否连接成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ 数据库连接错误: {e}")
            return None

    def init_database(self):
        """
        初始化数据库（兼容旧库，自动补列）
        :return: 初始化是否成功
        """
        conn = self.connect()
        if conn is None:
            return False

        try:
            c = conn.cursor()

            # 1. 创建 texts 表（保持不变）
            c.execute('''CREATE TABLE IF NOT EXISTS texts
                         (id      INTEGER PRIMARY KEY AUTOINCREMENT,
                          content TEXT)''')

            # 2. 创建/升级 files 表（含软删除字段）
            c.execute('''CREATE TABLE IF NOT EXISTS files
                         (id           INTEGER PRIMARY KEY AUTOINCREMENT,
                          filename     TEXT NOT NULL UNIQUE,
                          file_type    TEXT NOT NULL,
                          raw_filename TEXT,              -- 原始中文文件名
                          created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          deleted      INTEGER   DEFAULT 0)''')
            # -- 软删除标志

            # 3. 旧库兼容：依次补列
            c.execute("PRAGMA table_info(files)")
            cols = [col[1] for col in c.fetchall()]
            if 'raw_filename' not in cols:
                c.execute("ALTER TABLE files ADD COLUMN raw_filename TEXT")
                print("✅ 已自动为旧库添加 raw_filename 字段")
            if 'deleted' not in cols:
                c.execute("ALTER TABLE files ADD COLUMN deleted INTEGER DEFAULT 0")
                print("✅ 已自动为旧库添加 deleted 字段")

            # 4. 文本表处理 - 修改这里！！！
            # 只确保至少有一条记录，不删除已有数据
            c.execute("SELECT COUNT(*) FROM texts")
            count = c.fetchone()[0]

            if count == 0:
                # 如果表是空的，插入一条记录
                c.execute("INSERT INTO texts (content) VALUES (?)", ("",))
                print("✅ 文本表为空，插入一条空记录")
            # 如果已经有数据，什么也不做，保持现有数据

            conn.commit()
            print("✅ 数据库初始化完成")
            return True
        except sqlite3.Error as e:
            print(f"❌ 数据库初始化错误: {e}")
            return False
        finally:
            conn.close()


    def read_database(self):
        """
        读取数据库内容
        :return: None
        """
        print("\n===== 数据库内容读取器 =====")
        print(f"读取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        conn = self.connect()
        if conn is None:
            return

        try:
            c = conn.cursor()

            # 富文本内容
            print("\n===== 富文本内容 =====")
            c.execute("SELECT * FROM texts")
            texts = c.fetchall()
            for text in texts:
                content = text["content"] or ""
                print(f"ID: {text['id']}")
                print(f"内容长度: {len(content)} 字符")
                print(f"内容预览: {content[:100]}{'...' if len(content) > 100 else ''}")
                print("-" * 50)

            # 文件记录
            print("\n===== 文件记录 =====")
            c.execute("SELECT id, filename, raw_filename, file_type, created_at FROM files ORDER BY created_at DESC")
            files = c.fetchall()

            if not files:
                print("文件表中没有记录")
            else:
                for file in files:
                    file_path = os.path.join(self.uploads_dir, file["filename"])
                    exists = "✅ 存在" if os.path.exists(file_path) else "❌ 缺失"
                    display_name = file["raw_filename"] or file["filename"]  # 优先中文
                    print(f"ID: {file['id']}, 文件名: {display_name}, "
                          f"类型: {file['file_type']}, 上传时间: {file['created_at']}, "
                          f"文件状态: {exists}")

            # 统计信息
            print("\n===== 数据库统计 =====")
            c.execute("SELECT COUNT(*) FROM texts")
            texts_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM files")
            files_count = c.fetchone()[0]

            actual_files = set(os.listdir(self.uploads_dir))
            db_files = set(file["filename"] for file in files)

            print(f"富文本记录: {texts_count} 条")
            print(f"文件记录: {files_count} 条")
            print(f"实际存储的文件: {len(actual_files)} 个")
            print(f"记录中缺失的文件: {len(db_files - actual_files)} 个")
            print(f"未记录的额外文件: {len(actual_files - db_files)} 个")

        except sqlite3.Error as e:
            print(f"❌ 读取数据库错误: {e}")
        finally:
            conn.close()

        print("\n读取完成！")

    def clear_all(self):
        """
        清空所有数据库记录并删除文件
        :return: None
        """
        if input("⚠️ 警告: 这将删除所有数据和文件。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        conn = self.connect()
        if conn is None:
            return

        try:
            c = conn.cursor()

            # 获取所有文件记录以便删除
            c.execute("SELECT filename FROM files")
            filenames = [row["filename"] for row in c.fetchall()]

            # 清空数据表
            c.execute("DELETE FROM texts")
            c.execute("DELETE FROM files")
            c.execute("DELETE FROM sqlite_sequence")

            conn.commit()
            print("✅ 数据库记录已清空")

            # 删除上传的文件
            self.delete_files(filenames)

        except sqlite3.Error as e:
            print(f"❌ 清空数据库错误: {e}")
            return False
        finally:
            conn.close()

    def clear_files(self):
        """
        删除所有上传文件并清空文件记录
        :return: None
        """
        if input("⚠️ 警告: 这将删除所有上传文件。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        conn = self.connect()
        if conn is None:
            return

        try:
            c = conn.cursor()

            # 获取所有文件记录以便删除
            c.execute("SELECT filename FROM files")
            filenames = [row["filename"] for row in c.fetchall()]

            # 清空文件表
            c.execute("DELETE FROM files")
            c.execute("DELETE FROM sqlite_sequence WHERE name='files'")

            conn.commit()
            print("✅ 文件记录已清空")

            # 删除上传的文件
            self.delete_files(filenames)

        except sqlite3.Error as e:
            print(f"❌ 清空文件错误: {e}")
            return False
        finally:
            conn.close()

    def clear_text(self):
        """
        清除富文本内容
        :return: None
        """
        if input("⚠️ 警告: 这将清除所有富文本内容。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        conn = self.connect()
        if conn is None:
            return

        try:
            c = conn.cursor()
            c.execute("UPDATE texts SET content = ?", ("",))
            conn.commit()
            print("✅ 富文本内容已清除")
        except sqlite3.Error as e:
            print(f"❌ 清除富文本内容错误: {e}")
        finally:
            conn.close()

    def delete_files(self, filenames=None):
        """
        删除指定的文件
        :param filenames: 要删除的文件名
        :return: None
        """
        if filenames is None:
            # 如果未指定文件名，则删除所有上传文件
            filenames = os.listdir(self.uploads_dir)

        deleted_count = 0
        error_count = 0

        for filename in filenames:
            file_path = os.path.join(self.uploads_dir, filename)
            try:
                if os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                    else:
                        print(f"⚠️ 不是文件: {file_path}")
                else:
                    print(f"⚠️ 文件不存在: {file_path}")
            except Exception as e:
                print(f"❌ 删除文件 {filename} 时出错: {e}")
                error_count += 1

        print(f"✅ 已删除 {deleted_count} 个文件，{error_count} 个失败")

    def vacuum_database(self):
        """
        优化数据库并减小文件大小
        :return: None
        """
        conn = self.connect()
        if conn is None:
            return

        try:
            conn.execute("VACUUM")
            print("✅ 数据库已优化")
        except sqlite3.Error as e:
            print(f"❌ 优化数据库时出错: {e}")
        finally:
            conn.close()


def show_database_info(db_manager):
    """
    显示数据库信息
    :param db_manager: 数据库管理器
    :return: None
    """
    db_size = os.path.getsize(db_manager.db_path) if os.path.exists(db_manager.db_path) else 0
    files_count = len(os.listdir(db_manager.uploads_dir))

    print("\n===== 数据库信息 =====")
    print(f"数据库路径: {db_manager.db_path}")
    print(f"数据库大小: {db_size / 1024:.1f} KB" if db_size else "数据库文件不存在")
    print(f"上传目录: {db_manager.uploads_dir}")
    print(f"上传文件数量: {files_count}")


def main():
    db_manager = OldDatabaseManager()

    # 确保数据库已初始化
    if not os.path.exists(db_manager.db_path):
        print(f"数据库文件不存在，正在初始化...")
        db_manager.init_database()
    else:
        # 检查是否需要优化
        db_size = os.path.getsize(db_manager.db_path)
        if db_size > 10 * 1024 * 1024:
            print("⚠️ 注意: 数据库文件较大，建议优化")

    # 主菜单
    while True:
        print("\n===== 数据库管理工具 =====")
        print("1. 查看数据库内容")
        print("2. 清除所有内容（文件和文本）")
        print("3. 清除所有文件（图片和PDF）")
        print("4. 清除富文本内容")
        print("5. 优化数据库")
        print("6. 显示数据库信息")
        print("7. 退出")

        choice = input("请选择操作 (1-7): ")

        if choice == "1":
            db_manager.read_database()
        elif choice == "2":
            db_manager.clear_all()
        elif choice == "3":
            db_manager.clear_files()
        elif choice == "4":
            db_manager.clear_text()
        elif choice == "5":
            if input("⚠️ 将锁定数据库进行优化，确认吗？(y/n): ").lower() == "y":
                db_manager.vacuum_database()
        elif choice == "6":
            show_database_info(db_manager)
        elif choice == "7":
            print("退出程序")
            break
        else:
            print("无效选择，请重新输入")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被中断")
        sys.exit(0)
