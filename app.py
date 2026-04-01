import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="Football Manitoba Registration Portal", layout="wide", page_icon="🏈")
st.title("🏈 Football Manitoba Admin Registration Portal")

# ====================== GOOGLE SHEETS + AUTO TABS ======================
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
        return sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        st.info(f"Creating tab: {name}")
        ws = sheet.add_worksheet(title=name, rows=200, cols=30)
        ws.append_row(headers)
        return ws

players_ws = ensure_worksheet("Players", ["First Name","Last Name","Date of Birth","Address","Weight","Years Experience","ParentName","ParentPhone","ParentEmail","Secondary Emergency Contact Name","Secondary Emergency Contact Phone","Secondary Emergency Contact Email","Team","AgeGroup","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo","RegisteredCamps"])
teams_ws = ensure_worksheet("Teams", ["TeamID","TeamName","Division","CoachName","CoachPhone","CoachEmail","SeasonYear"])
users_ws = ensure_worksheet("Users", ["username","name","email","password","roles"])
camps_ws = ensure_worksheet("Camps", ["CampID","CampName","Date","Location","Description","MaxPlayers"])

players_df = pd.DataFrame(players_ws.get_all_records())
teams_df = pd.DataFrame(teams_ws.get_all_records())
camps_df = pd.DataFrame(camps_ws.get_all_records())

# ====================== 2026 AGE GROUPS ======================
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
    authenticator = stauth.Authenticate(
        credentials={"usernames": {rec["username"]: {"name": rec["name"], "email": rec.get("email",""), "password": rec.get("password","changeme123")} for rec in pd.DataFrame(users_ws.get_all_records()).to_dict("records") if rec.get("username")}},
        cookie_name="football_mb_portal",
        key="super_secret_key_2026_mb",
        cookie_expiry_days=30,
    )
    st.session_state.authenticator = authenticator

