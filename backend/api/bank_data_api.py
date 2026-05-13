# -*- coding: utf-8 -*-
"""
银行数据查询API

提供银行数据仓库的RESTful API接口。

接口列表：
- GET  /api/bank/list           - 银行列表
- GET  /api/bank/search         - 搜索银行
- GET  /api/bank/<id>           - 银行详情
- GET  /api/bank/statistics     - 统计信息
- GET  /api/bank/<id>/reports   - 报告列表
- GET  /api/bank/report/<id>    - 报告详情
- GET  /api/bank/analysis/trend - 指标趋势
- GET  /api/bank/analysis/compare - 多银行对比
- GET  /api/bank/analysis/ranking - 指标排名
- GET  /api/bank/export/bank/<id> - 导出银行数据
- POST /api/bank/export/compare  - 导出对比数据

作者：DocuVista Team
版本：1.0.0
"""

from flask import Blueprint, jsonify, request
from backend.services.bank_data_service import BankDataService

# 创建蓝图
bank_data_bp = Blueprint('bank_data', __name__, url_prefix='/api/bank')

# 初始化服务
bank_data_service = BankDataService()


# ============================================================
# 数据库初始化/种子数据接口
# ============================================================

@bank_data_bp.route('/seed', methods=['POST'])
def seed_demo_data():
    """
    写入演示种子数据（12家上市银行2020-2024年财务数据）

    Query参数：
    - force: 是否强制重新写入（true/false，默认false）
    """
    force = request.args.get('force', 'false').lower() == 'true'

    try:
        from backend.database.bank_warehouse.seed_data import seed_database
        result = seed_database(force_reseed=force)
        return jsonify({
            'success': True,
            'message': '种子数据写入完成',
            'data': result
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================
# 银行信息接口
# ============================================================

@bank_data_bp.route('/list', methods=['GET'])
def get_bank_list():
    """
    获取银行列表

    Query参数：
    - bank_type: 银行类型筛选
    - listed_only: 仅返回已上市（true/false）
    - page: 页码（默认1）
    - page_size: 每页数量（默认20）
    """
    bank_type = request.args.get('bank_type')
    listed_only = request.args.get('listed_only', 'true').lower() == 'true'
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))

    banks = bank_data_service.get_all_banks(
        bank_type=bank_type,
        listed_only=listed_only
    )

    # 分页
    total = len(banks)
    start = (page - 1) * page_size
    end = start + page_size
    banks_page = banks[start:end]

    return jsonify({
        'success': True,
        'data': {
            'items': banks_page,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    })


@bank_data_bp.route('/search', methods=['GET'])
def search_banks():
    """
    搜索银行

    Query参数：
    - keyword: 搜索关键词
    - limit: 返回数量（默认20）
    """
    keyword = request.args.get('keyword', '')
    limit = int(request.args.get('limit', 20))

    if not keyword:
        return jsonify({
            'success': False,
            'error': 'keyword参数不能为空'
        })

    banks = bank_data_service.search_banks(keyword)[:limit]

    return jsonify({
        'success': True,
        'data': banks,
        'count': len(banks)
    })


@bank_data_bp.route('/<int:bank_id>', methods=['GET'])
def get_bank_detail(bank_id):
    """
    获取银行详细信息
    """
    bank = bank_data_service.get_bank_detail(bank_id)

    if not bank:
        return jsonify({
            'success': False,
            'error': '银行不存在'
        }), 404

    return jsonify({
        'success': True,
        'data': bank
    })


@bank_data_bp.route('/statistics', methods=['GET'])
def get_bank_statistics():
    """
    获取银行统计信息
    """
    stats = bank_data_service.get_bank_statistics()

    return jsonify({
        'success': True,
        'data': stats
    })


# ============================================================
# 报告信息接口
# ============================================================

@bank_data_bp.route('/<int:bank_id>/reports', methods=['GET'])
def get_bank_reports(bank_id):
    """
    获取银行的报告列表
    """
    report_type = request.args.get('report_type')
    year = request.args.get('year', type=int)

    reports = bank_data_service.get_bank_reports(
        bank_id=bank_id,
        report_type=report_type,
        year=year
    )

    return jsonify({
        'success': True,
        'data': reports,
        'count': len(reports)
    })


@bank_data_bp.route('/report/<int:report_id>', methods=['GET'])
def get_report_detail(report_id):
    """
    获取报告详细信息
    """
    report = bank_data_service.get_report_detail(report_id)

    if not report:
        return jsonify({
            'success': False,
            'error': '报告不存在'
        }), 404

    return jsonify({
        'success': True,
        'data': report
    })


@bank_data_bp.route('/report/<int:report_id>/tables', methods=['GET'])
def get_report_tables(report_id):
    """
    获取报告包含的表格列表
    """
    tables = bank_data_service.get_report_tables(report_id)

    return jsonify({
        'success': True,
        'data': tables,
        'count': len(tables)
    })


# ============================================================
# 表格数据接口
# ============================================================

@bank_data_bp.route('/report/<int:report_id>/table/indicators', methods=['GET'])
def get_table_indicators(report_id):
    """
    获取表格指标数据
    Query参数：
    - table_name: 表格名称（必需）
    """
    table_name = request.args.get('table_name')
    
    if not table_name:
        return jsonify({
            'success': False,
            'error': 'table_name参数不能为空'
        }), 400
    
    indicators = bank_data_service.get_table_indicators(
        report_id=report_id,
        table_name=table_name
    )
    
    return jsonify({
        'success': True,
        'data': indicators,
        'count': len(indicators)
    })


@bank_data_bp.route('/report/<int:report_id>/indicator', methods=['GET'])
def get_indicator_value(report_id):
    """
    获取指定指标的值
    """
    indicator_name = request.args.get('indicator_name')

    if not indicator_name:
        return jsonify({
            'success': False,
            'error': 'indicator_name参数不能为空'
        })

    indicator = bank_data_service.get_indicator_value(
        report_id=report_id,
        indicator_name=indicator_name
    )

    if not indicator:
        return jsonify({
            'success': False,
            'error': '指标不存在'
        }), 404

    return jsonify({
        'success': True,
        'data': indicator
    })


# ============================================================
# 分析查询接口
# ============================================================

@bank_data_bp.route('/analysis/trend', methods=['GET'])
def get_indicator_trend():
    """
    获取指标趋势
    """
    bank_id = request.args.get('bank_id', type=int)
    indicator_name = request.args.get('indicator_name')
    years_str = request.args.get('years')

    if not bank_id or not indicator_name:
        return jsonify({
            'success': False,
            'error': 'bank_id和indicator_name参数不能为空'
        })

    years = None
    if years_str:
        years = [int(y.strip()) for y in years_str.split(',')]

    trend = bank_data_service.get_indicator_trend(
        bank_id=bank_id,
        indicator_name=indicator_name,
        years=years
    )

    return jsonify({
        'success': True,
        'data': trend
    })


@bank_data_bp.route('/analysis/quarter-trend', methods=['GET'])
def get_quarter_trend():
    """
    获取季度指标趋势 - 直接从Excel读取季度数据
    """
    bank_id = request.args.get('bank_id', type=int)
    indicator_name = request.args.get('indicator_name')

    if not bank_id:
        return jsonify({
            'success': False,
            'error': 'bank_id参数不能为空'
        })

    try:
        from backend.services.bank_data_service import BankDataService
        service = BankDataService()
        trend = service.get_quarter_trend(bank_id, indicator_name)
        return jsonify({
            'success': True,
            'data': trend
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        })


@bank_data_bp.route('/analysis/compare', methods=['GET'])
def get_multiple_banks_indicator():
    """
    多银行指标对比
    """
    bank_ids_str = request.args.get('bank_ids')
    indicator_name = request.args.get('indicator_name')
    year = request.args.get('year', type=int)

    if not bank_ids_str or not indicator_name:
        return jsonify({
            'success': False,
            'error': 'bank_ids和indicator_name参数不能为空'
        })

    bank_ids = [int(bid.strip()) for bid in bank_ids_str.split(',')]

    results = bank_data_service.get_multiple_banks_indicator(
        bank_ids=bank_ids,
        indicator_name=indicator_name,
        year=year
    )

    return jsonify({
        'success': True,
        'data': results,
        'count': len(results)
    })


@bank_data_bp.route('/analysis/ranking', methods=['GET'])
def get_indicator_ranking():
    """
    指标排名
    """
    indicator_name = request.args.get('indicator_name')
    year = request.args.get('year', type=int)
    bank_type = request.args.get('bank_type')
    limit = int(request.args.get('limit', 20))

    if not indicator_name:
        return jsonify({
            'success': False,
            'error': 'indicator_name参数不能为空'
        })

    ranking = bank_data_service.get_indicator_ranking(
        indicator_name=indicator_name,
        year=year,
        bank_type=bank_type,
        limit=limit
    )

    return jsonify({
        'success': True,
        'data': ranking,
        'count': len(ranking)
    })


# ============================================================
# 数据导出接口
# ============================================================

@bank_data_bp.route('/export/bank/<int:bank_id>', methods=['GET'])
def export_bank_full_data(bank_id):
    """
    导出银行完整数据
    """
    data = bank_data_service.export_bank_full_data(bank_id)

    if not data:
        return jsonify({
            'success': False,
            'error': '银行不存在'
        }), 404

    return jsonify({
        'success': True,
        'data': data
    })


@bank_data_bp.route('/export/compare', methods=['POST'])
def export_indicator_comparison():
    """
    导出多银行多指标对比数据
    """
    body = request.get_json()

    if not body:
        return jsonify({
            'success': False,
            'error': '请求体不能为空'
        }), 400

    bank_ids = body.get('bank_ids', [])
    indicator_names = body.get('indicator_names', [])
    year = body.get('year')

    if not bank_ids or not indicator_names:
        return jsonify({
            'success': False,
            'error': 'bank_ids和indicator_names参数不能为空'
        })

    data = bank_data_service.export_indicator_comparison(
        bank_ids=bank_ids,
        indicator_names=indicator_names,
        year=year
    )

    return jsonify({
        'success': True,
        'data': data
    })


# ============================================================
# 数据溯源接口
# ============================================================

@bank_data_bp.route('/data/<int:table_data_id>/sources', methods=['GET'])
def get_data_sources(table_data_id):
    """
    获取数据溯源信息
    """
    sources = bank_data_service.get_data_sources(table_data_id)

    return jsonify({
        'success': True,
        'data': sources,
        'count': len(sources)
    })


@bank_data_bp.route('/data/<int:table_data_id>/versions', methods=['GET'])
def get_data_versions(table_data_id):
    """
    获取数据版本历史
    """
    versions = bank_data_service.get_data_versions(table_data_id)

    return jsonify({
        'success': True,
        'data': versions,
        'count': len(versions)
    })


# ============================================================
# Excel 文件审核状态接口
# ============================================================

@bank_data_bp.route('/excel/list', methods=['GET'])
def get_excel_files():
    """
    获取 Excel 文件列表（支持审核状态筛选）

    Query参数：
    - page: 页码（默认1）
    - page_size: 每页数量（默认20）
    - filename: 文件名筛选
    - uploader_name: 上传人筛选
    - start_date: 开始日期
    - end_date: 结束日期
    - review_status: 审核状态 (auto/pending_review/reviewed/needs_reprocess)
    """
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))

    filters = {}
    if request.args.get('filename'):
        filters['filename'] = request.args.get('filename')
    if request.args.get('uploader_name'):
        filters['uploader_name'] = request.args.get('uploader_name')
    if request.args.get('start_date'):
        filters['start_date'] = request.args.get('start_date')
    if request.args.get('end_date'):
        filters['end_date'] = request.args.get('end_date')
    if request.args.get('review_status'):
        filters['review_status'] = request.args.get('review_status')

    # 使用带审核状态的查询方法
    result = bank_data_service.get_excel_files_with_review_status(filters, page, page_size)

    if result[0]:
        return jsonify({
            'success': True,
            'data': result[1]
        })
    else:
        return jsonify({
            'success': False,
            'error': result[1]
        }), 500


