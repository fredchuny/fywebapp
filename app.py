import streamlit as st
from supabase import create_client, Client
import datetime
import pytz
import pandas as pd
import random

st.html(
    """
    <style>
    /* 1. 強制手機版保持雙欄網格 */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: wrap !important;
        }
        div[data-testid="column"], div[data-testid="stColumn"] {
            width: calc(50% - 0.5rem) !important;
            flex: 1 1 calc(50% - 0.5rem) !important;
            min-width: calc(50% - 0.5rem) !important;
        }
    }

    /* 2. 定義方形卡片按鈕 */
    div[data-testid="stButton"] button {
        height: 140px !important;          /* 🌟 稍微加高一點，給大 Emoji 留出空間 */
        width: 100% !important;
        border-radius: 16px !important;
        
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--faded-text-10) !important;
        
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05) !important;
        padding: 15px 10px !important;
        white-space: pre-line !important;  /* 🌟 必須維持 pre-line 才能分行 */
        transition: all 0.2s ease-in-out !important;
    }
    
    /* 3. 卡片內部的文字樣式 (第二行與之後的文字) */
    div[data-testid="stButton"] button p {
        font-size: 16px !important;        /* 🌟 讓下方文字大小適中 (16px) */
        font-weight: 600 !important;
        margin: 0 !important;
        line-height: 1.4 !important;
        text-align: center !important;
    }

    /* 4. 🎯 關鍵：單獨將第一行的 Emoji 放大 */
    div[data-testid="stButton"] button p::first-line {
        font-size: 36px !important;        /* 🌟 超大 Emoji 圖示！ */
        line-height: 1.6 !important;
    }

    /* 5. 點擊與懸浮動態回饋 */
    div[data-testid="stButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(0,0,0,0.1) !important;
        border-color: var(--primary-color) !important;
    }
    </style>
    """
)


# =========================================================================
# 臨床輔助函式
# =========================================================================
def get_severity(score, lang="zh"):
    if score <= 4: return "正常或極輕微抑鬱 (0-4分)" if lang == "zh" else "Minimal depression (0-4 pts)"
    if score <= 9: return "輕度抑鬱 (5-9分)" if lang == "zh" else "Mild depression (5-9 pts)"
    if score <= 14: return "中度抑鬱 (10-14分)" if lang == "zh" else "Moderate depression (10-14 pts)"
    if score <= 19: return "中重度抑鬱 (15-19分)" if lang == "zh" else "Moderately severe depression (15-19 pts)"
    return "重度抑鬱 (20-27分)" if lang == "zh" else "Severe depression (20-27 pts)"

# =========================================================================
# 1. 全域設定與初始化 (連線快取優化)
# =========================================================================
st.set_page_config(page_title="FY Web App", page_icon="🌼", layout="centered")

# 使用 cache_resource 優化 Supabase 連線效率
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

if "supabase" not in st.session_state:
    st.session_state.supabase = init_supabase()

# 安全機制：確保每次執行都檢查並自動刷新 Session / RLS 憑證
def sync_supabase_auth():
    try:
        session = st.session_state.supabase.auth.get_session()
        if session and session.access_token:
            st.session_state.supabase.postgrest.auth(session.access_token)
    except Exception as e:
        st.session_state.user = None

if "user" not in st.session_state: st.session_state.user = None
if "permissions" not in st.session_state: st.session_state.permissions = {}
if "current_page" not in st.session_state: st.session_state.current_page = "login"

# 🎯 路由防護：允許未登入存取的公開頁面
PUBLIC_PAGES = ["login", "quiz", "result"]
if st.session_state.user is None and st.session_state.current_page not in PUBLIC_PAGES:
    st.session_state.current_page = "login"

# 執行 RLS 身分同步
if st.session_state.user:
    sync_supabase_auth()


# 多國語言字典設定
lang_options = ["繁體中文 (Traditional Chinese)", "English"]
selected_lang = st.selectbox("🌐 Language / 語言", options=lang_options, index=0)
lang = "zh" if selected_lang == lang_options[0] else "en"

