import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
from fpdf import FPDF
import base64
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# 🌟 준비물(import)을 다 챙긴 후, 가장 먼저 웹사이트 이름과 껍데기를 세팅합니다!
st.set_page_config(
    page_title="사출 품질 MES",
    page_icon="🏭",
    layout="wide"
)

# --- 🔐 로그인 자물쇠 기능 ---
def check_password():
    # 💡 여기에 원하시는 비밀번호를 설정하세요! (지금은 1234)
    CORRECT_PASSWORD = "1234" 

    def password_entered():
        if st.session_state["password"] == CORRECT_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #1A5276;'>🏭 사출 품질 MES</h2>", unsafe_allow_html=True)
        st.info("🔒 현장 데이터를 보호하기 위해 비밀번호를 입력해 주세요.")
        st.text_input("🔑 비밀번호", type="password", on_change=password_entered, key="password")
        return False
    
    elif not st.session_state["password_correct"]:
        st.markdown("<h2 style='text-align: center; color: #1A5276;'>🏭 사출 품질 MES</h2>", unsafe_allow_html=True)
        st.error("😕 비밀번호가 틀렸습니다. 다시 시도해 주세요.")
        st.text_input("🔑 비밀번호", type="password", on_change=password_entered, key="password")
        return False
    
    else:
        return True

if not check_password():
    st.stop()

# ==========================================
# (이 아래부터는 원래 있던 @st.cache_data 데이터 불러오기 함수 등 메인 코드가 이어집니다!)
# ==========================================

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

