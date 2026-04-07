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

# ====================== AUTHENTICATION FIRST ======================
if "authenticator" not in st.session_state:
    try:
        sheet = None  # Will be initialized later
        # Temporary placeholder - will be replaced after login
        authenticator = stauth.Authenticate(
            credentials={"usernames": {}},
            cookie_name="stvital_mustangs_portal",
            key="super_secret_key_2026_mustangs",
            cookie_expiry_days=30,
        )
        st.session_state.authenticator = authenticator
    except:
        pass

st.session_state.authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    # ====================== LOAD GOOGLE SHEETS ONLY AFTER LOGIN ======================
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

    # Age Group Calculation
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

    # Load user roles
    user_row = next((u for u in pd.DataFrame(users_ws.get_all_records()).to_dict("records") if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    can_rw = is_admin or "ReadWrite" in roles
    can_ro = is_admin or can_rw or "ReadOnly" in roles
    can_restricted = is_admin or "Restricted" in roles

    st.sidebar.success(f"👤 {name}")
    st.sidebar.write("**Roles:**", ", ".join(roles))

    # Sidebar Navigation
    nav_options = ["📋 Players", "📋 Registrar"]
    if can_restricted: nav_options.append("🔒 Restricted Health")
    nav_options.append("📄 Export")
    nav_options.append("🏕️ Camps")
    if is_admin: nav_options.append("🔧 Admin")
    nav_options.append("👤 Profile")

    page = st.sidebar.radio("Navigation", nav_options, key="sidebar_nav")

    if st.sidebar.button("Logout"):
        st.session_state.authenticator.logout('main')
        st.rerun()

    # ====================== PAGE CONTENT ======================
    if page == "📋 Players":
        st.header("Player Roster")
        team_options = ["All Players"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Players"]
        selected_team = st.selectbox("Filter by Team", team_options, key="team_filter")

        if selected_team == "All Players":
            df_display = players_df.copy()
        else:
            df_display = players_df[players_df["Team"] == selected_team].copy()

        display_cols = ["First Name", "Last Name", "Date of Birth", "AgeGroup", "Address", "Weight", "Years Experience", 
                        "ParentName", "ParentPhone", "ParentEmail", "Secondary Emergency Contact Name", "Team", "RegisteredCamps"]
        available_cols = [c for c in display_cols if c in df_display.columns]
        df_display = df_display[available_cols]

        search = st.text_input("🔍 Search players", key="player_search")
        if search:
            df_display = df_display[df_display.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        edited = st.data_editor(df_display, num_rows="dynamic", use_container_width=True, key="player_editor")
        if st.button("💾 Save Player Changes", type="primary"):
            for col in edited.columns:
                players_df[col] = edited[col]
            players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
            st.success("✅ Saved!")

    elif page == "📋 Registrar":
        st.header("📋 Registrar Dashboard")
        current_year = datetime.date.today().year
        selected_year = st.selectbox("Select Season Year", [2024, 2025, 2026, 2027], index=2)

        st.subheader(f"Registered Players – {selected_year} Season")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: st.metric("Total Players", len(players_df))
        with col2: st.metric("U10 Cruncher", len(players_df[players_df.get("AgeGroup", "") == "U10 Cruncher"]))
        with col3: st.metric("U12 Atom", len(players_df[players_df.get("AgeGroup", "") == "U12 Atom"]))
        with col4: st.metric("U14 PeeWee", len(players_df[players_df.get("AgeGroup", "") == "U14 PeeWee"]))
        with col5: st.metric("U16 Bantam", len(players_df[players_df.get("AgeGroup", "") == "U16 Bantam"]))

        st.subheader("Teams & Coaches Management")
        if can_rw:
            edited_teams = st.data_editor(teams_df, num_rows="dynamic", use_container_width=True, key="team_editor")
            if st.button("💾 Save Teams"):
                teams_ws.update([edited_teams.columns.values.tolist()] + edited_teams.fillna("").values.tolist())
                st.success("Teams saved!")

    # ... (other pages like Restricted, Export, Camps, Admin, Profile remain the same as previous version)

    st.caption("✅ St. Vital Mustangs Registration Portal | Fixed Logout")

else:
    if authentication_status is False:
        st.error("❌ Username or password is incorrect")
    else:
        st.warning("Please enter your username and password")