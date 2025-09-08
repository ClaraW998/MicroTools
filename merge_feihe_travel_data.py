import sys
import io
import csv
from typing import Optional, List, Dict, Tuple
import glob
import os
import pandas as pd

# ---------------- helper functions ----------------

def fetch_cell(row_slice: pd.Series, idx: Optional[int] or List[int]) -> Optional[str]:
    if idx is None:
        return ""
    if isinstance(idx, list):
        for i in idx:
            val = row_slice.iloc[i]
            if pd.notna(val) and str(val).strip():
                return str(val)
        return ""
    val = row_slice.iloc[idx]
    if pd.isna(val):
        return ""
    return str(val)

def to_date_str(val) -> str:
    if val is None or (isinstance(val, float) and (pd.isna(val) or val == 0)):
        return ""
    try:
        dt = pd.to_datetime(val, errors="coerce")
        if pd.isna(dt):
            return str(val)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(val)

def row_contains_target(row: pd.Series, target: str = "序号") -> bool:
    # 简单判定：行中是否有单元格等于目标文本
    for v in row:
        if pd.notna(v) and str(v).strip() == target:
            return True
    return False

def find_header_row(df: pd.DataFrame) -> Optional[int]:
    # 尝试定位包含“序号”的标题行
    for i in range(len(df)):
        row = df.iloc[i]
        if row_contains_target(row, "序号"):
            return i
    # 回退：若没有找到，返回首行（非空行）
    for i in range(len(df)):
        if not df.iloc[i].isna().all():
            return i
    return None

def normalize_header(header_row: pd.Series) -> List[str]:
    return [str(v).strip() for v in header_row.tolist()]

def locate_field_indices(header: List[str], field_candidates: Dict[str, List[str]]) -> Dict[str, Optional[int]]:
    # header: list of column header strings
    norm_header = [str(h).strip().lower() for h in header]
    idx_map: Dict[str, Optional[int]] = {}
    for field, candidates in field_candidates.items():
        found = []
        for cand in candidates:
            cand_lower = str(cand).strip().lower()
            for i, hv in enumerate(norm_header):
                if hv == cand_lower:
                    found.append(i)
        idx_map[field] = found
    return idx_map

def map_cost_center_from_row(row_slice: pd.Series,
                             cost_center_idx: Optional[int],
                             dept1_idx: Optional[int],
                             dept_in_idx: Optional[int],
                             file_path: str) -> Tuple[str, bool]:
    """
    根据行数据和文件名决定成本中心及是否输出该行。
    - 若文件名中包含“储发”，则成本中心映射为“储能发展”，并输出该行。
    - 否则，读取一级部门与入账部门：
        仅当入账部门为“战略市场部”时输出，成本中心映射为“战略市场部”。
    Returns: (cost_center_value, include_row)
    """
    if file_path and "储发" in file_path:
        # 储发场景：成本中心映射为“储能发展”
        return "储能发展", True

    dept1 = fetch_cell(row_slice, dept1_idx)
    dept_in = fetch_cell(row_slice, dept_in_idx)

    # 非储发场景：仅当入账部门为“战略市场部”时输出
    if dept_in != "战略市场部":
        return "", False

    # 满足条件时，成本中心映射为“战略市场部”
    return "战略市场部", True

# ---------------- main processing function ----------------

