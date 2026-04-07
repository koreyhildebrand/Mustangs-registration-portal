import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

# ====================== LOAD GOOGLE SHEETS ======================
@st.cache_resource
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("RegistrationPortal")

sheet = get_gsheet()

def ensure_worksheet(name, headers):
    try:
        return sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=name, rows=200, cols=40)
        ws.append_row(headers)
        return ws

players_ws = ensure_worksheet("Players", ["First Name","Last Name","Date of Birth","Address","Weight","Years Experience","ParentName","ParentPhone","ParentEmail","Secondary Emergency Contact Name","Secondary Emergency Contact Phone","Secondary Emergency Contact Email","Team","AgeGroup","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo","RegisteredCamps"])
teams_ws = ensure_worksheet("Teams", ["TeamID","TeamName","Division","CoachName","CoachPhone","CoachEmail","SeasonYear"])
users_ws = ensure_worksheet("Users", ["username","name","email","password","roles","permissions"])
camps_ws = ensure_worksheet("Camps", ["CampID","CampName","Date","Location","Description","MaxPlayers"])

players_df = pd.DataFrame(players_ws.get_all_records())
teams_df = pd.DataFrame(teams_ws.get_all_records())
camps_df = pd.DataFrame(camps_ws.get_all_records())

# Age Groups
def calculate_age_group(dob_str):
    try:
        dob = datetime.datetime.strptime(str(dob_str).strip(), "%Y-%m-%d").date()
        y = dob.year
        if 2016 <= y <= 2017: return "U10 Cruncher"
        elif 2014 <= y <= 2015: return "U12 Atom"
        elif 2012 <= y <= 2013: return "U14 PeeWee"
        elif 2010 <= y <= 2011: return "U16 Bantam"
        return "Outside 2026 Eligibility"
    except:
        return "Invalid DOB"

if "Date of Birth" in players_df.columns:
    players_df["AgeGroup"] = players_df["Date of Birth"].apply(calculate_age_group)

# ====================== AUTH & ROLES ======================
user_records = pd.DataFrame(users_ws.get_all_records()).to_dict("records")
user_row = next((u for u in user_records if u.get("username") == username), None)
roles_str = user_row.get("roles", "") if user_row else ""
permissions_str = user_row.get("permissions", "") if user_row else ""

roles = [r.strip() for r in roles_str.split(",") if r.strip()]
is_admin = "Admin" in roles
can_rw = is_admin or "ReadWrite" in roles
can_ro = is_admin or can_rw or "ReadOnly" in roles
can_restricted = is_admin or "Restricted" in roles

# Parse permissions
permissions = {}
for item in permissions_str.split(","):
    if ":" in item:
        tab, level = [x.strip() for x in item.split(":", 1)]
        permissions[tab] = level

# Default permissions
if not permissions:
    permissions = {"Players": "View", "Registrar": "View", "Restricted": "No", "Export": "View", "Camps": "View", "Coaches": "View"}

st.sidebar.success(f"👤 {name}")
st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")

# Dynamic Navigation (hide tabs with "No" permission)
nav_options = []
if permissions.get("Players", "No") != "No": nav_options.append("📋 Players")
if permissions.get("Registrar", "No") != "No": nav_options.append("📋 Registrar")
if permissions.get("Restricted", "No") != "No": nav_options.append("🔒 Restricted Health")
if permissions.get("Export", "No") != "No": nav_options.append("📄 Export")
if permissions.get("Camps", "No") != "No": nav_options.append("🏕️ Camps")
if is_admin: nav_options.append("🔧 Admin")
nav_options.append("👤 Profile")   # Always visible

page = st.sidebar.radio("Navigation", nav_options, key="sidebar_nav")

if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticator.logout('main')
    st.rerun()

# ====================== PAGES ======================
if page == "📋 Players" and permissions.get("Players", "No") != "No":
    st.header("Player Roster")
    # (team filter code as before)
    team_options = ["All Players"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Players"]
    selected_team = st.selectbox("Filter by Team", team_options, key="team_filter")
    # ... rest of players page (same as previous working version)

elif page == "📋 Registrar" and permissions.get("Registrar", "No") != "No":
    st.header("📋 Registrar Dashboard")
    # (your preferred registrar page content)

elif page == "🔒 Restricted Health" and permissions.get("Restricted", "No") != "No":
    if can_restricted:
        st.header("🔒 Restricted Health Data")
        # ... restricted health code

elif page == "📄 Export" and permissions.get("Export", "No") != "No":
    st.header("📄 Export")
    # ... export code

elif page == "🏕️ Camps" and permissions.get("Camps", "No") != "No":
    st.header("🏕️ Camps & Training Sessions")
    # ... camps code

elif page == "🔧 Admin" and is_admin:
    st.header("🔧 Admin – User Management")
    st.info("Full permission editor coming soon.\n\nEdit the **Users** sheet directly for now.")

elif page == "👤 Profile":
    st.header("👤 Profile")
    st.subheader("Update Your Information")
    st.info("You can change your password below.")
    if st.session_state.authenticator.update_password(username, location='main'):
        st.success("Password changed successfully!")

st.caption("✅ St. Vital Mustangs Registration Portal | Dynamic Permissions")
