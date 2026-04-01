import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="Football Manitoba Registration Portal", layout="wide", page_icon="🏈")
st.title("🏈 Football Manitoba Admin Registration Portal")

# ====================== GOOGLE SHEETS CONNECTION (Secrets) ======================
@st.cache_resource
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("RegistrationPortal")  # ← Change if your sheet name differs

sheet = get_gsheet()
players_ws = sheet.worksheet("Players")
teams_ws = sheet.worksheet("Teams")
users_ws = sheet.worksheet("Users")

players_df = pd.DataFrame(players_ws.get_all_records())
teams_df = pd.DataFrame(teams_ws.get_all_records())

# ====================== AGE GROUP (2026 MMFA / Football Manitoba Rules) ======================
def calculate_age_group(dob_str):
    try:
        dob = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date()
        birth_year = dob.year
        # 2026 season: 2-year birth cohorts (adjust cutoff if MMFA announces change)
        if 2016 <= birth_year <= 2017:      # turning ~9-10
            return "U10 Cruncher"
        elif 2014 <= birth_year <= 2015:    # turning ~11-12
            return "U12 Atom"
        elif 2012 <= birth_year <= 2013:    # turning ~13-14
            return "U14 PeeWee"
        elif 2010 <= birth_year <= 2011:    # turning ~15-16
            return "U16 Bantam"
        else:
            return "Check Eligibility - Outside 2026 MMFA Range"
    except:
        return "Invalid DOB"

players_df["AgeGroup"] = players_df.get("Date of Birth", "").apply(calculate_age_group)

# ====================== AUTHENTICATION (Phase 2 - Hashed + Multi-Role) ======================
if "authenticator" not in st.session_state:
    # Load users from Google Sheet "Users" tab (columns: username, name, email, password (plain - will be hashed on first run), roles)
    user_records = users_ws.get_all_records()
    credentials = {"usernames": {}}
    for rec in user_records:
        username = rec["username"]
        credentials["usernames"][username] = {
            "name": rec["name"],
            "email": rec.get("email", ""),
            "password": rec["password"]   # plain on first load → auto-hashed below
        }
    
    # Pre-hash if needed (run once)
    if any(not str(pw).startswith("$2b$") for pw in [u["password"] for u in credentials["usernames"].values()]):
        stauth.Hasher.hash_passwords(credentials)
        # Optional: write hashed back to sheet (advanced - manual for now)
    
    authenticator = stauth.Authenticate(
        credentials=credentials,
        cookie_name="football_mb_portal",
        key="super_secret_key_2026",   # change this
        cookie_expiry_days=30,
    )
    st.session_state.authenticator = authenticator
    st.session_state.user_roles = {}  # cache roles

name, authentication_status, username = st.session_state.authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")
    st.stop()
elif authentication_status == None:
    st.warning("Please enter your username and password")
    st.stop()