t = {
    "zh": {
        "login_title": "👋🏼 歡迎來到 FY Web App",
        "login_subtitle": "中央控制安全登入系統",
        "login_desc": "請在下方輸入您的工作人員帳號，開啟您的專屬工作面板 ✨",
        "email_label": "電子信箱 (Email)",
        "pass_label": "安全密碼 (Password)",
        "login_btn": "安全登入 🚀",
        "guest_btn": "📋 免登入直接填寫 PHQ-9 問卷",
        "logout_btn": "🚪 安全登出系統",
        "login_fail": "❌ 登入失敗：請確認帳號或密碼是否輸入正確。",
        "dash_title": "🌐 FY Web App 主控制面板",
        "dash_welcome": "歡迎回來！目前登入帳號：",
        "dash_section": "### 🗂️ 您已解鎖的功能模組：",
        "btn_phq9": "📝 進入 PHQ-9 臨床評估系統",
        "btn_water": "💧 進入 每日飲水追蹤系統",
        "btn_bujo": "📓 進入 子彈筆記隨手隨筆",
        "btn_food": "🍱 進入 今日食咩好？",
        "btn_gad7": "📊 進入 GAD-7 焦慮評估系統 (未來擴充)",
        "btn_analytics": "📈 進入 機構數據分析後台 (未來擴充)",
        "no_perm": "⚠️ 您的帳號目前尚未指派權限。請聯絡管理員幫您開啟權限喔！",
        "btn_back_dash": "⬅️ 返回 fywebapp 主面板",
        "btn_back_login": "⬅️ 返回登入頁面",
        # PHQ-9
        "phq9_title": "📝 PHQ-9 抑鬱症狀臨床評估", "phq9_subtitle": "📋 患者健康問卷 (PHQ-9)",
        "p_info_title": "### 🧑‍🦽 1. 患者基本資訊", "p_id_label": "患者編號 / 識別代碼 (必填)", "p_id_placeholder": "例如: Pt_Chen 或 P0001",
        "q_title": "### 📝 2. 量表評估作答", "q_info": "請詢問並根據患者 **過去兩星期** 以來受到下列問題困擾的頻率進行勾選：",
        "opt_0": "完全沒有 (0分)", "opt_1": "有幾天 (1分)", "opt_2": "一半以上的天數 (2分)", "opt_3": "幾乎天天 (3分)",
        "submit_btn": "🚀 提交患者報告", "view_hist_btn": "📁 檢視所有患者歷史紀錄", "err_pid": "⚠️ 請務必輸入『患者編號』才能提交報告喔！", "err_q": "⚠️ 請確保所有 9 道題目皆已作答評估完畢！",
        "success_匯入": "🎉 患者數據已成功安全匯入資料庫！", "rep_title": "📝 本次評估結果報告", "metric_p": "被評估患者", "metric_s": "PHQ-9 總得分", "status_lbl": "📊 **目前情緒狀態評級：**", "btn_next": "🔄 登記下一筆新問卷", "btn_all_hist": "📁 查看全歷史紀錄清單",
        "hist_title": "📁 患者歷史評估總表", "tz_title": "### 🌍 時區設定", "tz_select": "請選擇您目前的所在地時區：", "hist_desc": "以下是您登記過的所有患者檢測紀錄：", "no_hist": "📭 目前尚無任何提交紀錄。", "col_time": "登記時間 (時區)", "col_pid": "患者編號/代碼", "col_score": "PHQ-9 總分", "col_status": "狀態評級", "search_placeholder": "🔍 輸入患者編號篩選個人紀錄",
        # 飲水
        "water_title": "💧 每日飲水健康追蹤", "water_log_section": "### 📥 紀錄本次飲水", "water_label": "本次飲水量 (毫升 ml)", "water_notes": "備註說明 (選填)", "water_notes_placeholder": "例如：早起第一杯水...",
        "water_success": "🥤 成功紀錄！您剛剛喝了 {} ml 的水！", "water_err": "⚠️ 請輸入大於 0 的有效飲水量！", "water_review_section": "### 📊 歷史飲水追蹤與檢視", "water_col_time": "紀錄時間", "water_col_amount": "飲水量 (ml)", "water_col_notes": "備註", "water_no_data": "📭 您目前尚無 any 飲水紀錄，多喝水有益健康喔！", "water_total_today": "📅 今日累積總飲水量",
        # 子彈筆記
        "bujo_title": "📓 個人子彈隨筆筆記", "bujo_log_section": "### ✍🏼 新增子彈筆記", "bujo_type_lbl": "選擇筆記類型 (Bullet Icon)", "bujo_content_lbl": "筆記內容 (隨手記下今天發生的事情吧...)", "bujo_success": "✨ 成功將一筆子彈筆記儲存至日誌中！", "bujo_err": "⚠️ 內容空空的，寫點字再儲存吧！", "bujo_review_section": "### 📜 我的歷史子彈日誌", "bujo_col_time": "筆記時間", "bujo_col_type": "類型", "bujo_col_content": "內容明細", "bujo_no_data": "📭 目前還沒有寫下 any 子彈筆記喔。今天心情如何呢？",
        # 美食決策機
        "food_title": "🍱 今日食咩好？", "food_select_city": "🌍 選擇您目前所在的城市美食庫", "food_roll_section": "### 🎲 命運之輪：今天食咩好？", "food_roll_btn": "🎉 隨機幫我抽一個靈感！", "food_result_lbl": "💡 系統推薦您今天吃：", "food_empty_pool": "📭 目前的美食庫空空的，趕快在下方新增一些選項吧！", "food_add_section": "### ➕ 新增我的私藏美食選項", "food_name_lbl": "美食 / 餐廳 / 料理名稱 (例如：港式茶餐廳、Pho、乾炒牛河)", "food_privacy_lbl": "🔓 願意公開與所有人分享此美食選項 (不勾選則為個人私有)", "food_add_success": "🌟 成功將『{}』加入 {} 美食清單中！", "food_add_err": "⚠️ 請填寫美食名稱再行儲存！", "food_list_section": "### 📋 當前可抽獎的美食名單 (含個人私有與他人共享)", "col_food_name": "美食名稱", "col_food_src": "來源類型", "src_private": "🔒 僅自己可見 (Private)", "src_public": "🌐 眾人共享 (Shared)",
        "btn_yyems_lab": "📊 進入 YYEMS 數據實驗室", "yyems_lab_title": "📊 525APP_yyems 數據實驗室", "yyems_lab_caption": "💡 目前讀取雲端資料表：`525APP_yyems`（限制顯示最新 50 筆紀錄）", "yyems_lab_err": "📭 該資料表目前沒有數據。請確認名稱是否符合 `525APP_yyems`，或 RLS 是否阻擋了讀取。"
    },
    "en": {
        "login_title": "👋🏼 Welcome to fywebapp",
        "login_subtitle": "Central Security Login",
        "login_desc": "Please enter your staff credentials below to unlock your workspace ✨",
        "email_label": "Email Address",
        "pass_label": "Password",
        "login_btn": "Secure Login 🚀",
        "guest_btn": "📋 Take PHQ-9 Questionnaire without Login",
        "logout_btn": "🚪 Secure Logout",
        "login_fail": "❌ Login failed. Please double-check your email and password.",
        "dash_title": "🌐 FY Web App Main Dashboard",
        "dash_welcome": "Welcome back! Logged in as: ",
        "dash_section": "### 🗂️ Your Authorized Modules:",
        "btn_phq9": "📝 Access PHQ-9 Assessment System",
        "btn_water": "💧 Access Daily Water Tracking System",
        "btn_bujo": "📓 Access Personal Bullet Journal",
        "btn_food": "🍱 Access Food Picker Engine",
        "btn_gad7": "📊 Access GAD-7 Assessment System (Coming Soon)",
        "btn_analytics": "📈 Access Insights & Analytics Backoffice (Coming Soon)",
        "no_perm": "⚠️ Your account currently has no modules assigned. Please contact the administrator to grant permissions.",
        "btn_back_dash": "⬅️ Back to fywebapp Dashboard",
        "btn_back_login": "⬅️ Back to Login",
        # PHQ-9
        "phq9_title": "📝 PHQ-9 Depression Clinical Assessment", "phq9_subtitle": "📋 Patient Health Questionnaire (PHQ-9)",
        "p_info_title": "### 🧑‍🦽 1. Patient Information", "p_id_label": "Patient ID / Identifier (Required)", "p_id_placeholder": "e.g., Pt_Chen or P0001",
        "q_title": "### 📝 2. Questionnaire", "q_info": "Over the **last 2 weeks**, how often has the patient been bothered by any of the following problems:",
        "opt_0": "Not at all (0 pts)", "opt_1": "Several days (1 pt)", "opt_2": "More than half the days (2 pts)", "opt_3": "Nearly every day (3 pts)",
        "submit_btn": "🚀 Submit Patient Report", "view_hist_btn": "📁 View Patient History Logs", "err_pid": "⚠️ Please enter a Patient ID before submitting.", "err_q": "⚠️ Please ensure all 9 questions are answered.",
        "success_匯入": "🎉 Patient data has been securely uploaded to the database!", "rep_title": "📝 Assessment Report Summary", "metric_p": "Assessed Patient", "metric_s": "Total PHQ-9 Score", "status_lbl": "📊 **Current Severity Level:**", "btn_next": "🔄 Register Next Questionnaire", "btn_all_hist": "📁 View Full History Logs",
        "hist_title": "📁 Patient Assessment History Logs", "tz_title": "### 🌍 Timezone Settings", "tz_select": "Select your current local timezone:", "hist_desc": "Here are all the clinical records registered under your profile:", "no_hist": "📭 No records found.", "col_time": "Timestamp (Timezone)", "col_pid": "Patient ID", "col_score": "PHQ-9 Score", "col_status": "Severity Status", "search_placeholder": "🔍 Enter Patient ID to filter records",
        # 飲水
        "water_title": "💧 Daily Hydration Tracker", "water_log_section": "### 📥 Log Hydration", "water_label": "Amount of water (ml)", "water_notes": "Notes (Optional)", "water_notes_placeholder": "e.g., First cup in the morning...",
        "water_success": "🥤 Success! You just logged {} ml of water!", "water_err": "⚠️ Please enter a valid water amount greater than 0!", "water_review_section": "### 📊 Hydration History Review", "water_col_time": "Log Time", "water_col_amount": "Amount (ml)", "water_col_notes": "Notes", "water_no_data": "📭 No hydration data logged yet. Keep drinking water!", "water_total_today": "📅 Total Water Intake Today",
        # 子彈筆記
        "bujo_title": "📓 Personal Bullet Journal", "bujo_log_section": "### ✍🏼 Create Log Entry", "bujo_type_lbl": "Select Entry Type (Bullet Icon)", "bujo_content_lbl": "Journal Content (Jot down your thoughts, tasks, or mood...)", "bujo_success": "✨ Successfully saved entry to your journal log!", "bujo_err": "⚠️ Journal content cannot be empty!", "bujo_review_section": "### 📜 My Historical Bullet Logs", "bujo_col_time": "Logged Time", "bujo_col_type": "Type", "bujo_col_content": "Content Details", "bujo_no_data": "📭 Your bullet journal is empty. How are you feeling today?",
        # 美食決策機
        "food_title": "🍱 Meal Picker Decision Engine", "food_select_city": "🌍 Select your current location database", "food_roll_section": "### 🎲 Wheel of Fortune: What to eat today?", "food_roll_btn": "🎉 Randomly pick a meal option!", "food_result_lbl": "💡 Recommended for you today:", "food_empty_pool": "📭 The meal pool for this city is empty. Add some options below first!", "food_add_section": "### ➕ Add Custom Food Option", "food_name_lbl": "Food / Restaurant / Cuisine Name (e.g., Cha Chaan Teng, Pho, Ramen)", "food_privacy_lbl": "🔓 Allow everyone to draw this option (Shared / Public)", "food_add_success": "🌟 Successfully added '{}' into the {} list!", "food_add_err": "⚠️ Food name cannot be empty!", "food_list_section": "### 📋 Available Food Pool (Your Private Items + Community Shared Items)", "col_food_name": "Food Name", "col_food_src": "Source Type", "src_private": "🔒 Private (Just for you)", "src_public": "🌐 Shared (Public Option)",
        "btn_yyems_lab": "📊 Access YYEMS Data Lab", "yyems_lab_title": "📊 525APP_yyems Data Lab", "yyems_lab_caption": "💡 Currently reading cloud table: `525APP_yyems` (Limited to top 50 rows)", "yyems_lab_err": "📭 No data found. Please verify the table name is `525APP_yyems` or if RLS blocked the access.",
    }
}

