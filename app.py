import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

# ====================== AUTHENTICATION ======================
if "authenticator" not in st.session_state:
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("RegistrationPortal")
        st.session_state.sheet = sheet

        # Build credentials
        users_ws = sheet.worksheet("Users")
        user_data = users_ws.get_all_records()
        credentials = {"usernames": {}}
        for user in user_data:
            uname = str(user.get("username", "")).strip()
            if uname:
                credentials["usernames"][uname] = {
                    "name": user.get("name", uname),
                    "email": user.get("email", ""),
                    "password": user.get("password", "changeme123")
                }

        authenticator = stauth.Authenticate(
            credentials=credentials,
            cookie_name="stvital_mustangs_portal",
            key="super_secret_key_2026_mustangs",
            cookie_expiry_days=30,
        )
        st.session_state.authenticator = authenticator
    except Exception as e:
        st.error(f"Setup error: {str(e)}")
        st.stop()

st.session_state.authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    sheet = st.session_state.sheet

    @st.cache_data(ttl=300)  # Cache for 5 minutes to reduce reads
    def get_worksheet_data(ws_name):
        try:
            ws = sheet.worksheet(ws_name)
            return pd.DataFrame(ws.get_all_records())
        except Exception as e:
            if "429" in str(e):
                st.warning(f"Quota limit reached for {ws_name}. Waiting 15 seconds...")
                time.sleep(15)
                ws = sheet.worksheet(ws_name)
                return pd.DataFrame(ws.get_all_records())
            else:
                st.error(f"Error loading {ws_name}: {str(e)}")
                return pd.DataFrame()

    # Load data with caching
    players_df = get_worksheet_data("Players")
    teams_df = get_worksheet_data("Teams")
    camps_df = get_worksheet_data("Camps")
    camp_reg_df = get_worksheet_data("CampRegistrations")

    # Dynamic Age Group
    def calculate_age_group(dob_str, season_year):
        try:
            dob = datetime.datetime.strptime(str(dob_str).strip(), "%Y-%m-%d").date()
            age = season_year - dob.year
            if 9 <= age <= 10: return "U10 Cruncher"
            elif 11 <= age <= 12: return "U12 Atom"
            elif 13 <= age <= 14: return "U14 PeeWee"
            elif 15 <= age <= 16: return "U16 Bantam"
            return f"Outside {season_year} Eligibility"
        except:
            return "Invalid DOB"

    if "Date of Birth" in players_df.columns:
        players_df["AgeGroup"] = players_df["Date of Birth"].apply(lambda x: calculate_age_group(x, datetime.date.today().year))

    # User roles
    user_records = pd.DataFrame(sheet.worksheet("Users").get_all_records()).to_dict("records")
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    can_rw = is_admin or "ReadWrite" in roles
    can_ro = is_admin or can_rw or "ReadOnly" in roles
    can_restricted = is_admin or "Restricted" in roles

    st.sidebar.success(f"👤 {name}")
    st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")

    nav_options = ["📋 Players", "📋 Registrar"]
    if can_restricted: nav_options.append("🔒 Restricted Health")
    nav_options.append("🏕️ Camps")
    if is_admin: nav_options.append("🔧 Admin")
    nav_options.append("👤 Profile")

    page = st.sidebar.radio("Navigation", nav_options, key="sidebar_nav")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticator.logout('main')
        st.rerun()

    # Registrar page - Teams editing
    if page == "📋 Registrar":
        st.header("📋 Registrar Dashboard")
        selected_year = st.selectbox("Select Season Year", [2024, 2025, 2026, 2027], index=2)

        st.subheader("Teams & Coaches Management")
        if can_rw:
            edited_teams = st.data_editor(teams_df, num_rows="dynamic", use_container_width=True, key="team_editor")
            if st.button("💾 Save Teams Changes"):
                try:
                    teams_ws = sheet.worksheet("Teams")
                    teams_ws.update([edited_teams.columns.values.tolist()] + edited_teams.fillna("").values.tolist())
                    st.success("✅ Teams saved!")
                    st.cache_data.clear()  # Clear cache so next load gets fresh data
                except Exception as e:
                    if "429" in str(e):
                        st.error("Quota limit reached. Please wait 60 seconds and try saving again.")
                    else:
                        st.error(f"Save failed: {str(e)}")

    st.caption("✅ St. Vital Mustangs Registration Portal - Quota Optimized")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
