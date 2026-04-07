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

# ====================== GOOGLE SHEETS ======================
@st.cache_resource
def get_gsheet():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("RegistrationPortal")
    except Exception as e:
        st.error(f"❌ Sheet connection failed: {str(e)}")
        st.stop()

sheet = get_gsheet()

def ensure_worksheet(name, headers):
    try:
        ws = sheet.worksheet(name)
        existing = ws.row_values(1)
        missing = [h for h in headers if h not in existing]
        if missing:
            ws.append_row(existing + missing)
        return ws
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=name, rows=200, cols=40)
        ws.append_row(headers)
        return ws

players_ws = ensure_worksheet("Players", ["First Name","Last Name","Date of Birth","Address","Weight","Years Experience","ParentName","ParentPhone","ParentEmail","Secondary Emergency Contact Name","Secondary Emergency Contact Phone","Secondary Emergency Contact Email","Team","AgeGroup","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo","RegisteredCamps"])
teams_ws = ensure_worksheet("Teams", ["TeamID","TeamName","Division","CoachName","CoachPhone","CoachEmail","SeasonYear"])
users_ws = ensure_worksheet("Users", ["username","name","email","password","roles"])
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

# ====================== AUTHENTICATION ======================
if "authenticator" not in st.session_state:
    user_records = pd.DataFrame(users_ws.get_all_records()).to_dict("records")
    credentials = {"usernames": {}}
    for rec in user_records:
        uname = rec.get("username", "").strip()
        if uname:
            credentials["usernames"][uname] = {
                "name": rec.get("name", uname),
                "email": rec.get("email", ""),
                "password": rec.get("password", "changeme123")
            }

    authenticator = stauth.Authenticate(
        credentials=credentials,
        cookie_name="stvital_mustangs_portal",
        key="super_secret_key_2026_mustangs",
        cookie_expiry_days=30,
    )
    st.session_state.authenticator = authenticator

st.session_state.authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    user_row = next((u for u in pd.DataFrame(users_ws.get_all_records()).to_dict("records") if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    can_rw = is_admin or "ReadWrite" in roles
    can_ro = is_admin or can_rw or "ReadOnly" in roles
    can_restricted = is_admin or "Restricted" in roles

    # ====================== SIDEBAR ======================
    st.sidebar.success(f"👤 {name}")
    st.sidebar.write("**Roles:**", ", ".join(roles))

    # Navigation
    page = st.sidebar.radio("Navigation", 
        ["📋 Players", "📋 Registrar", "🔒 Restricted Health", "📄 Export", "👔 Coaches", "🏕️ Camps", "👤 Profile"], 
        key="sidebar_nav")

    if st.sidebar.button("Logout"):
        st.session_state.authenticator.logout('main')
        st.rerun()

    # ====================== PAGES ======================
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
        with col2: st.metric("U10 Cruncher", len(players_df[players_df.get("AgeGroup", pd.Series([""])) == "U10 Cruncher"]))
        with col3: st.metric("U12 Atom", len(players_df[players_df.get("AgeGroup", pd.Series([""])) == "U12 Atom"]))
        with col4: st.metric("U14 PeeWee", len(players_df[players_df.get("AgeGroup", pd.Series([""])) == "U14 PeeWee"]))
        with col5: st.metric("U16 Bantam", len(players_df[players_df.get("AgeGroup", pd.Series([""])) == "U16 Bantam"]))

        st.subheader("Teams & Coaches Management")
        if can_rw:
            edited_teams = st.data_editor(teams_df, num_rows="dynamic", use_container_width=True, key="team_editor")
            if st.button("💾 Save Teams"):
                teams_ws.update([edited_teams.columns.values.tolist()] + edited_teams.fillna("").values.tolist())
                st.success("Teams saved!")

    elif page == "🔒 Restricted Health":
        if can_restricted:
            st.header("🔒 Restricted Health Data")
            health_cols = ["First Name","Last Name","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo"]
            avail = [c for c in health_cols if c in players_df.columns]
            edited_h = st.data_editor(players_df[avail], num_rows="dynamic", use_container_width=True, key="health_editor")
            if st.button("💾 Save Restricted Data"):
                for c in edited_h.columns:
                    players_df[c] = edited_h[c]
                players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                st.success("🔒 Saved securely!")
        else:
            st.warning("🔒 You do not have access to restricted health data.")

    elif page == "📄 Export":
        st.header("📄 Export")
        player_list = (players_df["First Name"].astype(str) + " " + players_df["Last Name"].astype(str)).tolist()
        sel = st.selectbox("Generate PDF for", player_list) if player_list else None
        if sel and st.button("Generate PDF"):
            idx = player_list.index(sel)
            row = players_df.iloc[idx]
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            c.drawString(100, 750, "St. Vital Mustangs Registration 2026")
            c.drawString(100, 720, f"{row.get('First Name','')} {row.get('Last Name','')} - {row.get('AgeGroup','')}")
            c.drawString(100, 690, f"Parent: {row.get('ParentName','')} | Phone: {row.get('ParentPhone','')}")
            c.drawString(100, 660, f"Team: {row.get('Team','')}")
            c.save()
            st.download_button("⬇️ Download PDF", buffer.getvalue(), f"{sel.replace(' ','_')}.pdf", "application/pdf")

    elif page == "👔 Coaches":
        st.header("👔 Coaches Dashboard")
        coach_teams = teams_df[teams_df["CoachName"] == name] if name else pd.DataFrame()
        if not coach_teams.empty:
            st.subheader("Your Teams")
            st.dataframe(coach_teams, use_container_width=True)
        else:
            st.info("No teams assigned to you yet.")

        st.subheader("Your Camps")
        # Simple display of camps (can be expanded)
        if not camps_df.empty:
            st.dataframe(camps_df, use_container_width=True)
        else:
            st.info("No camps created yet.")

    elif page == "🏕️ Camps":
        st.header("🏕️ Camps & Training Sessions")
        if can_rw:
            # Create camp form (same as before)
            col1, col2 = st.columns(2)
            with col1:
                c_name = st.text_input("Camp Name")
                c_date = st.date_input("Date")
            with col2:
                c_location = st.text_input("Location")
                c_max = st.number_input("Max Players", min_value=1, value=40)
            c_desc = st.text_area("Description")
            if st.button("Create Camp"):
                new_camp = {"CampID": len(camps_df)+1, "CampName": c_name, "Date": str(c_date), "Location": c_location, "Description": c_desc, "MaxPlayers": c_max}
                camps_df = pd.concat([camps_df, pd.DataFrame([new_camp])], ignore_index=True)
                camps_ws.update([camps_df.columns.values.tolist()] + camps_df.fillna("").values.tolist())
                st.success("Camp created!")

    elif page == "👤 Profile":
        st.header("👤 Profile Settings")
        st.subheader("Change Password")
        if st.session_state.authenticator.update_password(username, location='main'):
            st.success("Password changed successfully!")
            st.rerun()

    st.caption("✅ St. Vital Mustangs Registration Portal | Sidebar Navigation + Profile + Coaches View")

else:
    if authentication_status is False:
        st.error("❌ Username or password is incorrect")
    else:
        st.warning("Please enter your username and password")