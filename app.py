import streamlit as st
import pandas as pd
# 등등 다른 import들...

# 🌟 무조건 다른 st. 코드들보다 가장 위에 있어야 합니다!
st.set_page_config(
    page_title="사출 품질 MES",  
    page_icon="🏭",           
    layout="wide"             
)

# --- 🔐 로그인 자물쇠 기능 ---
# (이 아래로 로그인 코드 시작)
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
from fpdf import FPDF
import base64
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 🔐 로그인 자물쇠 기능 ---
def check_password():
    # 💡 여기에 원하시는 비밀번호를 설정하세요! (지금은 1234)
    CORRECT_PASSWORD = "1234" 

    def password_entered():
        if st.session_state["password"] == CORRECT_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 보안을 위해 입력 기록 지우기
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 처음 접속했을 때 보이는 화면
        st.markdown("<h2 style='text-align: center; color: #1A5276;'>🏭 사출 품질 MES</h2>", unsafe_allow_html=True)
        st.info("🔒 현장 데이터를 보호하기 위해 비밀번호를 입력해 주세요.")
        st.text_input("🔑 비밀번호", type="password", on_change=password_entered, key="password")
        return False
    
    elif not st.session_state["password_correct"]:
        # 비밀번호가 틀렸을 때 보이는 화면
        st.markdown("<h2 style='text-align: center; color: #1A5276;'>🏭 사출 품질 MES</h2>", unsafe_allow_html=True)
        st.error("😕 비밀번호가 틀렸습니다. 다시 시도해 주세요.")
        st.text_input("🔑 비밀번호", type="password", on_change=password_entered, key="password")
        return False
    
    else:
        # 비밀번호가 맞았을 때 (통과!)
        return True

# 🚨 만약 비밀번호가 틀렸다면 여기서 프로그램을 멈춤! (아래 코드는 실행 안 됨)
if not check_password():
    st.stop()

# ==========================================
# (이 아래부터는 원래 있던 데이터 불러오기 함수 등 메인 코드가 이어집니다!)
# ==========================================

# 1. 페이지 설정
st.set_page_config(page_title="사출 품질 MES 시스템", page_icon="🏭", layout="wide")

# --- 🚀 1. 데이터 로드 함수 ---
@st.cache_data(ttl=600) # 10분 동안은 구글에 안 물어보고 메모리에서 즉시 꺼냄! 
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

    # [3] 부자재 기준정보
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
        if len(data_incoming) > 1:
            df_incoming = pd.DataFrame(data_incoming[1:], columns=data_incoming[0])
        else:
            df_incoming = pd.DataFrame()
    except:
        df_incoming = pd.DataFrame()

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

# --- 🚀 3. 구글 시트 데이터 다중 삭제 함수 (업그레이드!) ---
def delete_incoming_data_multiple(sheet_row_indices):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" 
    doc = client.open_by_url(sheet_url)
    sheet_incoming = doc.worksheet("수입검사일지")
    
    # 🚨 중요: 인덱스가 꼬이지 않도록 무조건 번호가 큰 것(밑에 있는 행)부터 역순으로 삭제합니다.
    for row_index in sorted(sheet_row_indices, reverse=True):
        sheet_incoming.delete_rows(row_index)
        
# --- 🚀 구글 시트 데이터 단일 셀(승인결과) 업데이트 함수 ---
def update_approval_status(sheet_row_index, new_status):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" # 실제 시트 주소 확인
    doc = client.open_by_url(sheet_url)
    sheet1 = doc.get_worksheet(0) 
    
    headers = sheet1.row_values(1)
    # 🚨 구글 시트의 실제 제목인 '승인자 확인'으로 찾도록 수정 완료!
    if "승인자 확인" in headers:
        col_index = headers.index("승인자 확인") + 1
        sheet1.update_cell(sheet_row_index, col_index, new_status)
# --- 📄 4. PDF 생성 함수 ---
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
try:
    df, df_master, df_sub_master, df_tool, df_incoming = load_all_data()