st.session_state.authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    # Load roles
    user_row = next((u for u in pd.DataFrame(users_ws.get_all_records()).to_dict("records") if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 Players", "🏈 Teams & Coaches", "🔒 Restricted Health", "📄 Export", "⚙️ Admin", "🏕️ Team Management & Camps"])

    with tab1:  # (unchanged - kept for brevity)
        st.header("Player Roster")
        display_cols = ["First Name", "Last Name", "Date of Birth", "AgeGroup", "Address", "Weight", "Years Experience", "ParentName", "ParentPhone", "ParentEmail", "Secondary Emergency Contact Name", "Team", "RegisteredCamps"]
        df_display = players_df[[c for c in display_cols if c in players_df.columns]].copy()
        search = st.text_input("🔍 Search players", "")
        if search:
            df_display = df_display[df_display.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        edited = st.data_editor(df_display, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Player Changes", type="primary"):
            for col in edited.columns:
                players_df[col] = edited[col]
            players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
            st.success("✅ Saved!")

    with tab2:
        st.header("Teams & Coaches")
        if can_rw:
            edited_teams = st.data_editor(teams_df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Save Teams"):
                teams_ws.update([edited_teams.columns.values.tolist()] + edited_teams.fillna("").values.tolist())
                st.success("Saved!")
            with st.expander("➕ Create New Team"):
                t_name = st.text_input("Team Name")
                t_div = st.selectbox("Division", ["U10 Cruncher", "U12 Atom", "U14 PeeWee", "U16 Bantam"])
                t_coach = st.text_input("Coach Name")
                if st.button("Create Team"):
                    new_row = {"TeamID": len(teams_df)+1, "TeamName": t_name, "Division": t_div, "CoachName": t_coach, "CoachPhone": "", "CoachEmail": "", "SeasonYear": 2026}
                    teams_df = pd.concat([teams_df, pd.DataFrame([new_row])], ignore_index=True)
                    teams_ws.update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())
                    st.success(f"Team {t_name} created!")
        else:
            st.info("View-only mode.")

    with tab3:  # (restricted health - unchanged)
        if can_restricted:
            st.header("🔒 Restricted Health Data")
            health_cols = ["First Name","Last Name","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo"]
            avail = [c for c in health_cols if c in players_df.columns]
            edited_h = st.data_editor(players_df[avail], num_rows="dynamic", use_container_width=True)
            if st.button("💾 Save Restricted Data"):
                for c in edited_h.columns:
                    players_df[c] = edited_h[c]
                players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                st.success("🔒 Saved securely!")
        else:
            st.warning("🔒 Restricted access denied.")

    with tab4:  # (export - unchanged)
        st.header("📄 Export")
        player_list = (players_df["First Name"].astype(str) + " " + players_df["Last Name"].astype(str)).tolist()
        sel = st.selectbox("Generate PDF for", player_list) if player_list else None
        if sel and st.button("Generate PDF"):
            idx = player_list.index(sel)
            row = players_df.iloc[idx]
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            c.drawString(100, 750, "Football Manitoba Registration 2026")
            c.drawString(100, 720, f"{row.get('First Name','')} {row.get('Last Name','')} - {row.get('AgeGroup','')}")
            c.drawString(100, 690, f"Parent: {row.get('ParentName','')} | Phone: {row.get('ParentPhone','')}")
            c.drawString(100, 660, f"Team: {row.get('Team','')} | Camps: {row.get('RegisteredCamps','')}")
            c.save()
            st.download_button("⬇️ Download PDF", buffer.getvalue(), f"{sel.replace(' ','_')}.pdf", "application/pdf")
        if st.button("Export All as CSV"):
            st.download_button("⬇️ Download CSV", players_df.to_csv(index=False), "players_2026.csv", "text/csv")

    with tab5:  # (admin - unchanged)
        if is_admin:
            st.header("⚙️ Super Admin")
            p_sel = st.selectbox("Player", player_list) if player_list else None
            t_sel = st.selectbox("Team", teams_df["TeamName"].tolist() if not teams_df.empty else ["No teams"])
            if st.button("Assign Player to Team"):
                idx = player_list.index(p_sel)
                players_df.at[idx, "Team"] = t_sel
                players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                st.success("Assigned!")
            st.info("Edit Users sheet for new users/roles.")
        else:
            st.info("Admin tools only.")

    # ====================== NEW: TEAM MANAGEMENT & CAMPS ======================
    with tab6:
        st.header("🏕️ Team Management & Camps")

        subtab1, subtab2 = st.tabs(["Team View", "Create / Register Camps"])

        with subtab1:  # Team Management View
            st.subheader("Select a Team")
            if not teams_df.empty:
                selected_team = st.selectbox("Team", teams_df["TeamName"])
                team_players = players_df[players_df["Team"] == selected_team].copy()
                if not team_players.empty:
                    st.dataframe(team_players[["First Name", "Last Name", "AgeGroup", "RegisteredCamps"]], use_container_width=True)
                else:
                    st.info("No players assigned to this team yet.")
            else:
                st.info("No teams created yet.")

        with subtab2:  # Camps
            if is_admin or can_rw:
                st.subheader("Create New Training Session / Camp")
                c_name = st.text_input("Camp Name (e.g. Skills Camp Day 1)")
                c_date = st.date_input("Date")
                c_location = st.text_input("Location")
                c_desc = st.text_area("Description")
                c_max = st.number_input("Max Players", min_value=1, value=40)
                if st.button("Create Camp"):
                    new_camp = {"CampID": len(camps_df)+1, "CampName": c_name, "Date": str(c_date), "Location": c_location, "Description": c_desc, "MaxPlayers": c_max}
                    camps_df = pd.concat([camps_df, pd.DataFrame([new_camp])], ignore_index=True)
                    camps_ws.update([camps_df.columns.values.tolist()] + camps_df.fillna("").values.tolist())
                    st.success(f"✅ Camp '{c_name}' created!")

                st.subheader("Register Players to a Camp")
                if not camps_df.empty:
                    selected_camp = st.selectbox("Select Camp", camps_df["CampName"])
                    all_players = players_df["First Name"].astype(str) + " " + players_df["Last Name"].astype(str)
                    selected_players = st.multiselect("Players to register", all_players.tolist())
                    if st.button("Register Selected Players to Camp"):
                        for p in selected_players:
                            idx = players_df[(players_df["First Name"] + " " + players_df["Last Name"]) == p].index[0]
                            current = players_df.at[idx, "RegisteredCamps"]
                            if pd.isna(current) or current == "":
                                players_df.at[idx, "RegisteredCamps"] = selected_camp
                            else:
                                players_df.at[idx, "RegisteredCamps"] = f"{current}, {selected_camp}"
                        players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                        st.success(f"✅ {len(selected_players)} player(s) registered to {selected_camp}")
                else:
                    st.info("Create a camp first.")

            else:
                st.info("You need Read-Write or Admin rights to manage camps.")

    st.sidebar.button("Logout", on_click=lambda: st.session_state.authenticator.logout('main'))

elif authentication_status is False:
    st.error("❌ Username or password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")

st.caption("✅ Phase 5: Team Management + Camps/Training Sessions added | Multi-role | Google Sheet connected")