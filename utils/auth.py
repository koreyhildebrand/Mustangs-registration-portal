import streamlit as st
import streamlit_authenticator as stauth
from google.oauth2.service_account import Credentials
import gspread
from config import COOKIE_NAME, COOKIE_KEY, COOKIE_EXPIRY_DAYS


def initialize_authenticator() -> stauth.Authenticate:
    """Set up Google Sheets client and Streamlit Authenticator (runs once)."""
    if "authenticator" not in st.session_state:
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets",
                     "https://www.googleapis.com/auth/drive"]
            creds_dict = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            st.session_state.sheet = client.open("RegistrationPortal")

            # Build credentials dict from Users sheet
            users_ws = st.session_state.sheet.worksheet("Users")
            user_data = users_ws.get_all_records()
            credentials = {"usernames": {}}
            for user in user_data:
                uname = str(user.get("username", "")).strip()
                if uname:
                    credentials["usernames"][uname] = {
                        "name": user.get("name", uname),
                        "email": user.get("email", ""),
                        "password": user.get("password", "changeme123"),
                    }

            authenticator = stauth.Authenticate(
                credentials=credentials,
                cookie_name=COOKIE_NAME,
                key=COOKIE_KEY,
                cookie_expiry_days=COOKIE_EXPIRY_DAYS,
            )
            st.session_state.authenticator = authenticator
        except Exception as e:
            st.error(f"Setup error: {str(e)}")
            st.stop()

    return st.session_state.authenticator
