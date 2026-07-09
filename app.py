import streamlit as st
from supabase import create_client, Client

# 1. 初始化 Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 處理網頁跳轉後的登入狀態 (OAuth Session) ---
# 當使用者從 Google 登入跳轉回來時，網址會帶有 access_token，這裡用來攔截並保持登入
query_params = st.query_params
if "access_token" in query_params:
    # 這裡可以透過 token 讓 supabase 記住 session，為保持極簡，我們主要依賴 Supabase 內建狀態
    pass

# 檢查當前是否有登入的使用者
user = None
try:
    session = supabase.auth.get_session()
    if session and session.user:
        user = session.user
except Exception:
    pass

# --- 介面開始 ---
st.title("📊 PHQ-9 完整健康評估系統")

# ==================================================================
# 🔒 狀況 A：使用者尚未登入 ➜ 顯示 Google 登入按鈕
# ==================================================================
if not user:
    st.info("👋 歡迎使用本系統！為了保護您的隱私與紀錄追蹤，請先登入。")
    
    # 點擊按鈕後，會直接導向 Google 的官方登入畫面
    if st.button("🚀 使用 Google 帳號登入", type="primary"):
        try:
            # 這裡的 redirectTo 會在登入成功後把使用者帶回你的 Streamlit 網站
            auth_url = supabase.auth.get_oauth_nav_url({
                "provider": "google",
                "redirect_to": st.secrets.get("STREAMLIT_APP_URL", "http://localhost:8501") # 正式環境請在 Secrets 設好網址
            })
            # 透過 Streamlit 的跳轉功能前往 Google
            st.markdown(f'<meta http-equiv="refresh" content="0;URL=\'{auth_url}\'" />', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"啟動 Google 登入失敗：{e}")

# ==================================================================
# 🎉 狀況 B：使用者已成功登入 ➜ 顯示問卷與歷史查詢（完全隱藏手動 ID 輸入）
# ==================================================================
else:
    # 🎯 自動從 Google 帳號中撈取使用者的系統 UUID 與 Email 姓名
    user_id = user.id  # 這是一串全宇宙唯一的 UUID，例如: d3b07384...
    user_email = user.email
    # 有些 Google 帳號可以撈到全名，撈不到就拿 Email 前綴當名字
    full_name = user.user_metadata.get("full_name", user_email.split("@")[0])
    
    st.success(f"🟢 已成功連線 | 歡迎回來，{full_name} ({user_email})")
    
    if st.button("登出帳號"):
        supabase.auth.sign_out()
        st.rerun()

    st.write("---")
    st.write("### 過去兩星期以來，您有多少天受以下問題困擾？")
    
    options = {0: "0 - 完全沒有", 1: "1 - 有幾天", 2: "2 - 一半以上的天數", 3: "3 - 幾乎天天"}

    # 9 道題目（維持並排單選鈕）
    q1_score = st.radio("1. 做任何事情都提不起勁或沒有樂趣", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
    q2_score = st.radio("2. 感到心情低落、沮喪或絕望", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
    q3_score = st.radio("3. 入睡困難、睡不安穩或睡太多", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
    q4_score = st.radio("4. 感到疲倦或沒有活力", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
    st.write("---")
    q5_score = st.radio("5. 食慾不振或吃得太多", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
    q6_score = st.radio("6. 覺得自己很糟、覺得自己很失敗，或讓家人失望", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
    q7_score = st.radio("7. 專注事情有困難，例如看報紙或看電視時", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
    q8_score = st.radio("8. 動作或說話速度慢到別人察覺？或正好相反，煩躁不安到處走動？", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
    st.write("---")
    q9_score = st.radio("9. 有自殺或傷害自己的想法", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)

    # 計算總分
    q_list = [q1_score, q2_score, q3_score, q4_score, q5_score, q6_score, q7_score, q8_score, q9_score]  
    total_score = sum(q_list)

    st.write("---")
    st.write(f"### 📊 目前評估總分：**{total_score} 分**")

    # 送出問卷按鈕
    if st.button("確認送出並上傳雲端"):
        try:
            # 1. 寫入或更新使用者基本資料（這裡的 id 就是自動抓到的 Google UUID）
            user_data = {"id": user_id, "full_name": full_name, "role": "patient"}
            supabase.table("phq9_users").upsert(user_data).execute()
            
            # 2. 完整寫入 9 題的分數紀錄
            response_data = {
                "user_id": user_id, # 👈 自動帶入，使用者完全無感
                "q1": q1_score, "q2": q2_score, "q3": q3_score, "q4": q4_score, "q5": q5_score, 
                "q6": q6_score, "q7": q7_score, "q8": q8_score, "q9": q9_score,
                "total_score": total_score
            }
            supabase.table("phq9_responses").insert(response_data).execute()
            
            st.success(f"🎉 成功！數據已自動歸類至您的帳號。總分：{total_score} 分。")
        except Exception as e:
            st.error(f"寫入失敗：{e}")

    # ==================================================================
    # 🔍 歷史紀錄查詢區塊（自動帶入登入者的 UUID，別人絕對查不到）
    # ==================================================================
    st.write("---")
    st.write("## 🔍 您的歷史結果查詢")
    
    if st.button("查看我的歷史評估紀錄"):
        try:
            with st.spinner("正在查詢您的專屬雲端病歷..."):
                response = supabase.table("phq9_responses") \
                                   .select("created_at, total_score") \
                                   .eq("user_id", user_id) \
                                   .order("created_at", desc=False) \
                                   .execute()
            
            if response.data:
                st.success(f"🎉 成功找到您過去的 {len(response.data)} 筆歷史紀錄：")
                for index, record in enumerate(response.data, 1):
                    clean_date = record['created_at'].split('.')[0].replace('T', ' ')
                    score = record['total_score']
                    status = "🔴 中重度/重度" if score >= 15 else ("🟡 中度" if score >= 10 else "🟢 輕微/良好")
                    st.write(f"**第 {index} 次紀錄** | 📅 時間: `{clean_date}` | 📊 總分: **{score} 分** ({status})")
            else:
                st.info("您目前尚無歷史紀錄，請在上方提交您的第一份問卷！")
        except Exception as e:
            st.error(f"撈取資料失敗：{e}")