# 全域側邊欄登出控制
if st.session_state.user is not None and st.session_state.current_page != "login":
    if st.sidebar.button(t[lang]["logout_btn"]):
        st.session_state.supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.permissions = {}
        st.session_state.current_page = "login"
        st.rerun()

# =========================================================================
# 頁面 A：中央控制登入入口
# =========================================================================
if st.session_state.current_page == "login":
    st.title(t[lang]["login_title"])
    st.subheader(t[lang]["login_subtitle"])
    st.write(t[lang]["login_desc"])
    
    with st.form("central_login_form"):
        email = st.text_input(t[lang]["email_label"])
        password = st.text_input(t[lang]["pass_label"], type="password")
        submit = st.form_submit_button(t[lang]["login_btn"])
        
        if submit and email and password:
            try:
                res = st.session_state.supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                role_resp = st.session_state.supabase.table("user_roles").select("*").eq("user_id", res.user.id).execute()
                
                if role_resp.data:
                    st.session_state.permissions = role_resp.data[0]
                else:
                    st.session_state.permissions = {"can_access_phq9": False, "can_access_water": False, "can_access_bujo": False, "can_access_food_picker": False, "can_access_gad7": False, "can_access_analytics": False}
                
                st.session_state.current_page = "dashboard"; st.rerun()
            except Exception:
                st.error(t[lang]["login_fail"])

    # 🎯 免登入訪客問卷入口按鈕
    st.divider()
    if st.button(t[lang]["guest_btn"], use_container_width=True):
        st.session_state.current_page = "quiz"
        st.rerun()

