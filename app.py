import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit_authenticator as stauth
from utils.sheets import get_worksheet_data
from pages.equipment import show_equipment

# ====================== VERSION CONTROL ======================
VERSION = "v4.02"  # Added Events & Check-In page

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

        # Load users
        users_ws = sheet.worksheet("Users")
        user_data = users_ws.get_all_records()
        credentials = {"usernames": {}}
        for user in user_data:
            uname = str(user.get("username", "")).strip()
            if uname:
                credentials["usernames"][uname] = {
                    "name": user.get("name", uname),
                    "email": user.get("email", ""),
                    "password": user.get("password", "")
                }

        authenticator = stauth.Authenticate(
            credentials,
            cookie_name="mustangs_registration",
            cookie_key=st.secrets["cookie"]["key"],
            cookie_expiry_days=30,
        )
        st.session_state.authenticator = authenticator
    except Exception as e:
        st.error(f"Failed to load authentication: {e}")
        st.stop()

authenticator = st.session_state.authenticator
name, authentication_status, username = authenticator.login(location='main')

if authentication_status:
    st.sidebar.success(f"Welcome, {name}!")
    
    # ====================== LOAD MAIN DATA ======================
    players_df = get_worksheet_data("Players")
    teams_df   = get_worksheet_data("Teams")

    # ====================== SIDEBAR NAVIGATION ======================
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Equipment Management", "Events & Check-In", "Registrar Dashboard", "Coach Portal", 
         "Football Operations", "Admin", "Profile"],
        key="main_page"
    )

    # ====================== PAGE ROUTING ======================
    if page == "Equipment Management":
        show_equipment(players_df, teams_df, st.session_state.sheet)
    
    elif page == "Events & Check-In":
        from pages.events import show_events
        show_events(st.session_state.sheet)
    
    elif page == "Registrar Dashboard":
        st.info("👷 Registrar Dashboard – Under development")
    
    elif page == "Coach Portal":
        st.info("👷 Coach Portal – Under development")
    
    elif page == "Football Operations":
        st.info("👷 Football Operations – Under development")
    
    elif page == "Admin":
        st.info("👷 Admin Panel – Under development")
    
    elif page == "Profile":
        authenticator.logout(location='sidebar')
        st.write("Profile settings coming soon...")

    st.sidebar.caption(f"✅ Version {VERSION}")

elif authentication_status is False:
    st.error("❌ Invalid username or password")
elif authentication_status is None:
    st.warning("Please enter your username and password")

st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")
