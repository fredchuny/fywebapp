import streamlit as st
from supabase import create_client, Client
import datetime

# ==========================================
# 1. 網頁基本設定
# ==========================================
st.set_page_config(
    page_title="PHQ-9 完整健康評估系統 (代入端)",
    page_icon="📊",
    layout="centered"
)

# ==========================================
# 2. 初始化 Supabase 連結
# ==========================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 3. 狀態機與登入 Session 鎖定
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state.user = session.user
    except Exception:
        pass

# 頁面切換控制："quiz" (寫問卷), "result" (看本次分數), "history" (看過往紀錄)
if "current_page" not in st.session_state:
    st.session_state.current_page = "quiz"

if "last_score" not in st.session_state:
    st.session_state.last_score = 0

if "last_severity" not in st.session_state:
    st.session_state.last_severity = ""

if "last_patient" not in st.session_state:
    st.session_state.last_patient = ""

# 登出邏輯
def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.user = None
    st.session_state.current_page = "quiz"
    st.rerun()

# 評級邏輯
def get_severity(score):
    if score <= 4: return "無或極輕微憂鬱 (Minimal)"
    elif score <= 9: return "輕度憂鬱 (Mild)"
    elif score <= 14: return "中度憂鬱 (Moderate)"
    elif score <= 19: return "中重度憂鬱 (Moderately Severe)"
    else: return "重度憂鬱 (Severe)"

# ==========================================
# 4. 介面渲染
# ==========================================
st.title("📊 PHQ-9 完整健康評估系統")
st.caption("🧑‍⚕️ 模式：工作人員協助患者輸入端")

# ------------------------------------------
# 【未登入畫面】
# ------------------------------------------
if st.session_state.user is None:
    st.info("👋 歡迎使用！請登入工作人員帳號以開始為患者進行評估。")
    tab1, tab2 = st.tabs(["🔑 密碼登入", "🚀 Google 快速登入"])
    
    with tab1:
        email = st.text_input("電子信箱", key="login_email", placeholder="staff@example.com")
        password = st.text_input("密碼", type="password", key="login_password", placeholder="請輸入密碼")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("登入", type="primary", use_container_width=True):
                if not email or not password:
                    st.warning("請填寫電子信箱與密碼！")
                else:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res.user
                        st.session_state.current_page = "quiz"
                        st.success("登入成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 登入失敗：{e}")
                            
        with col2:
            if st.button("註冊新帳號", use_container_width=True):
                if not email or not password:
                    st.warning("請輸入欲註冊的電子信箱與密碼！")
                elif len(password) < 6:
                    st.warning("密碼長度至少需要 6 個字元！")
                else:
                    try:
                        res = supabase.auth.sign_up({"email": email, "password": password})
                        st.success("📨 註冊確認信已寄出！請至您的信箱點擊驗證連結後返回登入。")
                    except Exception as e:
                        st.error(f"❌ 註冊失敗：{e}")

    with tab2:
        if st.button("使用 Google 帳號快速登入", type="secondary", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {
                        "redirect_to": "https://afancfdlwnbokaohkrsy.supabase.co/auth/v1/callback"
                    }
                })
                auth_url = res.url
                st.markdown(f'<meta http-equiv="refresh" content="0;URL=\'{auth_url}\'" />', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"❌ 啟動 Google 登入失敗：{e}")

