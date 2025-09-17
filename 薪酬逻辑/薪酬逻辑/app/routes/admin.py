from flask import Blueprint, render_template, request, session, redirect, url_for,send_file,jsonify
from app.db import get_db_connection
from datetime import datetime
import pandas as pd
import io
import zipfile
from io import BytesIO
from collections import defaultdict
from decimal import Decimal   
from app.utils import *

admin=Blueprint('admin', __name__,url_prefix='/admin')
@admin.route('/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login_admin'))

    months = generate_month_list()  # 生成下拉的月份
    records = []
    columns = []
    dept=None
    month=None

    if request.method == 'POST':

        dept = request.form['department']
        month = request.form['month']  # 格式：2024-03

        if dept == "总计表格":#如果选择汇总表格
           raw_summary = build_summary_for_month(month)
           if raw_summary:
              summary_columns = list(raw_summary[0].keys())
              summary_records = [tuple(row.values()) for row in raw_summary]
           else:
              summary_columns, summary_records = [], []
           records = summary_records
           columns = summary_columns           

        else:
            # 转换为 datetime 对象以筛选
            start_date = datetime.strptime(month, "%Y-%m")
            end_date = datetime(start_date.year, start_date.month + 1, 1) if start_date.month < 12 else datetime(start_date.year + 1, 1, 1)

            conn = get_db_connection()
            cursor = conn.cursor()

            query = f"SELECT * FROM {dept} WHERE 日期 >= ? AND 日期 < ? ORDER BY 姓名"
    
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
                       
            idx_total = None
            if '总和' in columns:
                idx_total = columns.index('总和')
            else:
                idx_total = columns.index('薪酬')
          
            for row in rows:
                row_dict = dict(zip(columns, row))  # 将 pyodbc.Row 转成 dict
                renamed_row = map_values_for_display(row_dict)
                new_row = [renamed_row.get(col, '') for col in columns]  # 保持顺序

                #rename_row=map_values_for_display(row)
                #new_row = list(rename_row)              # 先把整行复制出来
                if idx_total is not None and row[idx_total]!=None:       # 有“总和”列才处理
                    new_row[idx_total] = round(row[idx_total], 1)
                records.append(new_row)
            
            columns=rename_columns(columns)
            conn.close()

    return render_template('admin/dashboard.html', months=months, records=records, columns=columns, dept=dept, month=month)

def generate_month_list():
    # 举例：生成近6个月（含当前月）的列表 ['2024-07', ..., '2023-08']
    now = datetime.now()
    return [(now.replace(day=1).replace(month=now.month - i) if now.month - i > 0
             else now.replace(day=1, year=now.year - 1, month=now.month - i + 6)).strftime("%Y-%m")
            for i in range(6)]

@admin.route('/export')
def export_zip():
    month = request.args.get("month")
    try:
        return generate_export_zip(month)
    except Exception as e:
        print("导出失败：", e)
        return "导出失败", 500

def disable(row,col,condition):
    if(condition):
       for c in col:
         row[c]=''

