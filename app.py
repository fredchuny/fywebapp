import streamlit as st
from supabase import create_client, Client
import datetime
import pytz
import pandas as pd

# =========================================================================
# 臨床輔助函式：PHQ-9 抑鬱症狀評級邏輯
# =========================================================================
def get_severity(score):
    if score <= 4:
        return "正常或極輕微抑鬱 (0-4分)"
    elif score <= 9:
        return "輕度抑鬱 (5-9分)"
    elif score <= 14:
        return "中度抑鬱 (10-14分)"
    elif score <= 19:
        return "中重度抑鬱 (15-19分)"
    else:
        return "重度抑鬱 (20-27分)"

# =========================================================================
# 1. 全域設定與初始化 (fywebapp)
# =========================================================================
st.set_page_config(page_title="fywebapp", page_icon="🔑", layout="centered")

# 初始化 Supabase 連線
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(
        st.secrets["SUPABASE_URL"], 
        st.secrets["SUPABASE_KEY"]
    )

# 初始化 Session State 導航與用戶狀態
if "user" not in st.session_state:
    st.session_state.user = None
if "permissions" not in st.session_state:
    st.session_state.permissions = {}
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

# =========================================================================
# 頁面 A：中央控制登入入口 (Central Login)
# =========================================================================
if st.session_state.current_page == "login":
    st.title("🔑 fywebapp")
    st.subheader("中央控制安全登入系統")
    st.write("請使用您的工作人員帳號登入以存取授權功能。")
    
    with st.form("central_login_form"):
        email = st.text_input("工作人員電子信箱 (Email)")
        password = st.text_input("密碼 (Password)", type="password")
        submit = st.form_submit_button("安全登入")
        
        if submit:
            if email and password:
                try:
                    # 1. 驗證帳密登入 (觸發 Supabase authenticated 角色)
                    res = st.session_state.supabase.auth.sign_in_with_password({
                        "email": email, 
                        "password": password
                    })
                    st.session_state.user = res.user
                    
                    # 2. 登入成功後，立刻去資料庫撈取該用戶的權限清單 (Feature Toggles)
                    role_resp = st.session_state.supabase.table("user_roles").select("*").eq("user_id", res.user.id).execute()
                    
                    if role_resp.data:
                        st.session_state.permissions = role_resp.data[0]
                    else:
                        # 預防機制：如果在 user_roles 找不到對應資料，預設全關閉以保安全
                        st.session_state.permissions = {
                            "can_access_phq9": False, 
                            "can_access_gad7": False, 
                            "can_access_analytics": False
                        }
                    
                    st.success("安全驗證成功！正在導向主控制面板...")
                    st.session_state.current_page = "dashboard"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 登入失敗：請確認帳號密碼是否正確。")
            else:
                st.warning("請填寫所有欄位！")

# =========================================================================
# 頁面 B：中央主控面板 (Dashboard)
# =========================================================================
elif st.session_state.current_page == "dashboard":
    st.title("🌐 fywebapp 中央主控面板")
    st.write(f"目前登入帳號: `{st.session_state.user.email}`")
    
    # 側邊欄全域安全登出
    if st.sidebar.button("🚪 安全登出系統"):
        st.session_state.supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.permissions = {}
        st.session_state.current_page = "login"
        st.rerun()
        
    st.divider()
    st.write("### 🗂️ 您獲權存取的系統功能模組：")
    
    perms = st.session_state.permissions
    has_any_permission = False
    
    # 🎯 權限分流：依據資料庫的打勾 (True/False) 動態顯示按鈕
    if perms.get("can_access_phq9"):
        has_any_permission = True
        if st.button("📝 進入 PHQ-9 臨床評估系統", use_container_width=True):
            st.session_state.current_page = "quiz"  # 直接導向問卷開始填寫
            st.rerun()
            
    if perms.get("can_access_gad7"):
        has_any_permission = True
        if st.button("📊 進入 GAD-7 焦慮評估系統 (未來擴充)", use_container_width=True):
            st.session_state.current_page = "gad7_module"
            st.rerun()
            
    if perms.get("can_access_analytics"):
        has_any_permission = True
        if st.button("📈 進入 機構數據分析後台 (未來擴充)", use_container_width=True):
            st.session_state.current_page = "analytics_module"
            st.rerun()
            
    if not has_any_permission:
        st.warning("⚠️ 您的帳號目前未獲指派任何特定模組功能。請聯絡系統管理員在後台核發權限。")

