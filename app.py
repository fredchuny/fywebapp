import streamlit as st
from supabase import create_client, Client
import datetime
import pytz

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
            st.session_state.current_page = "phq9_module"
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
# 頁面 C：PHQ-9 臨床評估系統模組 (phq9_module)
# =========================================================================
elif st.session_state.current_page == "phq9_module":
    # 二次前端守衛，防止非法跳轉
    if not st.session_state.permissions.get("can_access_phq9"):
        st.error("⛔ 您沒有權限存取此模組。")
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    st.title("📝 PHQ-9 抑鬱症狀臨床評估")
    
    # 返回主面板按鈕
    if st.button("⬅️ 返回 fywebapp 主控制面板"):
        st.session_state.current_page = "dashboard"
        st.rerun()
        
    st.divider()
    
    # ---------------------------------------------------------------------
    # 💡 這裡放妳原本完整的 PHQ-9 程式碼邏輯 
    # (例如：st.tabs(["基本資料", "問卷填寫", "歷史紀錄"])、妳的資料寫入與時間轉換邏輯等)
    # ---------------------------------------------------------------------
    st.info("💡 妳原本做好的 PHQ-9 量表填寫、自動計分、時區轉換與歷史紀錄總表功能，將會完美呈現在此區塊中！")
    
    # 範例：安全寫入資料庫時拿取當前使用者真實 UUID 的寫法：
    # current_uid = st.session_state.user.id

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
