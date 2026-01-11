
# 数据库统一管理器迁移指南

## 概述
本指南将帮助您安全地将现有代码迁移到新的统一数据库管理器。

## 当前使用情况分析
- 使用 OldDatabaseManager 的文件: 24 个
- 需要迁移的总文件数: 24

## 迁移步骤

### 阶段1: 准备工作
1. 备份整个项目
2. 确保所有测试通过
3. 查看本迁移报告

### 阶段2: 逐步迁移
按照以下顺序迁移文件:

1. test_step2.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

2. test_step5.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

3. test_step5_simple.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

4. backend\api\file.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

5. backend\api\search_save_services.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

6. backend\database\adapters.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

7. backend\database\export.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

8. backend\database\unified_manager.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

9. backend\models\database_manager.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

10. backend\service\non_financial_table_service.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

11. backend\service\table_llm_service.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

12. test_step2.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

13. test_step5.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

14. test_step5_simple.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

15. backend\api\convert_apis.py
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

16. backend\api\convert\database_handler.py
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

17. backend\api\convert\progress_manager.py
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

18. backend\api\convert\table_processor.py
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

19. backend\api\convert\__init__.py
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

20. backend\database\adapters.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

21. backend\database\export.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

22. backend\database\unified_manager.py
   - 替换为 from database.export import OldDatabaseManagerAdapter
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

23. backend\models\new_database.py
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes

24. backend\models\unified_db.py
   - 替换为 from database.export import NewDatabaseManagerAdapter
   风险等级: low
   预计时间: 5-15 minutes


### 阶段3: 验证和清理
1. 运行完整测试套件
2. 验证所有功能正常
3. 清理备份文件
4. 更新项目文档

## 紧急回滚
如果迁移过程中出现问题，可以:
1. 使用git回滚: `git reset --hard HEAD`
2. 恢复备份文件
3. 联系开发团队

## 支持
如有问题，请参考:
- 统一数据库管理器文档
- 迁移工具使用说明
- 团队技术支持