# =========================================================================
# 頁面 B：中央主控面板
# =========================================================================
elif st.session_state.current_page == "dashboard":
    st.title(t[lang]["dash_title"])
    st.write(f"{t[lang]['dash_welcome']}`{st.session_state.user.email}`")
    st.divider()
    st.write(t[lang]["dash_section"])
    
    perms = st.session_state.permissions
    active_modules = []
    
    if perms.get("can_access_phq9"):
        active_modules.append({"label": f"📝\n{t[lang]['btn_phq9']}", "page": "quiz"})
    if perms.get("can_access_water"):
        active_modules.append({"label": f"💧\n{t[lang]['btn_water']}", "page": "water_module"})
    if perms.get("can_access_bujo"):
        active_modules.append({"label": f"📓\n{t[lang]['btn_bujo']}", "page": "bujo_module"})
    if perms.get("can_access_food_picker"):
        active_modules.append({"label": f"🍱\n{t[lang]['btn_food']}", "page": "food_module"})
    if perms.get("can_access_525APP_yyems"):
        active_modules.append({"label": f"📊\n{t[lang]['btn_yyems_lab']}", "page": "yyems_page"})

    if not active_modules:
        st.warning(t[lang]["no_perm"])
    else:
        for i in range(0, len(active_modules), 2):
            cols = st.columns(2)
            if i < len(active_modules):
                with cols[0]:
                    if st.button(active_modules[i]["label"], key=f"grid_{i}", use_container_width=True):
                        st.session_state.current_page = active_modules[i]["page"]
                        st.rerun()
            if i + 1 < len(active_modules):
                with cols[1]:
                    if st.button(active_modules[i+1]["label"], key=f"grid_{i+1}", use_container_width=True):
                        st.session_state.current_page = active_modules[i+1]["page"]
                        st.rerun()

        st.divider()
        st.write("### ⏳ 未來擴充功能 (Coming Soon)")
        cols_future = st.columns(2)
        with cols_future[0]:
            st.button(t[lang]["btn_gad7"], use_container_width=True, disabled=True)
        with cols_future[1]:
            st.button(t[lang]["btn_analytics"], use_container_width=True, disabled=True)

# =========================================================================
# 頁面 C-1：PHQ-9 問卷作答頁面 (支援未登入訪客作答)
# =========================================================================
elif st.session_state.current_page == "quiz":
    # 🎯 只有在「已登入」且「權限關閉」的情況下才阻擋；未登入訪客放行
    if st.session_state.user and not st.session_state.permissions.get("can_access_phq9", True): 
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    st.title(t[lang]["phq9_title"])
    
    # 🎯 動態返回按鈕目標
    back_btn_label = t[lang]["btn_back_dash"] if st.session_state.user else t[lang]["btn_back_login"]
    back_target = "dashboard" if st.session_state.user else "login"
    
    if st.sidebar.button(back_btn_label, key="back_quiz"): 
        st.session_state.current_page = back_target
        st.rerun()
        
    st.subheader(t[lang]["phq9_subtitle"])
    st.write(t[lang]["p_info_title"])
    patient_id = st.text_input(t[lang]["p_id_label"], placeholder=t[lang]["p_id_placeholder"])
    st.divider(); st.write(t[lang]["q_title"]); st.info(t[lang]["q_info"])

    # 1. 由 Supabase 抓取 question_items (包含英文與中文題目)
    questions_data = []
    try:
        session = st.session_state.supabase.auth.get_session()
        if session: 
            st.session_state.supabase.postgrest.auth(session.access_token)
            
        resp = st.session_state.supabase.table("question_items") \
            .select("link_id, display_order, question_text, question_text_zh, value_type, type_config") \
            .eq("questionnaire_id", "phq-9") \
            .order("display_order") \
            .execute()
        questions_data = resp.data
    except Exception as e:
        st.error(f"⚠️ 無法讀取題目列表：{e}")

    # 2. 雙語選項標籤字典 (0–3 分)
    opt_labels = {
        "zh": [t["zh"]["opt_0"], t["zh"]["opt_1"], t["zh"]["opt_2"], t["zh"]["opt_3"]],
        "en": [t["en"]["opt_0"], t["en"]["opt_1"], t["en"]["opt_2"], t["en"]["opt_3"]]
    }
    current_options = opt_labels[lang]
    score_map = {current_options[i]: i for i in range(4)}

    # 3. 動態渲染表單
    user_answers = {}
    if questions_data:
        for q in questions_data:
            link_id = q["link_id"]
            order = q["display_order"]
            
            q_text = q["question_text_zh"] if lang == "zh" and q.get("question_text_zh") else q["question_text"]
            prompt = f"{order}. {q_text}"

            if q["value_type"] == "choice":
                selected_label = st.radio(prompt, current_options, index=None, key=f"q_{link_id}")
                if selected_label:
                    user_answers[link_id] = score_map[selected_label]
                else:
                    user_answers[link_id] = None

    col_submit, col_go_hist = st.columns(2)
    with col_submit:
        if st.button(t[lang]["submit_btn"], type="primary", use_container_width=True):
            if not patient_id.strip(): 
                st.error(t[lang]["err_pid"])
            elif None in user_answers.values() or len(user_answers) < len(questions_data): 
                st.error(t[lang]["err_q"])
            else:
                total_score = sum(user_answers.values())
                severity = get_severity(total_score, lang=lang)

                try:
                    session = st.session_state.supabase.auth.get_session()
                    if session: 
                        st.session_state.supabase.postgrest.auth(session.access_token)
                    
                    # 🎯 訪客提交時 user_id 填入 None
                    current_user_id = st.session_state.user.id if st.session_state.user else None

                    payload = {
                        "user_id": current_user_id,
                        "patient_id": patient_id.strip(),
                        "questionnaire_id": "phq-9",
                        "answers": user_answers,
                        "total_score": total_score
                    }
                    
                    # 寫入資料庫
                    st.session_state.supabase.table("patient_responses").insert(payload).execute()
                    
                    # 安全寫入 Session State 並切換至結果頁
                    st.session_state.last_score = total_score
                    st.session_state.last_severity = severity
                    st.session_state.last_patient = patient_id.strip()
                    st.session_state.current_page = "result"
                    st.rerun()
                except Exception as e: 
                    st.error(f"❌ 儲存失敗，請檢查 RLS 權限或連線狀況：{e}")

    with col_go_hist:
        # 僅限已登入工作人員查看歷史紀錄
        if st.session_state.user:
            if st.button(t[lang]["view_hist_btn"], use_container_width=True): 
                st.session_state.current_page = "history"
                st.rerun()

