import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

# ====================== VERSION CONTROL ======================
VERSION = "v3.4"  # Logo added to login page only (on top of clean v3.3 stable)

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")

# ====================== ST. VITAL MUSTANGS LOGO ======================
LOGO_URL = "https://images.squarespace-cdn.com/content/v1/58a5f4c8be659445700a4bd4/1491935469145-6FTNR6TR5PMMGJ1EWFP2/logo_white_back.jpg?format=1500w"

# ====================== AUTHENTICATION ======================
if "authenticator" not in st.session_state:
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("RegistrationPortal")
        st.session_state.sheet = sheet

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

    @st.cache_data(ttl=300)
    def get_worksheet_data(ws_name, expected_headers=None):
        try:
            ws = sheet.worksheet(ws_name)
            if expected_headers:
                data = ws.get_all_records(expected_headers=expected_headers)
            else:
                data = ws.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                df.columns = pd.Index([f"{col}_{i}" if list(df.columns).count(col) > 1 else col
                                     for i, col in enumerate(df.columns)])
            return df
        except Exception as e:
            if "429" in str(e):
                st.warning(f"Quota limit for {ws_name}. Waiting 10 seconds...")
                time.sleep(10)
                return get_worksheet_data(ws_name, expected_headers)
            st.error(f"Error loading {ws_name}: {str(e)}")
            return pd.DataFrame()

    players_df = get_worksheet_data("Players")
    teams_df = get_worksheet_data("Teams", expected_headers=["TeamName", "Division", "Coach"])
    events_df = get_worksheet_data("Events")
    events_reg_df = get_worksheet_data("EventsRegistration")

    # Ensure Equipment sheet exists
    try:
        equipment_df = get_worksheet_data("Equipment")
    except:
        sheet.add_worksheet(title="Equipment", rows=1000, cols=10)
        equipment_headers = ["PlayerID", "First Name", "Last Name", "Helmet", "Shoulder Pads", "Pants", "Belt", "Pant Pads", "Secured Rental", "Payment Method"]
        sheet.worksheet("Equipment").update([equipment_headers])
        equipment_df = pd.DataFrame(columns=equipment_headers)

    def calculate_age_group(dob_str, season_year):
        try:
            dob = datetime.datetime.strptime(str(dob_str).strip(), "%Y-%m-%d").date()
            age = season_year - dob.year
            if 9 <= age <= 10: return "U10"
            elif 11 <= age <= 12: return "U12"
            elif 13 <= age <= 14: return "U14"
            elif 15 <= age <= 16: return "U16"
            return f"Outside {season_year}"
        except:
            return "Invalid"

    if "Date of Birth" in players_df.columns:
        players_df["AgeGroup"] = players_df["Date of Birth"].apply(lambda x: calculate_age_group(x, datetime.date.today().year))

    # User roles
    user_records = get_worksheet_data("Users").to_dict("records")
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    can_rw = is_admin or "ReadWrite" in roles
    can_ro = is_admin or can_rw or "ReadOnly" in roles
    can_restricted = is_admin or "Restricted" in roles

    # ====================== SIDEBAR ======================
    st.sidebar.success(f"👤 {name}")
    st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")
    st.sidebar.caption(f"**Version:** {VERSION}")

    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        if st.button("👤 Profile", key="profile_btn", use_container_width=True):
            st.session_state.page = "👤 Profile"
    with col2:
        if is_admin and st.button("🔧 Admin", key="admin_btn", use_container_width=True):
            st.session_state.page = "🔧 Admin"

    if st.sidebar.button("🚪 Logout", key="logout_btn", type="secondary"):
        st.session_state.authenticator.logout('main')
        for key in list(st.session_state.keys()):
            if key not in ["authenticator", "sheet"]:
                if key in st.session_state:
                    del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")

    # Main Navigation
    if st.sidebar.button("📋 Players", key="nav_players", use_container_width=True):
        st.session_state.page = "📋 Players"
    if st.sidebar.button("📋 Registrar", key="nav_registrar", use_container_width=True):
        st.session_state.page = "📋 Registrar"
    if st.sidebar.button("🛡️ Equipment", key="nav_equipment", use_container_width=True):
        st.session_state.page = "🛡️ Equipment"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", key="nav_restricted", use_container_width=True):
        st.session_state.page = "🔒 Restricted Health"
    if st.sidebar.button("🏕️ Events", key="nav_events", use_container_width=True):
        st.session_state.page = "🏕️ Events"

    if "page" not in st.session_state:
        st.session_state.page = "📋 Players"

    page = st.session_state.page

    # ====================== PAGES (exactly as in v3.3) ======================
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
        edited = st.data_editor(df_display, num_rows="dynamic", width="stretch", key="player_editor")
        if st.button("💾 Save Player Changes", type="primary"):
            for col in edited.columns:
                players_df[col] = edited[col]
            sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
            st.success("✅ Saved!")

    elif page == "📋 Registrar":
        st.header("📋 Registrar")
        selected_year = st.selectbox("Select Season Year", [2024, 2025, 2026, 2027], index=2, key="global_season_year")
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            if st.button("📊 Dashboard", key="reg_dashboard", use_container_width=True):
                st.session_state.reg_subpage = "Dashboard"
        with sub_col2:
            if st.button("👥 Team Assignments", key="reg_assign", use_container_width=True):
                st.session_state.reg_subpage = "Team Assignments"
        with sub_col3:
            if st.button("📅 Event Creation", key="reg_event", use_container_width=True):
                st.session_state.reg_subpage = "Event Creation"
        if "reg_subpage" not in st.session_state:
            st.session_state.reg_subpage = "Dashboard"
        subpage = st.session_state.reg_subpage
        if subpage == "Dashboard":
            st.subheader(f"Registered Players – {selected_year} Season")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1: st.metric("Total Players", len(players_df))
            with col2: st.metric("U10", len(players_df[players_df.get("AgeGroup", "") == "U10"]))
            with col3: st.metric("U12", len(players_df[players_df.get("AgeGroup", "") == "U12"]))
            with col4: st.metric("U14", len(players_df[players_df.get("AgeGroup", "") == "U14"]))
            with col5: st.metric("U16", len(players_df[players_df.get("AgeGroup", "") == "U16"]))
            st.subheader("Current Team Roster Summary")
            if not teams_df.empty and "TeamName" in teams_df.columns:
                team_summary = players_df.groupby("Team")["First Name"].count().reset_index()
                team_summary.columns = ["TeamName", "Players Assigned"]
                team_summary = team_summary.merge(teams_df[["TeamName", "Division"]], on="TeamName", how="left")
                team_summary = team_summary.fillna({"Division": "Unknown"})
                st.dataframe(team_summary[["TeamName", "Division", "Players Assigned"]], width="stretch", hide_index=True)
            else:
                st.info("No teams created yet.")
        # ... (the rest of Registrar, Equipment, Restricted Health, Events, Admin, Profile pages are identical to v3.3 – full code continues exactly as you provided)

    # (For brevity in this message, the rest of the pages are unchanged from your v3.3 stable script. Paste the full pages section from your last message after the if page == "📋 Registrar": block, up to the caption.)

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    # ====================== LOGIN PAGE WITH LOGO ======================
    st.markdown("<h2 style='text-align: center; color: #003087;'>St. Vital Mustangs Registration Portal</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(LOGO_URL, width=320)   # Large centered logo on login screen

    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")

# Note: Paste the full remaining page code (Equipment, Restricted Health, Events, Admin, Profile, etc.) from your v3.3 here to complete the file.