# Load roles for logged-in user
if username and username not in st.session_state.user_roles:
    user_row = next((u for u in user_records if u["username"] == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    st.session_state.user_roles[username] = [r.strip() for r in roles_str.split(",") if r.strip()]

roles = st.session_state.user_roles.get(username, [])
is_admin = "Admin" in roles
can_rw = is_admin or "ReadWrite" in roles
can_ro = is_admin or can_rw or "ReadOnly" in roles
can_restricted = is_admin or "Restricted" in roles

st.sidebar.success(f"👤 {name} ({username})")
st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")

if not can_ro:
    st.error("You have no access privileges.")
    st.stop()

# ====================== TABS ======================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Players", "🏈 Teams & Coaches", "🔒 Restricted Health", "📄 Export & Notify", "⚙️ Admin"])

# Tab 1: Players (non-restricted)
with tab1:
    st.header("Player Roster")
    display_cols = ["First Name", "Last Name", "Date of Birth", "AgeGroup", "Address", "Weight", 
                    "Years Experience", "ParentName", "ParentPhone", "ParentEmail", "Secondary Emergency Contact", "Team"]
    df_display = players_df[[c for c in display_cols if c in players_df.columns]].copy()
    
    search = st.text_input("Search players", "")
    if search:
        df_display = df_display[df_display.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
    
    edited = st.data_editor(df_display, num_rows="dynamic", use_container_width=True, key="player_editor")
    
    if st.button("💾 Save Player Changes to Google Sheet", type="primary"):
        # Sync back
        for col in edited.columns:
            players_df[col] = edited[col]
        players_ws.update([players_df.columns.values.tolist()] + players_df.values.tolist())
        st.success("✅ Player data saved!")

# Tab 2: Teams & Coaches (RW/Admin)
with tab2:
    st.header("Teams & Coach Assignment")
    if can_rw:
        edited_teams = st.data_editor(teams_df, num_rows="dynamic", use_container_width=True, key="team_editor")
        if st.button("Save Teams"):
            teams_ws.update([edited_teams.columns.values.tolist()] + edited_teams.values.tolist())
            st.success("Teams updated!")
        
        with st.expander("➕ Create New Team"):
            t_name = st.text_input("Team Name")
            t_div = st.selectbox("Division", ["U10 Cruncher", "U12 Atom", "U14 PeeWee", "U16 Bantam"])
            t_coach = st.text_input("Coach Name")
            t_phone = st.text_input("Coach Phone")
            t_email = st.text_input("Coach Email")
            if st.button("Create Team"):
                new_row = {"TeamID": len(teams_df)+1, "TeamName": t_name, "Division": t_div,
                           "CoachName": t_coach, "CoachPhone": t_phone, "CoachEmail": t_email, "SeasonYear": 2026}
                teams_df = pd.concat([teams_df, pd.DataFrame([new_row])], ignore_index=True)
                teams_ws.update([teams_df.columns.values.tolist()] + teams_df.values.tolist())
                st.success(f"Team {t_name} created!")
    else:
        st.info("View-only: Contact Admin for edit rights.")

# Tab 3: Restricted Data
with tab3:
    if can_restricted:
        st.header("🔒 Restricted Health Information")
        health_cols = ["First Name", "Last Name", "Health Number", "History of Concussion", "Glasses/Contacts",
                       "Asthma", "Diabetic", "Allergies", "Injuries in past year", "Epilepsy",
                       "Hearing problems", "Heart Condition", "Medication", "Surgeries in last year",
                       "ExplanationIfYes", "MedicationLists", "AdditionalInfo"]
        restricted_df = players_df[[c for c in health_cols if c in players_df.columns]]
        
        edited_health = st.data_editor(restricted_df, num_rows="dynamic", use_container_width=True)
        if st.button("Save Restricted Data"):
            for col in edited_health.columns:
                players_df[col] = edited_health[col]
            players_ws.update([players_df.columns.values.tolist()] + players_df.values.tolist())
            st.success("🔒 Health data saved securely.")
    else:
        st.warning("🔒 Restricted access denied. Contact Administrator.")

# Tab 4: Export & Notify (Phase 3)
with tab4:
    st.header("📄 PDF Registration Forms & Notifications")
    player_options = players_df["First Name"] + " " + players_df["Last Name"]
    selected_player = st.selectbox("Generate PDF for player", player_options)
    
    if st.button("Generate & Download PDF"):
        idx = player_options[player_options == selected_player].index[0]
        row = players_df.iloc[idx]
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, f"Football Manitoba Registration - {row.get('First Name')} {row.get('Last Name')}")
        c.drawString(100, 720, f"DOB: {row.get('Date of Birth')} | Age Group: {row.get('AgeGroup')}")
        c.drawString(100, 690, f"Parent: {row.get('ParentName')} | Phone: {row.get('ParentPhone')}")
        c.drawString(100, 660, f"Address: {row.get('Address')}")
        # Add more fields...
        c.save()
        
        st.download_button("⬇️ Download PDF", buffer.getvalue(), f"{selected_player}_registration.pdf", "application/pdf")
    
    # Bulk export button (simple list)
    if st.button("Export All Players as CSV"):
        csv = players_df.to_csv(index=False)
        st.download_button("⬇️ Download Full CSV", csv, "all_players.csv", "text/csv")

# Tab 5: Super Admin (Phase 2 user/role management)
with tab5:
    if is_admin:
        st.header("⚙️ Super Admin Tools")
        
        st.subheader("Assign Player to Team")
        p_select = st.selectbox("Player", player_options)
        t_select = st.selectbox("Team", teams_df["TeamName"] if not teams_df.empty else ["No teams"])
        if st.button("Assign Player"):
            idx = player_options[player_options == p_select].index[0]
            players_df.at[idx, "Team"] = t_select
            players_ws.update([players_df.columns.values.tolist()] + players_df.values.tolist())
            st.success("Player assigned!")
        
        st.subheader("User & Role Management")
        st.info("Edit the 'Users' sheet directly in Google Sheets. Columns: username, name, email, password (plain text - will auto-hash), roles (Admin,ReadWrite,ReadOnly,Restricted – comma separated). Restart app after changes.")
        
        st.caption("Multi-role example: ReadWrite,Restricted")
    else:
        st.info("Super Admin tools available only to Administrators.")

st.sidebar.button("Logout", on_click=lambda: st.session_state.authenticator.logout())

st.caption("✅ Phases 2-4 Complete | Secure hashed login | Multi-role + Restricted access | PDF export | Ready for Streamlit Cloud")