# =========================================================================
# 頁面 C-2：PHQ-9 評估結果頁面
# =========================================================================
elif st.session_state.current_page == "result":
    p_name = st.session_state.get("last_patient", "N/A")
    p_score = st.session_state.get("last_score", 0)
    p_severity = st.session_state.get("last_severity", get_severity(p_score, lang=lang))

    st.balloons()
    st.success(t[lang]['success_匯入'])
    st.subheader(t[lang]["rep_title"])
    
    col_p, col_s = st.columns(2)
    with col_p: 
        st.metric(label=t[lang]["metric_p"], value=p_name)
    with col_s: 
        st.metric(label=t[lang]["metric_s"], value=f"{p_score} / 27")
        
    st.info(f"{t[lang]['status_lbl']} {p_severity}")
    st.divider()
    
    col_again, col_hist = st.columns(2)
    with col_again:
        if st.button(t[lang]["btn_next"], type="primary", use_container_width=True): 
            st.session_state.current_page = "quiz"
            st.rerun()
    with col_hist:
        if st.session_state.user:
            if st.button(t[lang]["btn_all_hist"], use_container_width=True): 
                st.session_state.current_page = "history"
                st.rerun()
        else:
            if st.button(t[lang]["btn_back_login"], use_container_width=True):
                st.session_state.current_page = "login"
                st.rerun()

# =========================================================================
# 頁面 C-3：PHQ-9 歷史紀錄頁面 (僅限登入人員)
# =========================================================================
elif st.session_state.current_page == "history":
    if not st.session_state.user:
        st.session_state.current_page = "login"
        st.rerun()

    st.subheader(t[lang]["hist_title"])
    
    if st.button(t[lang]["btn_back_dash"], key="top_back_hist"):
        st.session_state.current_page = "quiz"
        st.rerun()
    if st.sidebar.button(t[lang]["btn_back_dash"], key="back_hist"): 
        st.session_state.current_page = "quiz"
        st.rerun()
        
    user_tz_name = st.selectbox(
        t[lang]["tz_select"], 
        options=["America/Toronto", "Asia/Hong_Kong", "UTC"] + sorted(pytz.common_timezones), 
        index=0
    )
    local_tz = pytz.timezone(user_tz_name)
    st.divider()

    try:
        session = st.session_state.supabase.auth.get_session()
        if session: 
            st.session_state.supabase.postgrest.auth(session.access_token)
        
        response = st.session_state.supabase.table("patient_responses") \
            .select("created_at, patient_id, total_score, answers") \
            .eq("questionnaire_id", "phq-9") \
            .order("created_at", desc=True) \
            .execute()
            
        records_data = response.data
        
        if not records_data: 
            st.warning(t[lang]["no_hist"])
        else:
            table_list = []
            for record in records_data:
                raw_time = record.get("created_at", "")
                try:
                    dt_utc = datetime.datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                    dt_local = dt_utc.astimezone(local_tz)
                    formatted_time = f"{dt_local.strftime('%Y-%m-%d %H:%M')} ({dt_local.strftime('%Z')})"
                except Exception: 
                    formatted_time = raw_time
                
                score = record.get("total_score", 0)
                severity_status = get_severity(score, lang=lang)

                table_list.append({
                    t[lang]["col_time"]: formatted_time,
                    t[lang]["col_pid"]: record.get("patient_id", "N/A"),
                    t[lang]["col_score"]: f"{score} / 27",
                    t[lang]["col_status"]: severity_status
                })

            df = pd.DataFrame(table_list)
            search_query = st.text_input(t[lang]["search_placeholder"])
            if search_query: 
                df = df[df[t[lang]["col_pid"]].str.contains(search_query, case=False, na=False)]
            
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e: 
        st.error(f"❌ 讀取歷史紀錄失敗：{e}")