def generate_export_zip(month):
    conn = get_db_connection()
    cursor = conn.cursor()

    start_date = datetime.strptime(month, "%Y-%m")
    if start_date.month == 12:
        end_date = datetime(start_date.year + 1, 1, 1)
    else:
        end_date = datetime(start_date.year, start_date.month + 1, 1)

    tables = ["文案部", "编辑部", "影视部", "其他"]
    excel_data_main = {}

    for table_name in tables:
        query = f"SELECT * FROM {table_name} WHERE 日期 >= ? AND 日期 < ?"
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        rows = [list(row) for row in rows]
        columns = [col[0] for col in cursor.description]
        data=[]
        for row in rows:
            row_dict = dict(zip(columns, row))  # 将 pyodbc.Row 转成 dict
            renamed_row = map_values_for_display(row_dict)
            #将不可填写的数据赋值为空
            isAdopted = renamed_row.get('是否采用','')
            print(f"当前行数据: {renamed_row}")
            print(f"是否采纳: {isAdopted}")
            if (table_name == '文案部'):
                disable(renamed_row,['工时'], isAdopted == '是')
                disable(renamed_row,['字数'], isAdopted == '否')
            elif (table_name == '编辑部'): 
                isOriginal = renamed_row.get('是否原创','')
                disable(renamed_row,['工时'], isAdopted == '是')
                disable(renamed_row,['是否原创'], isAdopted == '否')
                disable(renamed_row,['字数', '数量1', '好评1', '数量2', '好评2', '工时1'], (isAdopted == '否' or isOriginal == '否'))          
            elif (table_name == '影视部'):
                workType = renamed_row.get('工作类型','')
                disable(renamed_row,['拍摄时长', '整理时长'], (workType == '视频相关' or isAdopted == '否'))
                disable(renamed_row,['工作1', '工作2', '视频时长', '视频单价'], (workType == '拍摄' or isAdopted == '否'))
                disable(renamed_row,['工时'], isAdopted == '是')
                disable(renamed_row,['工作类型'], isAdopted == '否')
            print(f"处理之后的数据: {renamed_row}")
            new_row = [renamed_row.get(col, '') for col in columns]  # 转化成列表
            data.append(new_row)
        columns=rename_columns(columns)
        df = pd.DataFrame(data, columns=columns)
        excel_data_main[table_name] = df

    # 总计表格
    summary_data = build_summary_for_month(month)
    df_summary = pd.DataFrame(summary_data) if summary_data else pd.DataFrame()

    # ========== 生成两个 Excel 文件为 Bytes ==========
    buffer_salary = BytesIO()
    with pd.ExcelWriter(buffer_salary, engine='openpyxl') as writer:
        for sheet_name, df in excel_data_main.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    buffer_salary.seek(0)

    buffer_summary = BytesIO()
    with pd.ExcelWriter(buffer_summary, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name="总计表格", index=False)
    buffer_summary.seek(0)

    # ========== 打包成 ZIP ==========
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr(f"salary_{month}.xlsx", buffer_salary.read())
        zipf.writestr(f"学生劳务费_{month}.xlsx", buffer_summary.read())

    zip_buffer.seek(0)
    zip_filename = f"salary_export_{month}.zip"

    return send_file(
        zip_buffer,
        download_name=zip_filename,
        as_attachment=True,
        mimetype='application/zip'
    )

def build_summary_for_month(month_str):
    """
    输入：2024-03
    输出：一个 list，每个元素是一个人的总计信息，包括：学号、姓名、劳务费、工作事项
    """
    start_date = datetime.strptime(month_str, "%Y-%m")
    if start_date.month == 12:
        end_date = datetime(start_date.year + 1, 1, 1)
    else:
        end_date = datetime(start_date.year, start_date.month + 1, 1)

    tables = [
        {"name": "文案部", "salary_field": "总和", "work_field": "推文内容"},
        {"name": "编辑部", "salary_field": "总和", "work_field": "工作内容"},
        {"name": "影视部", "salary_field": "总和", "work_field": "工作内容"},
        {"name": "其他",   "salary_field": "薪酬", "work_field": "工作内容"},
    ]

    summary_dict = defaultdict(lambda: {"姓名": "", "学号": "", "劳务费": 0, "工作事项": []})

    conn = get_db_connection()
    cursor = conn.cursor()

    all_names_set = set()

    # 逐表查询并聚合
    for t in tables:
        query = f"""
            SELECT 姓名, {t['salary_field']} AS 工资, {t['work_field']} AS 工作
            FROM {t['name']}
            WHERE 日期 >= ? AND 日期 < ?
        """
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()

        for row in rows:
            name = row.姓名
            all_names_set.add(name)

            summary_dict[name]["姓名"] = name
            summary_dict[name]["劳务费"] +=round(Decimal(str( row.工资 or 0)),1)

            if row.工作:
                tag = f"[{t['name']}]"
                summary_dict[name]["工作事项"].append(f"{tag} {row.工作}")

    # 一次性查所有姓名的学号
    if all_names_set:
        placeholders = ','.join(['?'] * len(all_names_set))
        name_list = list(all_names_set)

        cursor.execute(
            f"SELECT 姓名, 学号 FROM 成员 WHERE 姓名 IN ({placeholders})",
            name_list
        )
        for row in cursor.fetchall():
            summary_dict[row.姓名]["学号"] = row.学号

    conn.close()

    # 最终输出结构
    summary = []
    for item in summary_dict.values():
        item["工作事项"] = "\n".join(item["工作事项"])
        summary.append(item)

    return summary

@admin.route('/multidelete',methods=['POST'])
def multidelete():
    try:
        months= request.get_json(force=True)['month_delete']
        department=['文案部','编辑部','影视部','其他']
        conn = get_db_connection()
        cursor = conn.cursor()
        for month in months:
            for dept in department:
                cursor.execute(
                    f"DELETE FROM [{dept}] WHERE 日期 LIKE ?",
                    (f"{month}%",)
                )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500