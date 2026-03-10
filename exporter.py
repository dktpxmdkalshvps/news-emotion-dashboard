"""
exporter.py - 뉴스 감성 분석 결과 엑셀 추출
"""

import os
from datetime import datetime
import pandas as pd

class DataExporter:
    def __init__(self, keyword: str, output_dir: str = "output"):
        self.keyword = keyword
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export(self, df: pd.DataFrame) -> str:
        if df.empty: return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.keyword}_감성분석_{timestamp}.xlsx"
        path = os.path.join(self.output_dir, filename)

        # 엑셀 저장
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="분석결과", index=False)
            
            # 긍정/부정 별도 시트
            pos_df = df[df["sentiment"] == "긍정"]
            pos_df.to_excel(writer, sheet_name="긍정뉴스", index=False)
            
            neg_df = df[df["sentiment"] == "부정"]
            neg_df.to_excel(writer, sheet_name="부정뉴스", index=False)

        return path
