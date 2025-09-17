from flask import Blueprint, render_template, request, session, redirect, url_for,send_file,jsonify,flash
from app.db import get_db_connection
from datetime import datetime
from collections import defaultdict
from decimal import Decimal  
from app.utils import *


member=Blueprint('member', __name__,url_prefix='/member')
@member.route('/dashboard', methods=['GET', 'POST'])
def member_dashboard():
    if session.get('role') != 'member':
        return redirect(url_for('auth.login_member'))

    months = generate_month_list()  # 生成下拉的月份
    records = []
    columns = []
    dept = None
    month = None

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

            query = f"SELECT * FROM {dept} WHERE 日期 >= ? AND 日期 < ? AND 姓名= ?"
    
            cursor.execute(query, (start_date, end_date, session['user']))
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
                #new_row = list(row)              # 先把整行复制出来
                if idx_total is not None and row[idx_total] is not None:        # 有“总和”列才处理
                    new_row[idx_total] = round(row[idx_total], 1)
                records.append(new_row)

            columns=rename_columns(columns)
            conn.close()

    return render_template('member/dashboard.html', months=months, records=records, columns=columns,dept=dept,month=month)#最后两个参数是之前选择的部门和月份，用于保持选择

def generate_month_list():
    # 举例：生成近6个月（含当前月）的列表 ['2024-07', ..., '2023-08']
    now = datetime.now()
    return [(now.replace(day=1).replace(month=now.month - i) if now.month - i > 0
             else now.replace(day=1, year=now.year - 1, month=now.month - i + 6)).strftime("%Y-%m")
            for i in range(6)]

def build_summary_for_month(month_str):
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

    summary_dict = {
        "劳务费": Decimal("0.0"),
        "工作事项": []
    }

    conn = get_db_connection()
    cursor = conn.cursor()

    for t in tables:
        query = f"""
            SELECT {t['salary_field']} AS 工资, {t['work_field']} AS 工作
            FROM {t['name']}
            WHERE 日期 >= ? AND 日期 < ? AND 姓名 = ?
        """
        cursor.execute(query, (start_date, end_date, session['user']))
        rows = cursor.fetchall()

        for row in rows:
            salary = Decimal(str(row.工资 or "0.0"))
            summary_dict["劳务费"] += salary.quantize(Decimal("0.1"))

            if row.工作:
                tag = f"[{t['name']}]"
                summary_dict["工作事项"].append(f"{tag} {row.工作}")

    conn.close()

    # 构造输出结构（只返回一个字典的列表）
    summary = [{
        "劳务费": summary_dict["劳务费"],
        "工作事项": "\n".join(summary_dict["工作事项"])
    }]

    return summary

work_dict={
   "文案部": "推文内容",
   "编辑部":"工作内容",
   "影视部":"工作内容",
   "其他":"工作内容"
}
@member.route("/update_data", methods=["POST"])
def update_data():
    try:
        data = request.get_json(force=True)
        print("收到前端数据：", data)
        #data = request.json  # 一次性接收多个 row 的更新       
        department = data.get("department")
        updates = data.get("updates", [])

        # 校验
        if not updates:
            return jsonify({"status": "error", "message": "无更新数据"})

        conn = get_db_connection()
        cursor = conn.cursor()

        for row in updates:
            id = row.pop("id")            
            set_clauses = []
            values = []

            for front_col, val in row.items():
                # 前端列名 → 数据库字段名
                db_col = None
                for k, v in COLUMN_RENAME_MAP.items():
                    if v == front_col:
                        db_col = k
                        break
                if not db_col:
                    db_col = front_col  # 无映射则直接使用

                # 值反向映射                
                if val in ("是", "否") :                    
                    val = BOOL_MAP.get(val, val)
                elif val in("视频相关","拍摄"):
                    val = WORK_TYPE_MAP.get(val,val)
                elif db_col in("工作1","工作2"):
                    # 多选字段 → 转 int
                    selected = val.split(",")
                    val = labels_to_binary(selected)  # 你定义的函数

                #对列做类型转换，因为html自动全转换成了字符串
                if val!="None":
                    if db_col in ("字数"):
                        val = int(val) 
                    elif db_col in("工时","数量1","数量2","工时1","工时2","拍摄时长","整理时长","薪酬"):
                        val = float(val) 
                else:
                    val=None
                set_clauses.append(f"[{db_col}] = ?")
                values.append(val)
                #print("将更新的列:", set_clauses) 
            if department in work_dict:
               condition_col = work_dict[department]            
            sql = f"UPDATE [{department}] SET {', '.join(set_clauses)} WHERE id=?"#通过id找到需要更新的行
            values.append(id)
            print("执行的SQL:", sql)
            print("参数:", values)  # 包含SET的值和WHERE的条件值
            cursor.execute(sql, values)
        conn.commit()
        return jsonify({"status": "success"})

    except Exception as e:
        print("更新出错：", e)
        return jsonify({"status": "error", "message": str(e)})

@member.route('/delete_row', methods=['POST'])
def delete_row():
    try:
        row = request.get_json(force=True)   
        department = row.get("department",'')
        d_id = row.get("row_id", '')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM [{department}] WHERE id = ?", d_id)
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@member.route('/add_row', methods=['POST'])
def add_row():
    try:
        data = request.get_json(force=True)   
        department = data.get("department",'')
        name = session['user']
        month=data.get("month",'')
        n=data.get('rows_num','')
        conn = get_db_connection()
        cursor = conn.cursor()
        for i in range(n):
           cursor.execute(f" INSERT INTO [{department}] (姓名,日期) VALUES (?,?)", (name,f"{month}-01"))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500