except Exception as e:
    st.warning("⏳ 구글 서버 보호를 위해 잠시 접속이 대기 중입니다. (새로고침이 너무 빨랐습니다!) 약 1분 뒤에 F5를 눌러주세요.")
    st.stop() # 여기서 멈춰서 무시무시한 빨간 에러창이 뜨는 것을 막아줍니다!

st.sidebar.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2 style='color: #1A5276; font-weight: bold;'>🏭 사출 품질 MES</h2>
        <span style='color: #7F8C8D; font-size: 14px;'>Quality Management System</span>
        <hr style='margin-top: 10px; margin-bottom: 10px;'>
    </div>
""", unsafe_allow_html=True)

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

# --- [2] 📋 검사 현황(성적서) (결재 O/X 기능 - 이름표 수정 완료) ---
elif menu == "📋 검사 현황(성적서)":
    st.title("📋 기간별 데이터 조회 및 성적서 결재")
    if not df.empty:
        # 🚨 파이썬 내부에서도 '승인자 확인'으로 인식하도록 모두 수정
        if "승인자 확인" not in df.columns:
            df["승인자 확인"] = "대기"
            
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

        # 🌟 1. 메인 표에 '승인자 확인' 열 추가
        core_cols = ["승인자 확인", "차종", "검사일자", "검사자", "설비번호", "품명", "품번"]
        available_cols = [c for c in core_cols if c in final_df.columns]
        view_df = final_df[available_cols].copy()
        
        view_df.insert(0, "상세보기", False)
        
        # 빈칸이면 '대기'로 표시
        view_df['승인자 확인'] = view_df['승인자 확인'].replace({'': '대기', 'nan': '대기', None: '대기'})

        st.write("👉 **책임자 결재:** 표 안의 `[✍️ 승인확인]` 칸을 더블클릭하여 O, X를 선택한 후, 아래 저장 버튼을 누르세요.")
        
        # 🌟 2. 표 렌더링 (승인자 확인 열만 조작 가능하게 오픈!)
        edited_df = st.data_editor(
            view_df,
            column_config={
                "상세보기": st.column_config.CheckboxColumn("🔍 상세보기", default=False),
                # 화면에 보이는 라벨은 "✍️ 승인확인"으로 예쁘게 유지하고, 실제 데이터 통신은 "승인자 확인"으로 함
                "승인자 확인": st.column_config.SelectboxColumn("✍️ 승인확인", options=["대기", "O", "X"], required=True)
            },
            disabled=[c for c in available_cols if c != "승인자 확인"], 
            hide_index=True,
            use_container_width=True,
            key="approval_editor" 
        )

        # 🌟 3. 결재(O/X) 변경 사항 감지 및 저장 버튼 표시
        changes = []
        for idx in view_df.index:
            old_val = str(view_df.loc[idx, "승인자 확인"]).strip()
            new_val = str(edited_df.loc[idx, "승인자 확인"]).strip()
            if old_val != new_val:
                changes.append((idx + 2, new_val))

        if changes:
            st.warning(f"⚠️ {len(changes)}건의 결재 상태가 변경되었습니다. 반드시 아래 저장 버튼을 눌러 확정해 주세요!")
            if st.button("💾 저장", type="primary", use_container_width=True):
                with st.spinner("변경 내용을 업데이트하는 중입니다..."):
                    for sheet_row, new_val in changes:
                        update_approval_status(sheet_row, new_val)
                st.success("✅ 승인(결재) 처리가 완벽하게 저장되었습니다!")
                st.cache_data.clear()
                st.rerun()

        # 🌟 4. 세부 측정 데이터 폴더 (상세보기)
        selected_indices = edited_df[edited_df["상세보기"] == True].index

        if not selected_indices.empty:
            st.markdown("---")
            st.subheader("🔎 상세 검사 결과")
            
            import re # 정규식(글자 쪼개기) 도구 

            for idx in selected_indices:
                row_data = final_df.loc[idx]
                
                # 유령 칸들 완벽 차단 명단
                exclude_cols = available_cols + ["타임스탬프", "검사일자_dt", "ID", "id", "이메일 주소", "이메일", "1열", "2열", "3열", "4열", "5열", "6열"]
                detail_data = row_data.drop(labels=[c for c in exclude_cols if c in row_data.index])
                
                ordered_base_names = [] 
                parsed_data = {}
                
                for col_name, val in detail_data.items():
                    col_str = str(col_name).strip()
                    
                    # 🌟 마법의 복사기: '판정' 열은 값이 하나뿐이어도 1,2,3번 시료 칸에 모두 도장을 찍어줌!
                    if col_str.startswith("판정"):
                        if col_str not in parsed_data:
                            parsed_data[col_str] = {}
                            ordered_base_names.append(col_str)
                        parsed_data[col_str]["1번 시료"] = val
                        parsed_data[col_str]["2번 시료"] = val
                        parsed_data[col_str]["3번 시료"] = val
                        parsed_data[col_str]["공통 / 단일값"] = "-" # 판정의 공통 칸은 비워둠
                        
                    # '치수'는 공통 칸에 그대로 둠
                    elif col_str.startswith("치수"):
                        if col_str not in parsed_data:
                            parsed_data[col_str] = {}
                            ordered_base_names.append(col_str)
                        parsed_data[col_str]["공통 / 단일값"] = val
                    
                    # 그 외 항목(중량, 두께, 외관 등)은 끝에 1~3이 있으면 시료 칸으로 보냄
                    else:
                        match = re.match(r'(.+?)([1-3])$', col_str) 
                        if match:
                            base_name = match.group(1).strip()     
                            sample_num = match.group(2) + "번 시료" 
                        else:
                            base_name = col_str 
                            sample_num = "공통 / 단일값"
                            
                        if base_name not in parsed_data:
                            parsed_data[base_name] = {}
                            ordered_base_names.append(base_name)
                            
                        parsed_data[base_name][sample_num] = val
                        
                # 🌟 기록해둔 순서대로 표 조립하기
                rows = []
                for base in ordered_base_names:
                    row_dict = {"검사 항목": base}
                    row_dict.update(parsed_data[base])
                    rows.append(row_dict)
                    
                detail_table = pd.DataFrame(rows)
                
                # 열 순서 정렬
                expected_cols = ['검사 항목', '공통 / 단일값', '1번 시료', '2번 시료', '3번 시료']
                ordered_cols = [c for c in expected_cols if c in detail_table.columns]
                detail_table = detail_table[ordered_cols].fillna("-") 
                
                with st.expander(f"📂 {row_data.get('검사일자', '')} | {row_data.get('품명', '')} ({row_data.get('품번', '')})", expanded=True):
                    st.dataframe(detail_table, hide_index=True, use_container_width=True)
        
        if st.button("📥 PDF 성적서 생성"):
            pdf_data = create_report_pdf(final_df, label, selected_part)
            b64 = base64.b64encode(pdf_data).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="{label}_성적서.pdf"><button style="width:100%; padding:15px; background-color:#1A5276; color:white; border:none; border-radius:10px; cursor:pointer;">💾 PDF 리포트 저장</button></a>'
            st.markdown(href, unsafe_allow_html=True)
# --- [3] 📈 SPC 관리도 (평균값 적용 및 고급 차트 업그레이드) ---
elif menu == "📈 SPC 관리도":
    st.title("📈 SPC 관리도 (X-bar 평균 차트)")
    st.markdown("측정된 3개의 샘플(초물/중물/종물)의 **평균값**을 계산하여 추이를 보여줍니다.")
    
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        with c1: 
            all_parts = sorted(list(df["품번"].unique()))
            selected_part = st.selectbox("📦 품번 선택", all_parts)
        with c2: 
            inspect_item = st.selectbox("🔍 검사 항목", ["중량", "두께", "내경", "외경", "전장"])
        with c3:
            data_count = st.number_input("📊 최근 조회 데이터 건수", min_value=5, max_value=100, value=30)
            
        # 선택한 품번 데이터 필터링 (최근 데이터 순)
        df_spc = df[df["품번"] == selected_part].copy()
        df_spc = df_spc.sort_values(by="검사일자_dt").tail(data_count)
        
        # 🌟 핵심 기능: 1, 2, 3번 측정값의 '평균' 구하기
        col1, col2, col3 = f"{inspect_item}1", f"{inspect_item}2", f"{inspect_item}3"
        
        if col1 in df_spc.columns and col2 in df_spc.columns and col3 in df_spc.columns:
            # 안전하게 숫자로 변환 후 빈칸은 제외하고 평균 계산
            for c in [col1, col2, col3]:
                df_spc[c] = pd.to_numeric(df_spc[c], errors='coerce')
            
            # 3개 측정치의 평균을 구해 새로운 '평균값' 기둥을 만듦
            df_spc['평균값'] = df_spc[[col1, col2, col3]].mean(axis=1, skipna=True)
            df_spc = df_spc.dropna(subset=['평균값']) # 평균이 안 구해진 텅 빈 데이터는 제외
            
            if not df_spc.empty:
                # 🌟 고급 Plotly 차트 그리기
                fig = go.Figure()
                
                # 평균값 꺾은선 추가
                fig.add_trace(go.Scatter(
                    x=df_spc['검사일자'], 
                    y=df_spc['평균값'],
                    mode='lines+markers+text',
                    name=f'{inspect_item} 평균',
                    line=dict(color='#1A5276', width=3), # 딥블루 선
                    marker=dict(size=10, color='#E74C3C', symbol='circle'), # 빨간색 타점
                    text=df_spc['평균값'].round(2), # 타점 위에 소수점 2자리 평균값 표시
                    textposition="top center",
                    textfont=dict(size=12, color='black')
                ))
                
                # 차트 디자인 세팅
                fig.update_layout(
                    title=dict(text=f"<b>[{selected_part}] {inspect_item} 평균값 추이</b>", font=dict(size=20)),
                    xaxis_title="검사 일시",
                    yaxis_title=f"{inspect_item} 평균 측정값",
                    template="plotly_white",
                    hovermode="x unified", # 마우스를 올리면 예쁜 정보창이 뜸!
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                # 화면에 예쁘게 꽉 채워서 출력
                st.plotly_chart(fig, use_container_width=True)
                
                # 계산된 상세 내역을 폴더로 숨겨둠 (필요할 때 열어볼 수 있게)
                with st.expander("📊 평균값 계산 상세 내역 보기 (클릭하여 펼치기)"):
                    st.dataframe(df_spc[['검사일자', '검사자', '설비번호', col1, col2, col3, '평균값']], hide_index=True)
            else:
                st.warning("측정된 숫자 데이터가 없습니다. (입력 시 숫자로 넣었는지 확인해주세요)")
        else:
            st.error(f"데이터에 {col1}, {col2}, {col3} 항목이 없어 평균을 낼 수 없습니다.")

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

# --- [5] 📥 수입자재 검사대기 (표 내부 체크박스 삭제 지원) ---
elif menu == "📥 수입자재 검사대기":
    st.title("📥 수입자재 입고 등록 및 검사 현황")
    
    with st.expander("➕ 현장 자재 입고 등록 (품질팀용)", expanded=False):
        col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])
        
        if not df_sub_master.empty and "업체명" in df_sub_master.columns and "품번" in df_sub_master.columns:
            vendor_list = ["선택하세요"] + sorted(list(df_sub_master["업체명"].dropna().unique()))
        else:
            vendor_list = ["부자재기준정보 시트 확인 요망"]

        with col1:
            new_date = st.date_input("입고일자", datetime.now())
            selected_vendor = st.selectbox("🏢 업체명 선택", vendor_list)

        with col2:
            if selected_vendor not in ["선택하세요", "부자재기준정보 시트 확인 요망"]:
                filtered_sub_master = df_sub_master[df_sub_master["업체명"] == selected_vendor]
                part_no_list = ["선택하세요"] + sorted(list(filtered_sub_master["품번"].dropna().unique()))
            else:
                part_no_list = ["업체를 먼저 선택하세요"]

            selected_part_no = st.selectbox("📦 품번 선택", part_no_list)

        auto_part_name = ""
        auto_inspect_flag = "대상" 

        if selected_part_no not in ["선택하세요", "업체를 먼저 선택하세요"]:
            matched_row = filtered_sub_master[filtered_sub_master["품번"] == selected_part_no].iloc[0]
            auto_part_name = matched_row["품명"]
            
            if "수입검사여부" in filtered_sub_master.columns:
                val = matched_row["수입검사여부"]
                if pd.notna(val) and str(val).strip() != "":
                    auto_inspect_flag = str(val).strip()

        with col3:
            new_part_name = st.text_input("📝 품명 (자동입력)", value=auto_part_name, disabled=True)
            new_qty = st.number_input("수량", min_value=0)
            
        with col4:
            st.text_input("🔍 검사여부 (자동판별)", value=auto_inspect_flag, disabled=True)
            new_lot = st.text_input("LOT NO")
        
        submit_btn = st.button("🚀 입고 등록", use_container_width=True)
        
        if submit_btn:
            if selected_vendor in ["선택하세요", "부자재기준정보 시트 확인 요망"] or selected_part_no in ["선택하세요", "업체를 먼저 선택하세요"]:
                st.warning("⚠️ 업체명과 품번을 정확히 선택해주세요.")
            else:
                current_status = "대기" if auto_inspect_flag == "대상" else "면제(완료)"
                
                new_row = [
                    len(df_incoming) + 1 if not df_incoming.empty else 1, 
                    new_date.strftime('%Y-%m-%d'), 
                    selected_vendor,             
                    auto_part_name,              
                    selected_part_no,            
                    new_lot,                     
                    new_qty,                     
                    auto_inspect_flag, 
                    current_status     
                ]
                append_incoming_data(new_row)
                
                if auto_inspect_flag == "대상":
                    st.error(f"🚨 [{selected_vendor}] {auto_part_name} - 수입검사 대기열에 추가되었습니다!")
                else:
                    st.success(f"✅ [{selected_vendor}] {auto_part_name} - 검사 비대상이므로 자동 완료 처리되었습니다!")
                
                st.cache_data.clear() 
                st.rerun() 

    st.markdown("---")

    # --- 🌟 조회 리스트 (체크박스 기능 적용) ---
    if not df_incoming.empty and "진행상태" in df_incoming.columns:
        view_mode = st.radio("조회 옵션", ["🚨 대기 중인 항목만 보기", "전체 입고 내역 보기"], horizontal=True)
        
        if view_mode == "🚨 대기 중인 항목만 보기":
            view_df = df_incoming[df_incoming['진행상태'].str.strip() == '대기'].copy()
        else:
            view_df = df_incoming.copy()

        st.subheader(f"📦 조회 리스트 (총 {len(view_df)}건)")

        # 1. 맨 앞에 '선택' 열(체크박스용) 추가 (기본값 False)
        view_df.insert(0, "선택", False)

        def highlight_row(row):
            if row.get('진행상태', '').strip() == '대기':
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        # 2. st.dataframe 대신 st.data_editor 사용 (표 안에서 클릭 가능하게 렌더링)
        edited_df = st.data_editor(
            view_df.style.apply(highlight_row, axis=1),
            column_config={
                "선택": st.column_config.CheckboxColumn("✅ 선택", default=False)
            },
            disabled=[col for col in view_df.columns if col != "선택"], # '선택' 열 빼고 나머지는 수정 불가
            hide_index=True,
            use_container_width=True
        )
        
        # 3. 체크된 항목들만 모아내기
        selected_rows = edited_df[edited_df["선택"] == True]

        # 4. 하나라도 체크된 항목이 있으면 삭제 버튼 표시
        if not selected_rows.empty:
            st.error(f"⚠️ {len(selected_rows)}개의 데이터가 선택되었습니다.")
            if st.button("🗑️ 선택한 데이터 영구 삭제", type="primary", use_container_width=True):
                # 원래 데이터프레임의 인덱스를 구글 시트의 행 번호(1번은 제목줄이므로 +2)로 변환
                indices_to_delete = selected_rows.index.tolist()
                sheet_rows_to_delete = [idx + 2 for idx in indices_to_delete]
                
                # 삭제 함수 실행
                delete_incoming_data_multiple(sheet_rows_to_delete)
                
                st.success("✅ 선택한 데이터가 구글 시트에서 완전히 삭제되었습니다!")
                st.cache_data.clear()
                st.rerun()

    else:
        st.success("✨ 현재 대기 중이거나 등록된 수입자재 내역이 없습니다.")


