# =========================================================================
# 頁面 D：💧 每日飲水追蹤系統模組
# =========================================================================
elif st.session_state.current_page == "water_module":
    if not st.session_state.permissions.get("can_access_water"): st.session_state.current_page = "dashboard"; st.rerun()
    st.title(t[lang]["water_title"])
    if st.sidebar.button(t[lang]["btn_back_dash"], key="back_water"): st.session_state.current_page = "dashboard"; st.rerun()
    user_tz_name = st.selectbox("🌍 Timezone / 時區", options=["America/Toronto", "Asia/Hong_Kong", "UTC"], index=0, key="water_tz")
    local_tz = pytz.timezone(user_tz_name); st.divider(); st.write(t[lang]["water_log_section"])
    
    with st.form("water_log_form"):
        amount = st.number_input(t[lang]["water_label"], min_value=0, value=250, step=50)
        notes = st.text_input(t[lang]["water_notes"], placeholder=t[lang]["water_notes_placeholder"])
        water_submit = st.form_submit_button("💾 Save")
        
        if water_submit:
            if amount > 0:
                try:
                    session = st.session_state.supabase.auth.get_session()
                    if session: st.session_state.supabase.postgrest.auth(session.access_token)
                    st.session_state.supabase.table("water_logs").insert({"user_id": st.session_state.user.id, "amount_ml": int(amount), "notes": notes.strip()}).execute()
                    st.success(t[lang]["water_success"].format(amount))
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
            else:
                st.error(t[lang]["water_err"])
                
    st.divider(); st.write(t[lang]["water_review_section"])
    try:
        session = st.session_state.supabase.auth.get_session()
        if session: st.session_state.supabase.postgrest.auth(session.access_token)
        resp = st.session_state.supabase.table("water_logs").select("created_at, amount_ml, notes").eq("user_id", st.session_state.user.id).order("created_at", desc=True).execute()
        if not resp.data: st.warning(t[lang]["water_no_data"])
        else:
            water_list = []; today_total = 0; now_local = datetime.datetime.now(local_tz)
            for log in resp.data:
                dt_utc = datetime.datetime.fromisoformat(log["created_at"].replace("Z", "+00:00")); dt_local = dt_utc.astimezone(local_tz)
                if dt_local.date() == now_local.date(): today_total += log["amount_ml"]
                water_list.append({t[lang]["water_col_time"]: f"{dt_local.strftime('%Y-%m-%d %H:%M')} ({dt_local.strftime('%Z')})", t[lang]["water_col_amount"]: log["amount_ml"], t[lang]["water_col_notes"]: log["notes"]})
            st.metric(label=t[lang]["water_total_today"], value=f"{today_total} ml / 2000 ml"); st.progress(min(today_total / 2000.0, 1.0))
            st.dataframe(pd.DataFrame(water_list), use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"Error: {e}")

# =========================================================================
# 頁面 E：📓 子彈筆記隨手隨筆模組
# =========================================================================
elif st.session_state.current_page == "bujo_module":
    if not st.session_state.permissions.get("can_access_bujo"): st.session_state.current_page = "dashboard"; st.rerun()
    st.title(t[lang]["bujo_title"])
    if st.sidebar.button(t[lang]["btn_back_dash"], key="back_bujo"): st.session_state.current_page = "dashboard"; st.rerun()
    user_tz_name = st.selectbox("🌍 Timezone / 時區", options=["America/Toronto", "Asia/Hong_Kong", "UTC"], index=0, key="bujo_tz")
    local_tz = pytz.timezone(user_tz_name); st.divider(); st.write(t[lang]["bujo_log_section"])
    
    with st.form("bujo_log_form"):
        bujo_types = ["任務 •", "事件 ○", "筆記 -", "靈感 💡", "心情 💖"] if lang == "zh" else ["Task •", "Event ○", "Note -", "Idea 💡", "Mood 💖"]
        b_type = st.selectbox(t[lang]["bujo_type_lbl"], options=bujo_types)
        b_content = st.text_area(t[lang]["bujo_content_lbl"], height=100)
        bujo_submit = st.form_submit_button("💾 Save Entry")
        
        if bujo_submit:
            if b_content.strip():
                try:
                    session = st.session_state.supabase.auth.get_session()
                    if session: st.session_state.supabase.postgrest.auth(session.access_token)
                    st.session_state.supabase.table("bullet_journal").insert({"user_id": st.session_state.user.id, "entry_type": b_type, "content": b_content.strip()}).execute()
                    st.success(t[lang]["bujo_success"])
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
            else:
                st.error(t[lang]["bujo_err"])
                
    st.divider(); st.write(t[lang]["bujo_review_section"])
    try:
        session = st.session_state.supabase.auth.get_session()
        if session: st.session_state.supabase.postgrest.auth(session.access_token)
        resp = st.session_state.supabase.table("bullet_journal").select("created_at, entry_type, content").eq("user_id", st.session_state.user.id).order("created_at", desc=True).execute()
        if not resp.data: st.warning(t[lang]["bujo_no_data"])
        else:
            bujo_list = []
            for item in resp.data:
                dt_utc = datetime.datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")); dt_local = dt_utc.astimezone(local_tz)
                bujo_list.append({t[lang]["bujo_col_time"]: f"{dt_local.strftime('%Y-%m-%d %H:%M')} ({dt_local.strftime('%Z')})", t[lang]["bujo_col_type"]: item.get("entry_type"), t[lang]["bujo_col_content"]: item.get("content")})
            st.dataframe(pd.DataFrame(bujo_list), use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"Error: {e}")