# --- 📌 사이드바 메뉴 (중복 제거 완료!) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #1A5276;'>🏭 사출 품질 MES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; font-size: 12px;'>Quality Management System</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    menu = option_menu(
        menu_title=None, 
        options=["📊 대시보드", "📋 현장 검사 등록", "📋 검사 현황(성적서)", "📈 SPC 관리도", "📥 수입자재 입고", "🛠️ 검교정 현황", "⚙️ 기준정보 관리"],
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "transparent"},
            "nav-link": {
                "font-size": "16px", "text-align": "left", "margin": "0px", "padding": "15px", 
                "--hover-color": "#E5E8E8"
            },
            "nav-link-selected": {
                "background-color": "#1A5276", "color": "white", "font-weight": "bold"
            },
        }
    )
    
    st.markdown("---")
    
    if st.button("🔄 데이터 강제 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 화면 출력부 시작 ---
# (이 바로 아래에 원래 있던 if menu == "📊 대시보드": 가 오면 완벽합니다!)
# --- 화면 출력부 시작 ---
if menu == "📊 대시보드":
    st.title("📊 실시간 품질 대시보드")
    st.info("💡 현장 검사 현황을 한눈에 파악할 수 있습니다.")

    # 🚨 여기에 관리자님의 진짜 구글 시트 주소 넣기!
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" 
    
    try:
        # --- 출입증 코드 ---
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        doc = client.open_by_url(sheet_url)
        
        try:
            # 🌟 새 창고(현장검사기록)에서 데이터를 가져옵니다!
            ws_log = doc.worksheet("현장검사기록")
            data = ws_log.get_all_values()
            
            if len(data) > 1:
                df_log = pd.DataFrame(data[1:], columns=data[0])
                
                # 날짜 계산을 위해 문자열을 시간 데이터로 변환
                df_log['검사일시'] = pd.to_datetime(df_log['검사일시'])
                
                # ==========================================
                # 🌟 1. 핵심 요약 지표 (Metrics)
                # ==========================================
                total_count = len(df_log)
                today_str = datetime.now().strftime("%Y-%m-%d")
                today_count = len(df_log[df_log['검사일시'].dt.strftime("%Y-%m-%d") == today_str])
                inspector_count = df_log['검사자'].nunique()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("📦 누적 검사 건수", f"{total_count}건")
                c2.metric("🆕 오늘 검사 건수", f"{today_count}건")
                c3.metric("👨‍🔧 참여 검사자 수", f"{inspector_count}명")
                
                st.markdown("---")
                
                # ==========================================
                # 🌟 2. 차트: 품목별 검사 건수
                # ==========================================
                st.subheader("📈 품목별 검사 현황")
                part_counts = df_log['품명'].value_counts().reset_index()
                part_counts.columns = ['품명', '검사건수']
                
                # Streamlit의 기본 막대그래프로 예쁘게 띄우기
                st.bar_chart(part_counts.set_index('품명'))
                
                st.markdown("---")
                
                # ==========================================
                # 🌟 3. 최근 검사 내역 (최신 5건만 심플하게)
                # ==========================================
                st.subheader("🕒 최근 검사 기록 (최신 5건)")
                recent_df = df_log.sort_values(by="검사일시", ascending=False).head(5)
                
                # 텍스트가 너무 길면 보기 싫으니 측정결과는 숨기기
                display_df = recent_df[["검사일시", "검사구분", "품번", "품명", "검사자"]]
                st.dataframe(display_df, hide_index=True, use_container_width=True)

            else:
                st.info("아직 입력된 데이터가 없습니다. [📋 현장 검사 등록]에서 첫 데이터를 입력해 주세요!")
                
        except Exception as e:
            st.warning("아직 '현장검사기록' 탭이 생성되지 않았습니다. 데이터를 한 번 등록해 주세요.")

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")


elif menu == "📋 검사 현황(성적서)":
    st.title("📋 현장 검사 기록 현황")
    st.info("💡 표 왼쪽의 '선택' 칸을 체크하면 상세 내용을 보거나 데이터를 삭제할 수 있습니다.")

    # 🚨 여기에 관리자님의 진짜 구글 시트 주소 넣기!
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" 
    
    try:
        # --- 출입증 코드 ---
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        doc = client.open_by_url(sheet_url)
        
        try:
            ws_master = doc.worksheet("기준정보")
            master_data = ws_master.get_all_values()
            df_master = pd.DataFrame(master_data[1:], columns=master_data[0]) if len(master_data) > 1 else pd.DataFrame()
            
            ws_log = doc.worksheet("현장검사기록")
            data = ws_log.get_all_values()
            
            if len(data) > 1:
                df_log = pd.DataFrame(data[1:], columns=data[0])
                df_log = df_log.iloc[::-1].reset_index(drop=True) 
                
                def make_judgment_str(part_name, result_string):
                    if df_master.empty: return result_string
                    items = result_string.split(" / ")
                    judgments = []
                    for item in items:
                        if ": " in item:
                            k, v = item.split(": ", 1)
                            base_k = k.split("-")[0] 
                            spec = df_master[(df_master["품명"] == part_name) & (df_master["검사항목"] == base_k)]
                            if not spec.empty:
                                min_v = spec.iloc[0]["최소값"]
                                max_v = spec.iloc[0]["최대값"]
                                try:
                                    if float(min_v) <= float(v) <= float(max_v):
                                        judgments.append(f"{k}: OK")
                                    else:
                                        judgments.append(f"{k}: 🔴NG")
                                except:
                                    if v == "NG": judgments.append(f"{k}: 🔴NG")
                                    else: judgments.append(f"{k}: OK")
                            else:
                                judgments.append(f"{k}: {v}")
                        else:
                            judgments.append(item)
                    return " / ".join(judgments)

                df_log["요약결과"] = df_log.apply(lambda x: make_judgment_str(x["품명"], x["측정결과"]), axis=1)
                df_log.insert(0, "선택", False)
                
                st.success(f"✅ 총 {len(df_log)}건의 검사 기록이 안전하게 보관되어 있습니다.")
                
                edited_df = st.data_editor(
                    df_log, hide_index=True, use_container_width=True,
                    column_config={"선택": st.column_config.CheckboxColumn("선택", default=False, width="small"), "측정결과": None, "요약결과": st.column_config.TextColumn("측정결과(판정)")}
                )
                
                selected_rows = edited_df[edited_df["선택"] == True]
                
                if not selected_rows.empty:
                    st.markdown("---")
                    
                    # 🌟 삭제 버튼을 제목 옆에 예쁘게 배치합니다!
                    c1, c2 = st.columns([8, 2])
                    with c1:
                        st.subheader("🔍 선택된 검사 상세 수치")
                    with c2:
                        if st.button("🗑️ 선택 데이터 삭제", use_container_width=True):
                            with st.spinner("구글 시트에서 삭제 중입니다..."):
                                # 1. 원본 데이터에서 선택된 행을 제거
                                df_remain = df_log.drop(selected_rows.index)
                                
                                # 2. 다시 시간순(오래된게 위로 오게)으로 뒤집기
                                df_remain = df_remain.iloc[::-1].reset_index(drop=True)
                                
                                # 3. 구글 시트용으로 불필요한 열(선택, 요약결과) 제거
                                df_to_save = df_remain.drop(columns=["선택", "요약결과"])
                                
                                # 4. 구글 시트 내용 비우고 남은 데이터 덮어쓰기
                                ws_log.clear()
                                updated_data = [df_to_save.columns.values.tolist()] + df_to_save.values.tolist()
                                ws_log.update("A1", updated_data)
                                
                                st.success("✅ 선택한 검사 기록이 삭제되었습니다!")
                                st.rerun() # 화면 새로고침
                    
                    for idx, row in selected_rows.iterrows():
                        with st.container():
                            st.markdown(f"#### 📦 [{row['검사구분']}] {row['품명']} ({row['품번']})")
                            st.caption(f"👨‍🔧 검사자: {row['검사자']} | 🕒 일시: {row['검사일시']}")
                            
                            results_list = row['측정결과'].split(" / ")
                            
                            num_cols = 4
                            for i in range(0, len(results_list), num_cols):
                                cols = st.columns(num_cols)
                                for j, res in enumerate(results_list[i:i+num_cols]):
                                    if ": " in res:
                                        item_name, item_val = res.split(": ", 1)
                                        base_item_name = item_name.split("-")[0]
                                        
                                        is_ng = False
                                        spec_str = "" 
                                        spec = df_master[(df_master["품명"] == row["품명"]) & (df_master["검사항목"] == base_item_name)]
                                        
                                        if not spec.empty:
                                            min_v = spec.iloc[0]["최소값"]
                                            max_v = spec.iloc[0]["최대값"]
                                            try:
                                                float(min_v)
                                                spec_str = f" (Spec: {min_v}~{max_v})"
                                                if not (float(min_v) <= float(item_val) <= float(max_v)): is_ng = True
                                            except: 
                                                spec_str = f" (기준: {min_v})"
                                                if item_val == "NG": is_ng = True
                                                    
                                        display_val = f"🔴 {item_val}{spec_str}" if is_ng else f"{item_val}{spec_str}"
                                        cols[j].metric(label=item_name, value=display_val)
                                    else:
                                        cols[j].write(res)
                            st.markdown("---") 
                else:
                    st.markdown("---")
                    st.subheader("🖨️ 성적서 PDF 출력")
                    st.warning("💡 PDF 출력 기능은 '한글 폰트 깨짐 방지' 세팅 중입니다.")
            else:
                st.info("아직 저장된 검사 기록이 없습니다.")
        except Exception as e:
            st.warning("아직 '현장검사기록' 탭이 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

elif menu == "📈 SPC 관리도":
    st.title("📈 실시간 SPC 관리도 (X-bar 추이)")
    st.info("💡 부품과 검사항목을 선택하면, 합격 기준(Spec)과 함께 측정값의 변화 추이를 확인합니다.")

    # 🚨 여기에 관리자님의 진짜 구글 시트 주소 넣기!
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" 
    
    try:
        # --- 출입증 코드 ---
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        doc = client.open_by_url(sheet_url)
        
        try:
            ws_log = doc.worksheet("현장검사기록")
            ws_master = doc.worksheet("기준정보")
            
            data_log = ws_log.get_all_values()
            data_master = ws_master.get_all_values()
            
            if len(data_log) > 1 and len(data_master) > 1:
                df_log = pd.DataFrame(data_log[1:], columns=data_log[0])
                df_master = pd.DataFrame(data_master[1:], columns=data_master[0])
                
                part_list = df_log['품명'].unique().tolist()
                selected_part = st.selectbox("📦 분석할 부품 선택", ["선택 안함"] + part_list)
                
                if selected_part != "선택 안함":
                    spec_df = df_master[df_master['품명'] == selected_part]
                    numeric_items = []
                    spec_dict = {}
                    
                    for _, row in spec_df.iterrows():
                        item = row['검사항목']
                        min_v = row['최소값']
                        max_v = row['최대값']
                        try:
                            lsl = float(min_v)
                            usl = float(max_v)
                            numeric_items.append(item)
                            spec_dict[item] = {'LSL': lsl, 'USL': usl}
                        except:
                            pass 
                            
                    if not numeric_items:
                        st.warning("⚠️ 이 부품에는 숫자로 측정하는 항목이 없습니다.")
                    else:
                        selected_item = st.selectbox("📏 분석할 검사 항목 선택", ["선택 안함"] + numeric_items)
                        
                        if selected_item != "선택 안함":
                            st.markdown("---")
                            st.subheader(f"📊 {selected_part} - {selected_item} 관리도")
                            
                            part_log = df_log[df_log['품명'] == selected_part].copy()
                            plot_data = []
                            
                            for _, row in part_log.iterrows():
                                dt = row['검사일시']
                                results_str = row['측정결과']
                                items = results_str.split(" / ")
                                
                                vals = []
                                for item_str in items:
                                    if ": " in item_str:
                                        k, v = item_str.split(": ", 1)
                                        if k.startswith(selected_item + "-") or k == selected_item:
                                            try: vals.append(float(v))
                                            except: pass
                                                
                                if vals:
                                    avg_val = sum(vals) / len(vals) 
                                    plot_data.append({"검사일시": dt, "측정값(평균)": avg_val})
                                    
                            if plot_data:
                                df_plot = pd.DataFrame(plot_data)
                                df_plot['검사일시'] = pd.to_datetime(df_plot['검사일시'])
                                df_plot = df_plot.sort_values('검사일시')
                                
                                # 🌟 핵심: 시간 단위는 버리고 'YY.MM.DD' (예: 26.03.11) 형식으로 강제 변환합니다!
                                df_plot['검사일시'] = df_plot['검사일시'].dt.strftime('%y.%m.%d')
                                
                                df_plot['상한선(USL)'] = spec_dict[selected_item]['USL']
                                df_plot['하한선(LSL)'] = spec_dict[selected_item]['LSL']
                                
                                df_plot.set_index('검사일시', inplace=True)
                                
                                st.line_chart(df_plot[['상한선(USL)', '측정값(평균)', '하한선(LSL)']])
                                
                                st.markdown("---")
                                st.markdown(f"**📝 데이터 요약 (총 {len(df_plot)}회 검사 진행)**")
                                c1, c2, c3 = st.columns(3)
                                c1.metric("최대 측정값 (Max)", f"{df_plot['측정값(평균)'].max():.2f}")
                                c2.metric("전체 평균값 (X-bar)", f"{df_plot['측정값(평균)'].mean():.2f}")
                                c3.metric("최소 측정값 (Min)", f"{df_plot['측정값(평균)'].min():.2f}")
                                
                            else:
                                st.info("선택한 항목에 대한 측정 데이터가 없습니다.")
            else:
                st.info("아직 분석할 데이터가 충분하지 않습니다. 현장 검사를 진행해 주세요.")
                
        except Exception as e:
            st.warning("데이터를 불러오는 중 문제가 발생했습니다. (현장검사기록 탭이 있는지 확인해 주세요)")
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

# --- [4] 🛠️ 검교정 현황 ---
elif menu == "🛠️ 검교정 현황":
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

elif menu == "⚙️ 기준정보 관리":
    st.title("⚙️ 부품별 기준정보(Spec) 관리")

    # 🚨 여기에 관리자님의 진짜 구글 시트 주소 넣기!
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" 
    
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        doc = client.open_by_url(sheet_url)
        
        ws = doc.worksheet("기준정보")
        data = ws.get_all_values()
        
        if len(data) > 1:
            df_master = pd.DataFrame(data[1:], columns=data[0])
        else:
            df_master = pd.DataFrame(columns=["차종", "품번", "품명", "검사항목", "시료수", "최소값", "최대값"])
            
        # ==========================================
        # 🌟 1. 스마트 간편 등록기
        # ==========================================
        st.markdown("### 🚀 신규 부품 간편 등록")
        st.info("💡 차종, 품번, 품명을 딱 한 번만 입력하고, 아래 항목만 적으세요.")
        
        with st.expander("➕ 여기를 눌러 새로운 부품을 등록하세요", expanded=False):
            c1, c2, c3 = st.columns(3)
            new_car = c1.text_input("🚗 차종 (예: AX PE)")
            new_part_num = c2.text_input("🔢 품번 (예: 97390-GX900)")
            new_part_name = c3.text_input("📦 품명 (예: HOSE-SD DEFROSTER RH)")
            
            empty_items = pd.DataFrame([
                {"검사항목": "중량", "시료수": 3, "최소값": "", "최대값": ""},
                {"검사항목": "두께", "시료수": 3, "최소값": "", "최대값": ""},
                {"검사항목": "외관", "시료수": 3, "최소값": "BURR 없을 것", "최대값": ""},
                {"검사항목": "", "시료수": 3, "최소값": "", "최대값": ""},
                {"검사항목": "", "시료수": 3, "최소값": "", "최대값": ""}
            ])
            
            edited_new_items = st.data_editor(empty_items, num_rows="dynamic", hide_index=True, use_container_width=True)
            
            if st.button("💾 위 내용으로 새 부품 등록하기", type="primary", use_container_width=True):
                if not new_car or not new_part_num or not new_part_name:
                    st.error("⚠️ 차종, 품번, 품명을 모두 입력해 주세요!")
                else:
                    valid_items = edited_new_items[edited_new_items["검사항목"].str.strip() != ""]
                    if valid_items.empty:
                        st.error("⚠️ 최소 1개 이상의 검사항목을 입력해 주세요!")
                    else:
                        with st.spinner("저장 중..."):
                            new_rows = []
                            for _, row in valid_items.iterrows():
                                new_rows.append([new_car, new_part_num, new_part_name, row["검사항목"], row["시료수"], row["최소값"], row["최대값"]])
                            for row in new_rows:
                                ws.append_row(row)
                            st.success(f"✅ {new_part_name} 부품 기준정보 등록 완료!")
                            st.cache_data.clear()
                            st.rerun() 
                            
        st.markdown("---")
        
        # ==========================================
        # 🌟 2. 기존 부품 스펙 조회 및 심플 수정
        # ==========================================
        st.markdown("### 📋 등록된 부품 스펙 수정")
        
        if not df_master.empty:
            df_master["부품식별"] = df_master["차종"] + " | " + df_master["품번"] + " | " + df_master["품명"]
            part_list = df_master["부품식별"].unique().tolist()
            
            # 🌟 검색창을 없애고, 드롭다운 자체를 검색기로 활용합니다!
            st.caption("💡 아래 선택 상자를 클릭하고 **'품번'이나 '품명'을 키보드로 입력**하시면 자동 검색됩니다!")
            selected_target = st.selectbox("🔍 수정할 부품 검색 및 선택", ["선택 안함"] + part_list)
            
            if selected_target != "선택 안함":
                target_df = df_master[df_master["부품식별"] == selected_target].copy()
                
                st.markdown(f"**🔍 [{selected_target}] 검사 항목 수정**")
                edit_df = target_df[["검사항목", "시료수", "최소값", "최대값"]]
                
                edited_spec = st.data_editor(edit_df, num_rows="dynamic", hide_index=True, use_container_width=True)
                
                if st.button("🔄 이 부품의 스펙만 업데이트하기", use_container_width=True):
                    with st.spinner("구글 시트에 업데이트 중입니다..."):
                        valid_edited = edited_spec[edited_spec["검사항목"].str.strip() != ""]
                        df_master_new = df_master[df_master["부품식별"] != selected_target].copy()
                        
                        car, p_num, p_name = selected_target.split(" | ")
                        valid_edited.insert(0, "품명", p_name)
                        valid_edited.insert(0, "품번", p_num)
                        valid_edited.insert(0, "차종", car)
                        
                        final_df = pd.concat([df_master_new, valid_edited], ignore_index=True)
                        if "부품식별" in final_df.columns:
                            final_df = final_df.drop(columns=["부품식별"])
                            
                        ws.clear()
                        updated_data = [final_df.columns.values.tolist()] + final_df.values.tolist()
                        ws.update("A1", updated_data)
                        
                        st.success("✅ 스펙 수정이 완벽하게 반영되었습니다!")
                        st.cache_data.clear() 
                        st.rerun()
        else:
            st.info("아직 등록된 부품이 없습니다. 위에서 신규 부품을 등록해 주세요.")
                
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        
elif menu == "📋 현장 검사 등록":
    st.title("📋 현장 검사(초/중/종물) 등록")
    st.info("💡 품명을 선택하면 등록된 스펙(기준값)이 자동으로 나타납니다.")

    # 🚨 여기에 관리자님의 진짜 구글 시트 주소 넣기!
    sheet_url = "https://docs.google.com/spreadsheets/d/1fh1XlF7Z1tlQQV7zFUql5gjv-veBgItjm0Hb2vfIEo8/edit?gid=1166124159#gid=1166124159" 
    
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        doc = client.open_by_url(sheet_url)
        
        ws_master = doc.worksheet("기준정보")
        data = ws_master.get_all_values()
        
        if len(data) > 1:
            df_master = pd.DataFrame(data[1:], columns=data[0])
            part_names = df_master["품명"].dropna().unique().tolist()
            
            selected_part = st.selectbox("📦 검사할 품명을 선택하세요", ["선택 안함"] + part_names)
            
            if selected_part != "선택 안함":
                st.markdown("---")
                spec_df = df_master[df_master["품명"] == selected_part]
                part_num = spec_df.iloc[0]["품번"] 
                
                st.subheader(f"🔍 [{part_num}] {selected_part} 검사 입력")
                
                with st.form("inspection_form"):
                    c1, c2 = st.columns(2)
                    
                    # 🌟 1. 검사자 이름을 드롭다운으로 변경! (여기에 실제 작업자분들 이름을 적어주세요)
                    inspector_list = ["함인철", "김윤곤"] 
                    inspector = c1.selectbox("👨‍🔧 검사자 이름", inspector_list)
                    
                    insp_type = c2.selectbox("🏷️ 검사 구분", ["초물", "중물", "종물"])
                    
                    st.markdown("##### 📝 측정 항목 입력")
                    results = {}
                    
                    for index, row in spec_df.iterrows():
                        item = row["검사항목"]
                        min_v = row["최소값"]
                        max_v = row["최대값"]
                        
                        try: sample_cnt = int(row["시료수"])
                        except: sample_cnt = 1 
                        
                        st.markdown(f"**📌 {item} (기준: {min_v}~{max_v} / 시료 {sample_cnt}개)**")
                        cols = st.columns(sample_cnt) 
                        
                        is_numeric = True
                        try: float(min_v)
                        except: is_numeric = False
                            
                        for i in range(sample_cnt):
                            item_key = f"{item}-{i+1}" 
                            with cols[i]:
                                # 🌟 2. '1회차' 대신 'N=1'로 이름 변경!
                                if not is_numeric:
                                    results[item_key] = st.selectbox(f"N={i+1}", ["OK", "NG"], key=item_key)
                                else:
                                    results[item_key] = st.text_input(f"N={i+1}", placeholder="측정값", key=item_key)
                        st.markdown("<br>", unsafe_allow_html=True)
                            
                    submit_btn = st.form_submit_button("💾 검사 결과 저장", type="primary", use_container_width=True)
                    
                    if submit_btn:
                        # 검사자를 선택하지 않고 넘어가려 할 때 경고!
                        if inspector == "선택 안함":
                            st.error("⚠️ 검사자 이름을 선택해 주세요!")
                        else:
                            with st.spinner("구글 시트에 안전하게 저장 중입니다..."):
                                result_str = " / ".join([f"{k}: {v}" for k, v in results.items() if v != ""])
                                
                                try: ws_log = doc.worksheet("현장검사기록")
                                except:
                                    ws_log = doc.add_worksheet(title="현장검사기록", rows="1000", cols="10")
                                    ws_log.append_row(["검사일시", "검사구분", "품번", "품명", "검사자", "측정결과"])
                                    
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                new_row = [now, insp_type, part_num, selected_part, inspector, result_str]
                                ws_log.append_row(new_row)
                                
                                st.success("✅ 검사 결과가 성공적으로 저장되었습니다!")
                                st.balloons() 
                                
        else:
            st.warning("⚠️ 등록된 기준정보가 없습니다. [⚙️ 기준정보 관리]에서 먼저 부품을 등록해 주세요.")
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

































































