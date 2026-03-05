import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
from fpdf import FPDF
import base64
import os
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="사출 품질 MES 시스템", page_icon="🏭", layout="wide")

# --- 🚀 1. 데이터 로드 함수 ---
@st.cache_data(ttl=5) 
def load_all_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" 
    doc = client.open_by_url(sheet_url)
    
    # [1] 검사 데이터
    sheet1 = doc.get_worksheet(0) 
    data1 = sheet1.get_all_values()
    df = pd.DataFrame(data1[1:], columns=data1[0]) if len(data1) > 1 else pd.DataFrame()
    if not df.empty:
        df = df[df["품번"].str.strip() != ""] 
        df["검사일자_dt"] = pd.to_datetime(df["검사일자"], errors='coerce')
        df = df.dropna(subset=["검사일자_dt"])

    # [2] 완제품 기준정보
    try:
        sheet_master = doc.worksheet("기준정보")
        data_master = sheet_master.get_all_values()
        df_master = pd.DataFrame(data_master[1:], columns=data_master[0]) if len(data_master) > 1 else pd.DataFrame()
    except:
        df_master = pd.DataFrame()

    # [3] 🌟 부자재 기준정보 (신규 추가!)
    try:
        sheet_sub_master = doc.worksheet("부자재기준정보")
        data_sub_master = sheet_sub_master.get_all_values()
        df_sub_master = pd.DataFrame(data_sub_master[1:], columns=data_sub_master[0]) if len(data_sub_master) > 1 else pd.DataFrame()
    except:
        df_sub_master = pd.DataFrame()

    # [4] 계측기 관리
    try:
        sheet_tool = doc.worksheet("계측기관리")
        data_tool = sheet_tool.get_all_values()
        df_tool = pd.DataFrame(data_tool[3:], columns=data_tool[2]) if len(data_tool) > 3 else pd.DataFrame()
    except:
        df_tool = pd.DataFrame()

    # [5] 수입검사일지
    try:
        sheet_incoming = doc.worksheet("수입검사일지") 
        data_incoming = sheet_incoming.get_all_values()
        if len(data_incoming) > 0:
            df_incoming = pd.DataFrame(data_incoming[1:], columns=data_incoming[0])
        else:
            df_incoming = pd.DataFrame()
    except:
        df_incoming = pd.DataFrame()

    # df_sub_master 가 추가로 반환됩니다.
    return df, df_master, df_sub_master, df_tool, df_incoming

# --- 🚀 2. 구글 시트 데이터 쓰기 함수 ---
def append_incoming_data(new_row):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" 
    doc = client.open_by_url(sheet_url)
    sheet_incoming = doc.worksheet("수입검사일지")
    sheet_incoming.append_row(new_row)