# =========================================================================
# 頁面 F：🍱 今日美食決策抽獎機模組
# =========================================================================
elif st.session_state.current_page == "food_module":
    if not st.session_state.permissions.get("can_access_food_picker"):
        st.session_state.current_page = "dashboard"; st.rerun()
        
    st.title(t[lang]["food_title"])
    if st.sidebar.button(t[lang]["btn_back_dash"], key="back_food"):
        st.session_state.current_page = "dashboard"; st.rerun()
        
    st.write(t[lang]["food_select_city"])
    city_choice = st.radio("📍 City / 城市", options=["Hong Kong", "Toronto"], horizontal=True)
    st.divider()
    
    food_pool = []
    raw_items = []
    try:
        session = st.session_state.supabase.auth.get_session()
        if session: st.session_state.supabase.postgrest.auth(session.access_token)
        
        resp = st.session_state.supabase.table("food_options").select("id, food_name, is_public, user_id").eq("city", city_choice).execute()
        raw_items = resp.data
        food_pool = [item["food_name"] for item in raw_items]
    except Exception as e:
        st.error(f"Error loading food pool: {e}")

    st.write(t[lang]["food_roll_section"])
    if not food_pool:
        st.warning(t[lang]["food_empty_pool"])
    else:
        if st.button(t[lang]["food_roll_btn"], type="primary", use_container_width=True):
            chosen_meal = random.choice(food_pool)
            st.balloons()
            st.success(f"{t[lang]['food_result_lbl']} **✨ {chosen_meal} ✨**")
            
    st.divider()
    
    st.write(t[lang]["food_add_section"])
    with st.form("add_food_form"):
        new_food = st.text_input(t[lang]["food_name_lbl"])
        is_public_checked = st.checkbox(t[lang]["food_privacy_lbl"], value=False)
        food_add_submit = st.form_submit_button("➕ Save Food / 儲存選項")
        
        if food_add_submit:
            if new_food.strip():
                try:
                    session = st.session_state.supabase.auth.get_session()
                    if session: st.session_state.supabase.postgrest.auth(session.access_token)
                    
                    st.session_state.supabase.table("food_options").insert({
                        "user_id": st.session_state.user.id,
                        "city": city_choice,
                        "food_name": new_food.strip(),
                        "is_public": is_public_checked
                    }).execute()
                    st.success(t[lang]["food_add_success"].format(new_food.strip(), city_choice))
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error(t[lang]["food_add_err"])
                
    st.divider()
    
    st.write(t[lang]["food_list_section"])
    if raw_items:
        display_list = []
        for item in raw_items:
            src_text = t[lang]["src_public"] if item.get("is_public") else t[lang]["src_private"]
            display_list.append({
                t[lang]["col_food_name"]: item.get("food_name"),
                t[lang]["col_food_src"]: src_text
            })
        st.dataframe(pd.DataFrame(display_list), use_container_width=True, hide_index=True)