# ------------------------------------------
# 【已登入畫面】
# ------------------------------------------
else:
    current_user = st.session_state.user
    col_user, col_logout = st.columns([4, 1])
    with col_user:
        st.write(f"🟢 **目前登入工作人員：** `{current_user.email}`")
    with col_logout:
        st.button("登出系統", on_click=logout, type="secondary", use_container_width=True)
        
    st.divider()

    # ==========================================
    # 頁面一：填寫問卷 (quiz)
    # ==========================================
    if st.session_state.current_page == "quiz":
        st.subheader("📋 患者健康問卷 (PHQ-9)")
        
        st.write("### 🧑‍🦽 1. 患者基本資訊")
        patient_id = st.text_input(
            "患者編號 / 識別代碼 (必填)", 
            placeholder="例如: Pt_Chen 或 P0001",
            help="此代碼將用作資料庫檢索與區分不同患者之用途"
        )
        
        st.divider()
        st.write("### 📝 2. 量表評估作答")
        st.info("請詢問並根據患者 **過去兩星期** 以來受到下列問題困擾的頻率進行勾選：")

        options = ["完全沒有 (0分)", "有幾天 (1分)", "一半以上的天數 (2分)", "幾乎天天 (3分)"]
        score_map = {options[0]: 0, options[1]: 1, options[2]: 2, options[3]: 3}

        # 9 道題目
        q1 = st.radio("1. 做任何事情都提不起勁或沒有樂趣？", options, index=0)
        q2 = st.radio("2. 感到心情低落、沮喪或絕望？", options, index=0)
        q3 = st.radio("3. 入睡困難、易醒或睡得太多？", options, index=0)
        q4 = st.radio("4. 覺得疲倦或沒有活力？", options, index=0)
        q5 = st.radio("5. 胃口不好、食慾不振或吃得太多？", options, index=0)
        q6 = st.radio("6. 覺得自己很糟、或覺得自己很失敗、或讓家人失望？", options, index=0)
        q7 = st.radio("7. 專注於事物上有困難，例如看報紙或看電視？", options, index=0)
        q8 = st.radio("8. 動作或說話速度慢到旁人已注意到？或者相反：煩躁不安、動來動去，比平常更易走動？", options, index=0)
        q9 = st.radio("9. 有「想要一了百了」或「用某種方式傷害自己」的想法？", options, index=0)

        st.write("")
        col_submit, col_go_hist = st.columns(2)
        
        with col_submit:
            if st.button("🚀 提交患者報告", type="primary", use_container_width=True):
                if not patient_id.strip():
                    st.error("⚠️ 請務必輸入『患者編號 / 識別代碼』才能提交資料！")
                else:
                    scores = [score_map[q] for q in [q1, q2, q3, q4, q5, q6, q7, q8, q9]]
                    total_score = sum(scores)
                    severity = get_severity(total_score)
                    
                    try:
                        # 寫入 Supabase 資料表（id 為自動產生的 UUID）
                        payload = {
                            "user_id": current_user.id,        # 工作人員的 UUID
                            "patient_id": patient_id.strip(),  # 患者代碼
                            "q1": scores[0], "q2": scores[1], "q3": scores[2],
                            "q4": scores[3], "q5": scores[4], "q6": scores[5],
                            "q7": scores[6], "q8": scores[7], "q9": scores[8],
                            "total_score": total_score,
                            "severity": severity
                        }
                        
                        supabase.table("phq_responses").insert(payload).execute()
                        
                        # 暫存狀態，轉換至結果頁
                        st.session_state.last_score = total_score
                        st.session_state.last_severity = severity
                        st.session_state.last_patient = patient_id.strip()
                        st.session_state.current_page = "result"
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 資料寫入失敗，請確認 SQL 是否確實運行成功。詳細錯誤：{e}")
                        
        with col_go_hist:
            if st.button("📁 檢視所有患者歷史紀錄", use_container_width=True):
                st.session_state.current_page = "history"
                st.rerun()

    # ==========================================
    # 頁面二：顯示結果頁 (result)
    # ==========================================
    elif st.session_state.current_page == "result":
        st.balloons()
        st.success(f"🎉 患者 `{st.session_state.last_patient}` 的作答數據已成功匯入資料庫！")
        
        st.subheader("📝 本次評估結果報告")
        
        col_p, col_s = st.columns(2)
        with col_p:
            st.metric(label="被評估患者", value=st.session_state.last_patient)
        with col_s:
            st.metric(label="PHQ-9 總得分", value=f"{st.session_state.last_score} / 27 分")
        
        st.info(f"📊 **目前情緒狀態評級：** {st.session_state.last_severity}")
        
        st.divider()
        col_again, col_hist = st.columns(2)
        with col_again:
            if st.button("🔄 登記下一筆新問卷", type="primary", use_container_width=True):
                st.session_state.current_page = "quiz"
                st.rerun()
        with col_hist:
            if st.button("📁 查看全歷史紀錄清單", use_container_width=True):
                st.session_state.current_page = "history"
                st.rerun()

    # ==========================================
    # 頁面三：顯示歷史紀錄頁 (history)
    # ==========================================
    elif st.session_state.current_page == "history":
        st.subheader("📁 患者歷史評估總表")
        st.write("以下是你登錄過的所有患者檢測紀錄：")
        
        try:
            # 讀取當前工作人員登記的所有紀錄
            response = supabase.table("phq_responses")\
                .select("created_at, patient_id, total_score, severity")\
                .eq("user_id", current_user.id)\
                .order("created_at", descending=True)\
                .execute()
                
            records_data = response.data
            
            if not records_data:
                st.warning("📭 目前尚無任何提交紀錄。")
            else:
                import pandas as pd
                
                table_list = []
                for record in records_data:
                    raw_time = record.get("created_at", "")
                    try:
                        dt = datetime.datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        formatted_time = raw_time
                        
                    table_list.append({
                        "登記時間": formatted_time,
                        "患者編號/代碼": record.get("patient_id", "未填寫"),
                        "PHQ-9 總分": f"{record.get('total_score')} / 27",
                        "狀態評級": record.get("severity")
                    })
                
                df = pd.DataFrame(table_list)
                
                # 患者 ID 動態過濾器
                search_query = st.text_input("🔍 輸入患者編號篩選個人紀錄", placeholder="輸入完整或部分代碼...")
                if search_query:
                    df = df[df["患者編號/代碼"].str.contains(search_query, case=False, na=False)]
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"無法從資料庫讀取紀錄：{e}")
            
        st.write("")
        if st.button("⬅️ 返回填寫面板", type="secondary", use_container_width=True):
            st.session_state.current_page = "quiz"
            st.rerun()