@bank_data_bp.route('/excel/<int:file_id>/review', methods=['POST'])
def update_excel_review(file_id):
    """
    更新 Excel 文件的审核状态

    请求体：
    {
        "review_status": "reviewed" | "needs_reprocess" | "auto",
        "review_issues": ["问题1", "问题2"],
        "reviewed_by": "审核人名称"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'error': '请求体不能为空'
        }), 400

    review_status = data.get('review_status')
    if not review_status:
        return jsonify({
            'success': False,
            'error': 'review_status 不能为空'
        }), 400

    # 验证审核状态值
    valid_statuses = ['auto', 'pending_review', 'reviewed', 'needs_reprocess']
    if review_status not in valid_statuses:
        return jsonify({
            'success': False,
            'error': f'review_status 必须是以下值之一: {valid_statuses}'
        }), 400

    review_issues = data.get('review_issues', [])
    reviewed_by = data.get('reviewed_by', '系统用户')

    # 更新审核状态
    result = bank_data_service.update_excel_review_status(
        file_id=file_id,
        review_status=review_status,
        review_issues=review_issues,
        reviewed_by=reviewed_by
    )

    if result[0]:
        return jsonify({
            'success': True,
            'message': result[1]
        })
    else:
        return jsonify({
            'success': False,
            'error': result[1]
        }), 400


@bank_data_bp.route('/excel/<int:file_id>', methods=['GET'])
def get_excel_file(file_id):
    """
    获取 Excel 文件详情
    """
    result = bank_data_service.get_excel_file_detail(file_id)

    if result[0]:
        return jsonify({
            'success': True,
            'data': result[1]
        })
    else:
        return jsonify({
            'success': False,
            'error': result[1]
        }), 404


@bank_data_bp.route('/excel/<int:file_id>/detect', methods=['POST'])
def detect_excel_anomalies(file_id):
    """
    重新检测 Excel 文件的异常

    POST /api/bank/excel/<id>/detect
    """
    try:
        result = bank_data_service.detect_excel_anomalies(file_id)

        if result[0]:
            return jsonify({
                'success': True,
                'data': result[1]
            })
        else:
            return jsonify({
                'success': False,
                'error': result[1]
            }), 400
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bank_data_bp.route('/excel/detect-batch', methods=['POST'])
def batch_detect_excel_anomalies():
    """
    批量检测 Excel 文件异常

    POST /api/bank/excel/detect-batch
    Body (可选):
    {
        "file_ids": [1, 2, 3]  // 如果为空则检测所有文件
    }
    """
    try:
        data = request.get_json() or {}
        file_ids = data.get('file_ids')

        result = bank_data_service.batch_detect_excel_anomalies(file_ids)

        if result[0]:
            return jsonify({
                'success': True,
                'data': result[1]
            })
        else:
            return jsonify({
                'success': False,
                'error': result[1]
            }), 400
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