# =========================================================================
# 頁面 G：525APP_yyems 獨立核心數據面板
# =========================================================================
elif st.session_state.current_page == "yyems_page":
    st.title(t[lang]["yyems_lab_title"])
    
    if st.button(t[lang]["btn_back_dash"], key="top_back_yyems"):
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    if st.sidebar.button(t[lang]["btn_back_dash"], key="side_back_yyems"):
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    try:
        session = st.session_state.supabase.auth.get_session()
        if session: 
            st.session_state.supabase.postgrest.auth(session.access_token)
            
        st.caption("💡 系統已成功安全對接雲端 `525APP_yyems` 完整歷史數據庫")
        
        @st.cache_data(ttl=600)
        def load_all_yyems_data():
            all_records = []
            chunk_size = 1000
            start = 0
            while True:
                resp = st.session_state.supabase.table("525APP_yyems").select("*").range(start, start + chunk_size - 1).order("DateTime", desc=True).execute()
                data = resp.data
                if not data:
                    break
                all_records.extend(data)
                if len(data) < chunk_size:
                    break
                start += chunk_size
            return all_records

        records = load_all_yyems_data()
        
        if not records:
            st.warning(t[lang]["yyems_lab_err"])
        else:
            df_all = pd.DataFrame(records)
            
            if "auto_amount" in df_all.columns:
                df_all["auto_amount"] = pd.to_numeric(df_all["auto_amount"], errors='coerce').fillna(0)
            if "auto_div_amount" in df_all.columns:
                df_all["auto_div_amount"] = pd.to_numeric(df_all["auto_div_amount"], errors='coerce').fillna(0)
                
            if "auto_stat_month" in df_all.columns:
                df_all["auto_stat_month"] = df_all["auto_stat_month"].astype(str)
                df_all = df_all[df_all["auto_stat_month"] != "nan"]
            
            cat_col = "auto_vendor_一級分類" if "auto_vendor_一級分類" in df_all.columns else "In_or_out"
            
            st.write("### 🎛️ 專屬財務分流與搜尋控制")
            col_view, col_currency, col_search = st.columns([1.5, 1, 1.5])
            
            with col_view:
                ownership_view = st.radio(
                    "📊 選擇分流視角 (Ownership Filter)", 
                    options=["全部顯示 (Show All Records)", "共同 + FRD (yyems + frd)", "共同 + CTY (yyems + cty)"], 
                    index=0
                )
            
            with col_currency:
                if "Currency" in df_all.columns:
                    available_currencies = ["全部 (All)"] + sorted(df_all["Currency"].dropna().unique().tolist())
                else:
                    available_currencies = ["全部 (All)"]
                selected_currency = st.selectbox("💱 篩選幣別 (Currency)", options=available_currencies, index=0)
                
            with col_search:
                search_query = st.text_input("🔍 關鍵字搜尋 (備註、說明、商家或 ID)", "")
                
            df_filtered = df_all.copy()
            
            if ownership_view == "全部顯示 (Show All Records)":
                target_amount_col = "auto_amount"
            else:
                target_amount_col = "auto_div_amount"
                if "Ownership" in df_filtered.columns:
                    df_filtered["Ownership_lower"] = df_filtered["Ownership"].astype(str).str.lower()
                    if ownership_view == "共同 + FRD (yyems + frd)":
                        df_filtered = df_filtered[df_filtered["Ownership_lower"].isin(["yyems", "frd"])]
                    elif ownership_view == "共同 + CTY (yyems + cty)":
                        df_filtered = df_filtered[df_filtered["Ownership_lower"].isin(["yyems", "cty"])]
                    df_filtered = df_filtered.drop(columns=["Ownership_lower"])

            if selected_currency != "全部 (All)" and "Currency" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["Currency"] == selected_currency]

            if search_query:
                search_mask = False
                for col in ["description", "remark", "YYEMS ID", "auto_vendor_name"]:
                    if col in df_filtered.columns:
                        search_mask |= df_filtered[col].astype(str).str.contains(search_query, case=False, na=False)
                df_filtered = df_filtered[search_mask]
            
            amt_label = "auto_amount (原始總額)" if target_amount_col == "auto_amount" else "auto_div_amount (分帳總額)"
            total_calc_amount = df_filtered[target_amount_col].sum() if target_amount_col in df_filtered.columns else 0.0
            st.metric(label=f"💰 當前篩選條件下計算總額 (基於 {amt_label})", value=f"${total_calc_amount:,.2f}")
            
            st.divider()

            st.write("### 🗂️ 歷史每月分類交叉透視表 (對標 Excel Pivot Table)")
            
            if "auto_stat_month" in df_filtered.columns and cat_col in df_filtered.columns:
                all_months_sorted = sorted(df_filtered["auto_stat_month"].unique().tolist(), reverse=True)
                
                if "yyems_month_page" not in st.session_state:
                    st.session_state.yyems_month_page = 0
                
                months_per_page = 5
                max_pages = max(0, (len(all_months_sorted) - 1) // months_per_page)
                
                if st.session_state.yyems_month_page > max_pages:
                    st.session_state.yyems_month_page = max_pages
                
                start_idx = st.session_state.yyems_month_page * months_per_page
                end_idx = start_idx + months_per_page
                current_visible_months = all_months_sorted[start_idx:end_idx]
                
                col_prev_btn, col_page_status, col_next_btn = st.columns([1, 2, 1])
                
                with col_prev_btn:
                    if st.button("⬅️ 往後看舊 5 個月", disabled=(st.session_state.yyems_month_page >= max_pages), use_container_width=True):
                        st.session_state.yyems_month_page += 1
                        st.rerun()
                        
                with col_page_status:
                    if current_visible_months:
                        st.markdown(f"<p style='text-align: center; color: gray; margin-top: 10px;'>📅 目前顯示：<b>{current_visible_months[-1]}</b> 至 <b>{current_visible_months[0]}</b> (第 {st.session_state.yyems_month_page + 1}/{max_pages + 1} 頁)</p>", unsafe_allow_html=True)
                    else:
                        st.write("無月份資料")
                        
                with col_next_btn:
                    if st.button("➡️ 往前看近 5 個月", disabled=(st.session_state.yyems_month_page == 0), use_container_width=True):
                        st.session_state.yyems_month_page -= 1
                        st.rerun()
                
                df_page_visible = df_filtered[df_filtered["auto_stat_month"].isin(current_visible_months)]
                
                if not df_page_visible.empty:
                    pivot_df = df_page_visible.pivot_table(
                        values=target_amount_col,
                        index="auto_stat_month",
                        columns=cat_col,
                        aggfunc="sum",
                        fill_value=0
                    ).sort_index(ascending=True)
                    
                    pivot_df["Total Grand Total"] = pivot_df.sum(axis=1)
                    
                    def color_negative_positive(val):
                        if val < 0:
                            return 'color: #D32F2F; font-weight: bold;'
                        elif val > 0:
                            return 'color: #388E3C; font-weight: bold;'
                        return 'color: #A0A0A0;'
                    
                    styled_pivot = pivot_df.style.format("{:,.2f}").map(color_negative_positive)
                    st.dataframe(styled_pivot, use_container_width=True)
                else:
                    st.info("ℹ️ 該頁面範圍內無可顯示的數據。")

            st.divider()
            
            st.write("### 🍕 每月類別佔比分析 (Category Analysis per Month)")
            if "auto_stat_month" in df_filtered.columns:
                pie_months = current_visible_months if current_visible_months else all_months_sorted
                
                if pie_months:
                    selected_month = st.selectbox("📅 選擇要查看佔比的指定月份：", options=pie_months, index=0)
                    df_month = df_filtered[df_filtered["auto_stat_month"] == selected_month]
                    
                    pie_data = df_month.groupby(cat_col)[target_amount_col].sum().reset_index()
                    pie_data["display_amount"] = pie_data[target_amount_col].abs()
                    
                    if not pie_data.empty and pie_data["display_amount"].sum() > 0:
                        st.write(f"#### 📊 {selected_month} 月份 - 各類別金額與比例明細")
                        col_pie_chart, col_pie_table = st.columns([1, 1])
                        
                        with col_pie_table:
                            pie_data["比例 (%)"] = (pie_data["display_amount"] / pie_data["display_amount"].sum() * 100).round(1)
                            st.dataframe(pie_data[[cat_col, target_amount_col, "比例 (%)"]].rename(columns={target_amount_col: "實際加總金額"}), use_container_width=True, hide_index=True)
                            
                        with col_pie_chart:
                            import altair as alt
                            pie_chart = alt.Chart(pie_data).mark_arc(innerRadius=0, outerRadius=100).encode(
                                theta=alt.Theta(field="display_amount", type="quantitative"),
                                color=alt.Color(field=cat_col, type="nominal", legend=alt.Legend(title="分類")),
                                tooltip=[alt.Tooltip(field=cat_col, title="分類"), alt.Tooltip(field=target_amount_col, title="實際金額", format=",.2f"), alt.Tooltip(field="比例 (%)", title="佔比")]
                            ).properties(width=250, height=250)
                            st.altair_chart(pie_chart, use_container_width=True)
                    else:
                        st.info("ℹ️ 該月份無足夠的金額數據生成圖表。")
            
            st.divider()
            
            st.write(f"📋 **交易原始明細：共 {len(df_filtered)} 筆**")
            st.dataframe(df_filtered, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"Error processing rolling visual dashboard: {e}")

# 未來擴充頁面
elif st.session_state.current_page == "gad7_module":
    st.title(t[lang]["btn_gad7"])
    if st.button(t[lang]["btn_back_dash"]): st.session_state.current_page = "dashboard"; st.rerun()
elif st.session_state.current_page == "analytics_module":
    st.title(t[lang]["btn_analytics"])
    if st.button(t[lang]["btn_back_dash"]): st.session_state.current_page = "dashboard"; st.rerun()

# 防錯預設落腳頁面
else:
    st.session_state.current_page = "login"
    st.rerun()