# =========================================================================
# 頁面 C：PHQ-9 臨床評估系統模組 (quiz / result / history)
# =========================================================================
elif st.session_state.current_page in ["quiz", "result", "history"]:
    # 二次前端守衛，防止非法跳轉
    if not st.session_state.permissions.get("can_access_phq9"):
        st.error("⛔ 您沒有權限存取此模組。")
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    st.title("📝 PHQ-9 抑鬱症狀臨床評估")
    
    # 全域側邊欄返回主面板按鈕
    if st.sidebar.button("⬅️ 返回 fywebapp 主面板"):
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    # --- PHQ-9 子分流：問卷作答頁面 ---
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
        
        # 🎯 建立穩健的安全對照防呆字典，防止 KeyError
        score_map = {options[0]: 0, options[1]: 1, options[2]: 2, options[3]: 3}

        # 9 道題目
        q1 = st.radio("1. 做任何事情都提不起勁或沒有樂趣？", options, index=None)
        q2 = st.radio("2. 感到心情低落、沮喪或絕望？", options, index=None)
        q3 = st.radio("3. 入睡困難、易醒或睡得太多？", options, index=None)
        q4 = st.radio("4. 覺得疲倦或沒有活力？", options, index=None)
        q5 = st.radio("5. 胃口不好、食慾不振或吃得太多？", options, index=None)
        q6 = st.radio("6. 覺得自己很糟、或覺得自己很失敗、或讓家人失望？", options, index=None)
        q7 = st.radio("7. 專注於事物上有困難，例如看報紙或看電視？", options, index=None)
        q8 = st.radio("8. 動作或說話速度慢到旁人已注意到？或者相反：煩躁不安、動來動去，比平常更易走動？", options, index=None)
        q9 = st.radio("9. 有「想要一了百了」或「用某種方式傷害自己」的想法？", options, index=None)

        st.write("")
        col_submit, col_go_hist = st.columns(2)
        
        with col_submit:
            if st.button("🚀 提交患者報告", type="primary", use_container_width=True):
                if not patient_id.strip():
                    st.error("⚠️ 請務必輸入『患者編號 / 識別代碼』才能提交資料！")
                elif None in [q1, q2, q3, q4, q5, q6, q7, q8, q9]:
                    st.error("⚠️ 請確保所有 9 道題目皆已作答評估完畢！")
                else:
                    # 🎯 使用 .get(q, 0) 防呆取分，確保永不崩潰
                    scores = [score_map.get(q, 0) for q in [q1, q2, q3, q4, q5, q6, q7, q8, q9]]
                    total_score = sum(scores)
                    severity = get_severity(total_score)
                    
                    try:
                        # 安全注入 Access Token 認證
                        session = st.session_state.supabase.auth.get_session()
                        if session:
                            st.session_state.supabase.postgrest.auth(session.access_token)
                        
                        payload = {
                            "user_id": st.session_state.user.id,        # 修正：對齊當前中央登入者的真實 UUID
                            "patient_id": patient_id.strip(),  
                            "q1": scores[0], "q2": scores[1], "q3": scores[2],
                            "q4": scores[3], "q5": scores[4], "q6": scores[5],
                            "q7": scores[6], "q8": scores[7], "q9": scores[8],
                            "total_score": total_score,
                            "severity": severity
                        }
                        
                        st.session_state.supabase.table("phq_responses").insert(payload).execute()
                        
                        # 暫存結果至狀態中，跳轉至結果頁
                        st.session_state.last_score = total_score
                        st.session_state.last_severity = severity
                        st.session_state.last_patient = patient_id.strip()
                        st.session_state.current_page = "result"
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 資料寫入失敗，請確認安全規則是否設定正確。詳細錯誤：{e}")
                        
        with col_go_hist:
            if st.button("📁 檢視所有患者歷史紀錄", use_container_width=True):
                st.session_state.current_page = "history"
                st.rerun()

    # --- PHQ-9 子分流：顯示結果頁面 ---
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

    # --- PHQ-9 子分流：檢視歷史紀錄頁面 ---
    elif st.session_state.current_page == "history":
        st.subheader("📁 患者歷史評估總表")
        st.write("### 🌍 時區設定")
        
        common_timezones = [
            "America/Toronto",      # 預設多倫多/美東時區
            "Asia/Hong_Kong",       # 香港時區
            "UTC"
        ] + sorted(pytz.common_timezones)
        
        seen = set()
        clean_zones = [x for x in common_timezones if not (x in seen or seen.add(x))]
        
        user_tz_name = st.selectbox(
            "請選擇您目前的所在地時區（系統將自動依此轉換顯示時間）：",
            options=clean_zones,
            index=0,
            help="系統會自動將資料庫的標準時間轉換為您所選的本地電腦時區"
        )
        
        local_tz = pytz.timezone(user_tz_name)
        st.divider()
        st.write(f"以下是您登錄過的所有患者檢測紀錄（目前已切換至：**{user_tz_name}**）：")
        
        try:
            session = st.session_state.supabase.auth.get_session()
            if session:
                st.session_state.supabase.postgrest.auth(session.access_token)
                
            # 讀取當前登入工作人員登記的所有紀錄
            response = st.session_state.supabase.table("phq_responses")\
                .select("created_at, patient_id, total_score, severity")\
                .eq("user_id", st.session_state.user.id)\
                .order("created_at", desc=True)\
                .execute()
                
            records_data = response.data
            
            if not records_data:
                st.warning("📭 目前尚無任何提交紀錄。")
            else:
                table_list = []
                for record in records_data:
                    raw_time = record.get("created_at", "")
                    try:
                        dt_utc = datetime.datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                        dt_local = dt_utc.astimezone(local_tz)
                        tz_abbr = dt_local.strftime("%Z")
                        formatted_time = f"{dt_local.strftime('%Y-%m-%d %H:%M')} ({tz_abbr})"
                    except Exception:
                        formatted_time = raw_time
                        
                    table_list.append({
                        "登記時間 (時區)": formatted_time,
                        "患者編號/代碼": record.get("patient_id", "未填寫"),
                        "PHQ-9 總分": f"{record.get('total_score')} / 27",
                        "狀態評級": record.get("severity")
                    })
                
                df = pd.DataFrame(table_list)
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

# =========================================================================
# 頁面 D：未來功能：GAD-7 焦慮評估系統模組 (gad7_module)
# =========================================================================
elif st.session_state.current_page == "gad7_module":
    if not st.session_state.permissions.get("can_access_gad7"):
        st.error("⛔ 您沒有權限存取此模組。")
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    st.title("📊 GAD-7 焦慮評估系統")
    if st.button("⬅️ 返回 fywebapp 主控制面板"):
        st.session_state.current_page = "dashboard"
        st.rerun()
    st.write("這裡是未來可以擴充的 GAD-7 功能頁面。")

# =========================================================================
# 頁面 E：未來功能：機構數據分析後台 (analytics_module)
# =========================================================================
elif st.session_state.current_page == "analytics_module":
    if not st.session_state.permissions.get("can_access_analytics"):
        st.error("⛔ 您沒有權限存取此模組。")
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    st.title("📈 機構數據分析後台")
    if st.button("⬅️ 返回 fywebapp 主控制面板"):
        st.session_state.current_page = "dashboard"
        st.rerun()
    st.write("這裡是未來可以擴充的數據統計與圖表面板。")