# --- 📄 3. PDF 생성 함수 ---
def create_report_pdf(dataframe, date_label, part_info):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    font_path = "C:\\Windows\\Fonts\\malgun.ttf"
    if os.path.exists(font_path):
        pdf.add_font('Malgun', '', font_path, uni=True)
        pdf.set_font('Malgun', size=18)
    else:
        pdf.set_font("Arial", 'B', size=18)

    pdf.cell(277, 15, txt=f"품 질 검 사 성 적 서 ({date_label})", ln=1, align='C')
    pdf.ln(5)
    pdf.set_font('Malgun', size=10)
    pdf.set_fill_color(240, 240, 240)
    
    h = 8
    pdf.cell(40, h, "조회기간", 1, 0, 'C', True); pdf.cell(100, h, str(date_label), 1, 0, 'C')
    pdf.cell(40, h, "선택품번", 1, 0, 'C', True); pdf.cell(97, h, str(part_info), 1, 1, 'C')
    pdf.ln(5)

    print_df = dataframe[~dataframe["판정1"].str.upper().str.contains("N/A", na=False)].copy()
    all_cols = dataframe.columns.tolist()
    exclude = ["메일", "mail", "id", "ID", "타임스탬프", "검사일자", "검사일자_dt"]
    
    display_headers = ["검사일자", "품번", "구분"] + [c for c in all_cols if "외관" in c]
    measure_cols = [c for c in all_cols if not any(k in c.lower() for k in exclude) 
                    and "외관" not in c and "판정" not in c and c not in display_headers]
    active_measures = [col for col in measure_cols if not print_df[col].apply(lambda x: str(x).strip() in ["", "-", "None", "nan"]).all()]
    display_headers += active_measures + ["판정1"]

    col_width = 277 / len(display_headers)
    pdf.set_font('Malgun', size=9)
    for h_text in display_headers:
        pdf.cell(col_width, 10, "판정" if "판정" in h_text else h_text, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font('Malgun', size=8)
    for _, row in print_df.iterrows():
        for col in display_headers:
            val = str(row.get(col, "-"))
            if col == "구분" and (val == "-" or val == "None"): val = str(row.get("초물/중물", "-"))
            curr_size = 8
            while pdf.get_string_width(val) > (col_width - 2) and curr_size > 5:
                curr_size -= 0.5; pdf.set_font('Malgun', size=curr_size)
            pdf.cell(col_width, 10, val, 1, 0, 'C')
            pdf.set_font('Malgun', size=8)
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1", errors="replace")

# --- 🛰️ 시스템 가동 ---
df, df_master, df_sub_master, df_tool, df_incoming = load_all_data()

st.sidebar.title("🏭 사출 품질 MES")

# 🔥 수입자재 대기건수 계산 및 알람 로직
pending_count = 0
if not df_incoming.empty and "진행상태" in df_incoming.columns:
    pending_items = df_incoming[df_incoming['진행상태'].str.strip() == '대기']
    pending_count = len(pending_items)

if pending_count > 0:
    st.sidebar.error(f"🚨 긴급 알람!\n수입검사 대기 물량: {pending_count}건")
    st.sidebar.info("👇 '수입자재 검사대기' 메뉴 확인 요망")

menu = st.sidebar.radio("메뉴 이동", ["🏠 홈 대시보드", "📋 검사 현황(성적서)", "📈 SPC 관리도", "📏 계측기 검교정 관리", "📥 수입자재 검사대기"])

if st.sidebar.button("🔄 데이터 강제 새로고침"):
    st.cache_data.clear()
    st.rerun()

# --- [1] 🏠 홈 대시보드 ---
if menu == "🏠 홈 대시보드":
    st.title("📊 실시간 품질 현황")
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("총 검사 건수", f"{len(df)}건")
        c2.metric("초물 완료", f"{len(df[df['초물/중물'] == '초물'])}건")
        c3.metric("중물 완료", f"{len(df[df['초물/중물'] == '중물'])}건")
        st.markdown("---")
        st.subheader("📦 품목별 검사 비중")
        st.bar_chart(df["품번"].value_counts())
    else:
        st.warning("데이터가 없습니다.")

# --- [2] 📋 검사 현황(성적서) ---
elif menu == "📋 검사 현황(성적서)":
    st.title("📋 기간별 데이터 조회 및 성적서")
    if not df.empty:
        min_date, max_date = df["검사일자_dt"].min().date(), df["검사일자_dt"].max().date()
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1: date_range = st.date_input("📅 기간 선택", value=(min_date, max_date))
        
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = date_range
            range_df = df[(df["검사일자_dt"].dt.date >= start) & (df["검사일자_dt"].dt.date <= end)].copy()
        else:
            range_df = df[df["검사일자_dt"].dt.date == date_range[0]].copy()
            start = end = date_range[0]

        with c2: all_parts = ["전체"] + sorted(list(range_df["품번"].unique()))
        selected_part = st.selectbox("📦 품번 선택", all_parts)
        with c3: st.write(""); show_na = st.checkbox("N/A 포함")

        final_df = range_df.copy()
        if selected_part != "전체": final_df = final_df[final_df["품번"] == selected_part]
        if not show_na: final_df = final_df[~final_df["판정1"].str.upper().str.contains("N/A", na=False)]

        label = f"{start} ~ {end}"
        st.success(f"✅ {label} 조회 결과 ({len(final_df)}건)")
        st.dataframe(final_df, use_container_width=True)
        
        if st.button("📥 PDF 성적서 생성"):
            pdf_data = create_report_pdf(final_df, label, selected_part)
            b64 = base64.b64encode(pdf_data).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="{label}_성적서.pdf"><button style="width:100%; padding:15px; background-color:#1A5276; color:white; border:none; border-radius:10px; cursor:pointer;">💾 PDF 리포트 저장</button></a>'
            st.markdown(href, unsafe_allow_html=True)

# --- [3] 📈 SPC 관리도 ---
elif menu == "📈 SPC 관리도":
    st.title("📈 SPC 공정 분석")
    if not df.empty:
        selected_part = st.selectbox("품번 선택", list(df["품번"].unique()))
        spc_df = df[df["품번"] == selected_part].copy()
        measures = [c for c in df.columns if c not in ["검사일자", "차종", "품명", "품번", "설비번호", "검사자", "타임스탬프", "판정1", "초물/중물", "검사일자_dt"] and "외관" not in c]
        if measures:
            selected_measure = st.selectbox("측정 항목", measures)
            spc_df[selected_measure] = pd.to_numeric(spc_df[selected_measure], errors='coerce')
            spc_df = spc_df.dropna(subset=[selected_measure])
            master = df_master[df_master["품번"] == selected_part]
            if not master.empty:
                u_col, l_col = f"{selected_measure}MAX", f"{selected_measure}MIN"
                if u_col in master.columns and l_col in master.columns:
                    ucl, lcl = pd.to_numeric(master[u_col], errors='coerce').values[0], pd.to_numeric(master[l_col], errors='coerce').values[0]
                    chart_data = pd.DataFrame({"측정치": spc_df[selected_measure].values, "상한(UCL)": ucl, "하한(LCL)": lcl}, index=spc_df["검사일자"].tolist())
                    st.line_chart(chart_data)
                else: st.line_chart(spc_df[selected_measure])
            else: st.line_chart(spc_df[selected_measure])

# --- [4] 📏 계측기 검교정 관리 ---
elif menu == "📏 계측기 검교정 관리":
    st.title("📏 계측기 검교정 계획 및 실적")
    if not df_tool.empty:
        target_col = "교정일자"
        df_tool[target_col] = pd.to_datetime(df_tool[target_col], format='%y.%m.%d', errors='coerce')
        df_tool["차기교정일"] = df_tool[target_col] + timedelta(days=365)
        df_tool["D-Day"] = (df_tool["차기교정일"] - datetime.now()).dt.days
        
        def get_status(days):
            if pd.isna(days): return "기록없음"
            if days < 0: return "❌ 지연"
            elif days <= 30: return "⚠️ 임박"
            else: return "✅ 정상"
        
        df_tool["상태"] = df_tool["D-Day"].apply(get_status)

        c1, c2, c3 = st.columns(3)
        c1.metric("보유 계측기", f"{len(df_tool)}대")
        c2.metric("교정 지연", f"{len(df_tool[df_tool['상태']=='❌ 지연'])}대", delta_color="inverse")
        c3.metric("교정 임박", f"{len(df_tool[df_tool['상태']=='⚠️ 임박'])}대")

        st.markdown("---")
        def color_status(val):
            return f'background-color: {"#ffcccc" if val == "❌ 지연" else "#fff2cc" if val == "⚠️ 임박" else ""}'
        
        disp_df = df_tool.copy()
        disp_df[target_col] = disp_df[target_col].dt.strftime('%Y-%m-%d')
        disp_df["차기교정일"] = disp_df["차기교정일"].dt.strftime('%Y-%m-%d')
        
        st.dataframe(disp_df[["관리 NO", "검사설비명", "기기번호", "규격", target_col, "차기교정일", "상태"]].style.applymap(color_status, subset=['상태']), use_container_width=True)
    else:
        st.warning("계측기 관리 데이터를 불러오지 못했습니다. '계측기관리' 시트와 열 이름을 확인해 주세요.")

# --- [5] 📥 수입자재 검사대기 (검사대상 여부 자동 연동형) ---
elif menu == "📥 수입자재 검사대기":
    st.title("📥 수입자재 입고 등록 및 검사 현황")
    
    with st.expander("➕ 현장 자재 입고 등록 (품질팀용)", expanded=True):
        col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1]) # 열을 4개로 쪼갭니다
        
        # 1. 부자재기준정보에서 업체명 가져오기
        if not df_sub_master.empty and "업체명" in df_sub_master.columns and "품번" in df_sub_master.columns:
            vendor_list = ["선택하세요"] + sorted(list(df_sub_master["업체명"].dropna().unique()))
        else:
            vendor_list = ["부자재기준정보 시트 확인 요망"]

        with col1:
            new_date = st.date_input("입고일자", datetime.now())
            selected_vendor = st.selectbox("🏢 업체명 선택", vendor_list)

        with col2:
            # 2. 업체명에 맞는 품번 솎아내기
            if selected_vendor not in ["선택하세요", "부자재기준정보 시트 확인 요망"]:
                filtered_sub_master = df_sub_master[df_sub_master["업체명"] == selected_vendor]
                part_no_list = ["선택하세요"] + sorted(list(filtered_sub_master["품번"].dropna().unique()))
            else:
                part_no_list = ["업체를 먼저 선택하세요"]

            selected_part_no = st.selectbox("📦 품번 선택", part_no_list)

        # 🌟 3. 품번 선택 시 품명 & "수입검사여부" 자동 가져오기
        auto_part_name = ""
        auto_inspect_flag = "대상" # 기본값

        if selected_part_no not in ["선택하세요", "업체를 먼저 선택하세요"]:
            matched_row = filtered_sub_master[filtered_sub_master["품번"] == selected_part_no].iloc[0]
            auto_part_name = matched_row["품명"]
            
            # 수입검사여부 열이 시트에 있는지 확인 후 가져오기
            if "수입검사여부" in filtered_sub_master.columns:
                val = matched_row["수입검사여부"]
                if pd.notna(val) and str(val).strip() != "":
                    auto_inspect_flag = str(val).strip()

        with col3:
            new_part_name = st.text_input("📝 품명 (자동입력)", value=auto_part_name, disabled=True)
            new_qty = st.number_input("수량", min_value=0)
            
        with col4:
            # 화면에 검사대상인지 아닌지 띄워줍니다.
            st.text_input("🔍 검사여부 (자동판별)", value=auto_inspect_flag, disabled=True)
            new_lot = st.text_input("LOT NO")
        
        submit_btn = st.button("🚀 입고 등록", use_container_width=True)
        
        if submit_btn:
            if selected_vendor in ["선택하세요", "부자재기준정보 시트 확인 요망"] or selected_part_no in ["선택하세요", "업체를 먼저 선택하세요"]:
                st.warning("⚠️ 업체명과 품번을 정확히 선택해주세요.")
            else:
                # 🌟 비대상일 경우 알람이 안 울리도록 상태를 '면제'로 자동 세팅!
                current_status = "대기" if auto_inspect_flag == "대상" else "면제(완료)"
                
                new_row = [
                    len(df_incoming) + 1 if not df_incoming.empty else 1, 
                    new_date.strftime('%Y-%m-%d'), 
                    selected_vendor,             
                    auto_part_name,              
                    selected_part_no,            
                    new_lot,                     
                    new_qty,                     
                    auto_inspect_flag, # 자동 판별된 검사여부 (대상/비대상)
                    current_status     # 자동 판별된 상태 (대기/면제)
                ]
                append_incoming_data(new_row)
                
                if auto_inspect_flag == "대상":
                    st.error(f"🚨 [{selected_vendor}] {auto_part_name} - 수입검사 대기열에 추가되었습니다!")
                else:
                    st.success(f"✅ [{selected_vendor}] {auto_part_name} - 검사 비대상이므로 자동 완료 처리되었습니다!")
                
                st.cache_data.clear() 
                st.rerun() 

    st.markdown("---")

    if not df_incoming.empty and "진행상태" in df_incoming.columns:
        view_mode = st.radio("조회 옵션", ["🚨 대기 중인 항목만 보기", "전체 입고 내역 보기"], horizontal=True)
        
        if view_mode == "🚨 대기 중인 항목만 보기":
            view_df = df_incoming[df_incoming['진행상태'].str.strip() == '대기']
        else:
            view_df = df_incoming.copy()

        st.subheader(f"📦 조회 리스트 (총 {len(view_df)}건)")

        def highlight_row(row):
            if row.get('진행상태', '').strip() == '대기':
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        st.dataframe(view_df.style.apply(highlight_row, axis=1), use_container_width=True)
    else:
        st.success("✨ 현재 대기 중이거나 등록된 수입자재 내역이 없습니다.")