def excel_to_csv_string(excel_path: str) -> str:
    """
    读取 Excel 文件，按照固定的 Sheet 顺序处理，输出 CSV 字符串。
    - Sheet 顺序：国际机票、国内机票、国际酒店、国内酒店
    - 输出字段顺序定义见 out_columns
    - 未提供字段留空
    """
    sheet_order = ["国际机票", "国内机票", "国际酒店", "国内酒店"]

    # 输出字段顺序
    out_columns = [
        "产品类型",          # sheet 名称
        "预订日期",            # 对应字段：发布日期/销售日期/预订日期
        "成本中心",            # 需通过规则计算
        "乘客/旅客名（中文）",  # 中文名/乘客名/入住旅客
        "行程/城市",            # 行程
        "航班号/酒店名称",      # 航班号或酒店名称
        "出行/入住日期",         # 出行日期或入住日期
        "应收款",               # 应收款
        "出差单",               # 出差单
        "备注",                 # 备注
    ]

    # 读取 Excel 的所有工作表
    try:
        xls = pd.read_excel(excel_path, sheet_name=None, header=None)
    except Exception as e:
        raise RuntimeError(f"无法读取 Excel 文件：{e}")

    rows_out: List[List[str]] = []

    for sheet_name in sheet_order:
        if sheet_name not in xls:
            continue
        df = xls[sheet_name]

        header_row_idx = find_header_row(df)
        if header_row_idx is None:
            continue

        header = normalize_header(df.iloc[header_row_idx])
        # 构建字段候选字典（字段名 -> 可能的表头名称）
        if "机票" in sheet_name:
            field_candidates = {
                "预订日期": ["销售日期", "销售日期", "预订日期", "订票日期"],
                "成本中心": ["成本中心", "主体"],
                "一级部门": ["一级部门"],
                "入账部门": ["入账部门"],
                "乘客/旅客名（中文）": ["中文名", "乘客名", "入住旅客"],
                "行程/城市": ["行程", "城市"],
                "航班号/酒店名称": ["航班", "酒店名称", "航班号"],
                "出行/入住日期": ["出发日期", "出行日期", "出发时间", "入住时间"],
                "应收款": ["应收款"],
                "出差单": ["出差单","项目组"],
                "备注": ["备注", "违反政策"],
            }
        else:
            field_candidates = {
                "预订日期": ["预订日期", "销售日期"],
                "成本中心": ["成本中心", "主体"],
                "一级部门": ["一级部门"],
                "入账部门": ["入账部门"],
                "乘客/旅客名（中文）": ["中文名", "乘客名", "入住旅客"],
                "行程/城市": ["城市", "行程"],
                "航班号/酒店名称": ["酒店名称", "名称", "酒店"],
                "出行/入住日期": ["入住时间", "入住日期", "入住日"],
                "应收款": ["应收款"],
                "出差单": ["出差单","项目组"],
                "备注": ["备注", "违反政策"],
            }

        # 找到各字段所在的列索引
        idx_map = locate_field_indices(header, field_candidates)

        # 提取数据行：从标签行之后开始，排除空行与“合计”行
        data_start_df = df.iloc[header_row_idx + 1:].copy()
        if data_start_df.empty:
            continue

        product_type = sheet_name

        # 逐行处理
        for r_idx in range(len(data_start_df)):
            row_slice = data_start_df.iloc[r_idx]

            # 第一列（序号列）若为空或为合计，跳过
            first_col_val = fetch_cell(row_slice, idx_map.get("预订日期"))  # 先用一个字段做非空判断，更稳妥
            # 也可以直接用第一列：row_slice.iloc[0]，但列位置可能不同；这里以序号列的存在性来判断
            first_col_raw = row_slice.iloc[0] if len(row_slice) > 0 else None
            if pd.isna(first_col_raw) or str(first_col_raw).strip() == "" or str(first_col_raw).strip() == "合计":
                continue

            # 读取字段
            booked_raw = fetch_cell(row_slice, idx_map.get("预订日期"))
            booked_date = to_date_str(booked_raw)

            # 成本中心通过带上下文的映射函数处理
            cost_center, include_row = map_cost_center_from_row(
                row_slice,
                idx_map.get("成本中心"),
                idx_map.get("一级部门"),
                idx_map.get("入账部门"),
                excel_path
            )
            if not include_row:
                continue

            # 乘客/旅客名（中文）
            name = ""
            for key in ["乘客/旅客名（中文）", "中文名", "乘客名", "入住旅客"]:
                val = fetch_cell(row_slice, idx_map.get(key))
                if val:
                    name = val
                    break

            # 行程/城市
            travel = fetch_cell(row_slice, idx_map.get("行程/城市"))

            # 航班号/酒店名称
            flight_or_hotel = fetch_cell(row_slice, idx_map.get("航班号/酒店名称"))

            # 出行/入住日期
            travel_date_raw = fetch_cell(row_slice, idx_map.get("出行/入住日期"))
            travel_date = to_date_str(travel_date_raw)

            # 应收款
            receivable = fetch_cell(row_slice, idx_map.get("应收款"))

            # 出差单
            business_trip = fetch_cell(row_slice, idx_map.get("出差单"))

            # 备注
            note = fetch_cell(row_slice, idx_map.get("备注"))
            if note == "":
                note = ""  # 兜底

            # 组装输出行：字段顺序为 out_columns
            out_row = [
                product_type,
                booked_date,
                cost_center,
                name,
                travel,
                flight_or_hotel,
                travel_date,
                receivable,
                business_trip,
                note,
            ]
            rows_out.append(out_row)

    # 构建 CSV 字符串
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(out_columns)
    for row in rows_out:
        writer.writerow(row)

    csv_text = output.getvalue()
    output.close()
    return csv_text


# ----------------- entry point -----------------
# ----------------- 示例/入口 -----------------

if __name__ == "__main__":
    # 获取当前目录下所有xlsx文件名
    files = [os.path.basename(f) for f in glob.glob("*.xlsx")]
    print(f"Files to process: {files}")

    all_rows = []
    header_written = False
    output_csv = "merged_output.csv"

    for f in files:
        if "飞鹤" in f:
            print(f"Processing file: {f}")
            try:
                csv_result = excel_to_csv_string(f)
                csv_io = io.StringIO(csv_result)
                reader = csv.reader(csv_io)
                rows = list(reader)
                if not header_written and rows:
                    all_rows.append(rows[0])  # 写入表头
                    header_written = True
                all_rows.extend(rows[1:])  # 合并数据行
                print(f"Finished processing file: {f}")
            except Exception as e:
                print(f"Error processing file {f}: {e}")

    # 写入合并后的CSV文件
    if all_rows:
        with open(output_csv, "w", newline='', encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(all_rows)
        print(f"合并结果已写入: {output_csv}")
    else:
        print("没有可合并的数据。")
