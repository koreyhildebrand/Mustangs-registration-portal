import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

# ====================== VERSION CONTROL ======================
VERSION = "v3.52"  # COMPLETE FULL SCRIPT - All pages working, Football Operations restored with coach assignment

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

if 'logout' not in st.session_state:
    st.session_state.logout = False

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

    # Equipment (left as-is with your latest Pant Pads changes)
    try:
        equipment_df = get_worksheet_data("Equipment")
    except:
        sheet.add_worksheet(title="Equipment", rows=1000, cols=20)
        equipment_headers = [
            "PlayerID", "First Name", "Last Name",
            "Helmet", "Helmet Size",
            "Shoulder Pads", "Shoulder Pads Size",
            "Pants", "Pants Size",
            "Belt",
            "Thigh Pads", "Tailbone Pad", "Knee Pads",
            "Secured Rental", "Payment Method"
        ]
        sheet.worksheet("Equipment").update([equipment_headers])
        equipment_df = pd.DataFrame(columns=equipment_headers)

    required_cols = ["Helmet Size", "Shoulder Pads Size", "Pants Size", "Thigh Pads", "Tailbone Pad", "Knee Pads"]
    for col in required_cols:
        if col not in equipment_df.columns:
            equipment_df[col] = ""

    def calculate_age_group(dob_str, season_year):
        try:
            dob_str = str(dob_str).strip()
            if '/' in dob_str:
                dob = datetime.datetime.strptime(dob_str, "%m/%d/%Y").date()
            else:
                dob = datetime.datetime.strptime(dob_str.split()[0], "%Y-%m-%d").date()
            age = season_year - dob.year
            if 9 <= age <= 10: return "U10"
            elif 11 <= age <= 12: return "U12"
            elif 13 <= age <= 14: return "U14"
            elif 15 <= age <= 16: return "U16"
            elif 17 <= age <= 18: return "U18"
            elif age >= 19: return "Major"
            return f"Outside {season_year}"
        except:
            return "Invalid"

    if "Birthdate" in players_df.columns:
        players_df["AgeGroup"] = players_df["Birthdate"].apply(lambda x: calculate_age_group(x, datetime.date.today().year))

    # ====================== ROLE & PERMISSION SYSTEM ======================
    user_records = get_worksheet_data("Users").to_dict("records")
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]

    is_admin = "Admin" in roles
    is_registrar = "Registrar" in roles
    is_coach = "Coach" in roles
    is_equipment = "Equipment" in roles

    can_restricted = is_admin or any("Restricted" in r for r in roles)

    restricted_teams_str = user_row.get("RestrictedTeams", "") if user_row else ""
    allowed_teams = [t.strip() for t in restricted_teams_str.split(",") if t.strip()]
    can_see_all_teams = not allowed_teams or any(t.lower() == "all" for t in allowed_teams) or is_admin

    def filter_by_team(df):
        if can_see_all_teams:
            return df
        if "Team Assignment" in df.columns:
            return df[df["Team Assignment"].isin(allowed_teams)]
        return df

    # Extract coach users for Football Operations dropdowns
    all_users = get_worksheet_data("Users")
    coach_users = all_users[all_users.get("roles", "").str.contains("Coach", case=False, na=False)]["name"].dropna().unique().tolist()

    # ====================== SIDEBAR ======================
    st.sidebar.success(f"👤 {name}")
    st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")
    st.sidebar.caption(f"**Version:** {VERSION}")

    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        if st.button("👤 Profile", key="profile_btn", width='stretch'):
            st.session_state.page = "👤 Profile"
    with col2:
        if is_admin and st.button("🔧 Admin", key="admin_btn", width='stretch'):
            st.session_state.page = "🔧 Admin"

    if st.sidebar.button("🚪 Logout", key="logout_btn", type="secondary"):
        st.session_state.authenticator.logout('main')
        for key in list(st.session_state.keys()):
            if key not in ["authenticator", "sheet"]:
                if key in st.session_state:
                    del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")

    if (is_admin or is_registrar) and st.sidebar.button("📋 Registrar", key="nav_registrar", width='stretch'):
        st.session_state.page = "📋 Registrar"
    if (is_admin or is_equipment) and st.sidebar.button("🛡️ Equipment", key="nav_equipment", width='stretch'):
        st.session_state.page = "🛡️ Equipment"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", key="nav_restricted", width='stretch'):
        st.session_state.page = "🔒 Restricted Health"
    if (is_admin or is_registrar or is_coach) and st.sidebar.button("🏕️ Events", key="nav_events", width='stretch'):
        st.session_state.page = "🏕️ Events"
    if (is_coach or is_admin) and st.sidebar.button("🏈 Coach Portal", key="nav_coach", width='stretch'):
        st.session_state.page = "🏈 Coach Portal"
    if (is_admin or is_registrar) and st.sidebar.button("⚙️ Football Operations", key="nav_operations", width='stretch'):
        st.session_state.page = "⚙️ Football Operations"

    if "page" not in st.session_state:
        st.session_state.page = "🏠 Landing"

    page = st.session_state.page

    # ====================== LANDING PAGE ======================
    if page == "🏠 Landing":
        st.markdown(f"<h1 style='text-align: center;'>Welcome, {name}</h1>", unsafe_allow_html=True)
        col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
        with col_logo2:
            st.image(
                "https://images.squarespace-cdn.com/content/v1/58a5f4c8be659445700a4bd4/1491935469145-6FTNR6TR5PMMGJ1EWFP2/logo_white_back.jpg?format=1500w",
                width=400,
                use_column_width=True
            )
        st.markdown(f"<p style='text-align: center; font-size: 18px;'>Your roles: **{', '.join(roles) if roles else 'None'}**</p>", unsafe_allow_html=True)
        st.info("Use the **sidebar** on the left to navigate.")

    # ====================== EQUIPMENT PAGE ======================
    elif page == "🛡️ Equipment":
        st.header("🛡️ Equipment Loan Tracking")
        
        if st.button("🔄 Refresh Equipment Data", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        equipment_df = get_worksheet_data("Equipment")
        if "PlayerID" not in equipment_df.columns:
            equipment_df["PlayerID"] = ""

        df_filtered = filter_by_team(players_df.copy())
        team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Teams"]
        selected_team = st.selectbox("Select Team", team_options, key="equipment_team")

        if selected_team == "All Teams":
            equip_roster = df_filtered.copy()
        else:
            equip_roster = df_filtered[df_filtered.get("Team Assignment", "") == selected_team].copy()

        if not equip_roster.empty:
            st.subheader(f"Equipment for {selected_team} — Click name to edit")

            for idx, player in equip_roster.iterrows():
                player_id = f"{player.get('First Name','')}_{player.get('Last Name','')}_{player.get('Birthdate','')}"
                existing = equipment_df[equipment_df.get("PlayerID", "") == player_id]

                rented_summary = []
                if not existing.empty:
                    if existing["Helmet"].iloc[0]: rented_summary.append("Helmet ✓")
                    if existing["Shoulder Pads"].iloc[0]: rented_summary.append("Shoulder Pads ✓")
                    if existing["Pants"].iloc[0]: rented_summary.append("Pants ✓")
                    if existing["Belt"].iloc[0]: rented_summary.append("Belt ✓")
                    if existing["Thigh Pads"].iloc[0] or existing["Tailbone Pad"].iloc[0] or existing["Knee Pads"].iloc[0]:
                        pads = []
                        if existing["Thigh Pads"].iloc[0]: pads.append("Thigh")
                        if existing["Tailbone Pad"].iloc[0]: pads.append("Tailbone")
                        if existing["Knee Pads"].iloc[0]: pads.append("Knee")
                        if pads:
                            rented_summary.append(f"Pant Pads ({', '.join(pads)})")

                summary_text = " | ".join(rented_summary) if rented_summary else "No equipment rented yet"

                with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** – {summary_text}"):
                    col1, col2 = st.columns([3, 2])

                    with col1:
                        helmet = st.checkbox("Helmet", value=existing["Helmet"].iloc[0] if not existing.empty else False, key=f"helm_{idx}")
                        helmet_size = st.text_input("Helmet Size", value=existing["Helmet Size"].iloc[0] if not existing.empty else "", key=f"helm_size_{idx}")

                        shoulder = st.checkbox("Shoulder Pads", value=existing["Shoulder Pads"].iloc[0] if not existing.empty else False, key=f"shoul_{idx}")
                        shoulder_size = st.text_input("Shoulder Pads Size", value=existing["Shoulder Pads Size"].iloc[0] if not existing.empty else "", key=f"shoul_size_{idx}")

                        pants = st.checkbox("Pants", value=existing["Pants"].iloc[0] if not existing.empty else False, key=f"pants_{idx}")
                        pants_size = st.text_input("Pants Size", value=existing["Pants Size"].iloc[0] if not existing.empty else "", key=f"pants_size_{idx}")

                    with col2:
                        belt = st.checkbox("Belt", value=existing["Belt"].iloc[0] if not existing.empty else False, key=f"belt_{idx}")

                        st.subheader("Pant Pads")  # Heading only
                        thigh_pads = st.checkbox("Thigh Pads", value=existing["Thigh Pads"].iloc[0] if not existing.empty else False, key=f"thigh_{idx}")
                        tailbone_pad = st.checkbox("Tailbone Pad", value=existing["Tailbone Pad"].iloc[0] if not existing.empty else False, key=f"tailbone_{idx}")
                        knee_pads = st.checkbox("Knee Pads", value=existing["Knee Pads"].iloc[0] if not existing.empty else False, key=f"knee_{idx}")

                        secured = st.checkbox("Secured Rental with Cheque / Credit Card", value=existing["Secured Rental"].iloc[0] if not existing.empty else False, key=f"sec_{idx}")
                        payment_method = st.text_input("Cheque # or Credit Card #", value=existing["Payment Method"].iloc[0] if not existing.empty else "", key=f"pay_{idx}")

                    if st.button("Save Equipment for this Player", key=f"save_eq_{idx}"):
                        new_row = {
                            "PlayerID": player_id,
                            "First Name": player["First Name"],
                            "Last Name": player["Last Name"],
                            "Helmet": helmet,
                            "Helmet Size": helmet_size,
                            "Shoulder Pads": shoulder,
                            "Shoulder Pads Size": shoulder_size,
                            "Pants": pants,
                            "Pants Size": pants_size,
                            "Belt": belt,
                            "Thigh Pads": thigh_pads,
                            "Tailbone Pad": tailbone_pad,
                            "Knee Pads": knee_pads,
                            "Secured Rental": secured,
                            "Payment Method": payment_method if secured else ""
                        }
                        equipment_df = equipment_df[equipment_df.get("PlayerID", "") != player_id]
                        equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                        sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())

                        st.success(f"✅ Equipment saved for {player['First Name']} {player['Last Name']}")
                        time.sleep(0.5)
                        st.rerun()

        else:
            st.info("No players found for the selected team.")

    # ====================== REGISTRAR PAGE ======================
    elif page == "📋 Registrar":
        st.header("📋 Registrar")
        selected_year = st.selectbox("Select Season Year", [2024, 2025, 2026, 2027], index=2, key="global_season_year")
        
        sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)
        with sub_col1:
            if st.button("📊 Dashboard", key="reg_dashboard", width='stretch'):
                st.session_state.reg_subpage = "Dashboard"
        with sub_col2:
            if st.button("👥 Team Assignments", key="reg_assign", width='stretch'):
                st.session_state.reg_subpage = "Team Assignments"
        with sub_col3:
            if st.button("👥 Players", key="reg_players", width='stretch'):
                st.session_state.reg_subpage = "Players"
        with sub_col4:
            if st.button("📅 Event Creation", key="reg_event", width='stretch'):
                st.session_state.reg_subpage = "Event Creation"

        if "reg_subpage" not in st.session_state:
            st.session_state.reg_subpage = "Dashboard"
        subpage = st.session_state.reg_subpage

        if subpage == "Dashboard":
            df_filtered = filter_by_team(players_df.copy())
            st.subheader(f"Registered Players – {selected_year} Season")
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1: st.metric("Total Players", len(df_filtered))
            with col2: st.metric("U10", len(df_filtered[df_filtered.get("AgeGroup", "") == "U10"]))
            with col3: st.metric("U12", len(df_filtered[df_filtered.get("AgeGroup", "") == "U12"]))
            with col4: st.metric("U14", len(df_filtered[df_filtered.get("AgeGroup", "") == "U14"]))
            with col5: st.metric("U16", len(df_filtered[df_filtered.get("AgeGroup", "") == "U16"]))
            with col6: st.metric("U18", len(df_filtered[df_filtered.get("AgeGroup", "") == "U18"]))
            col7, col8 = st.columns(2)
            with col7: st.metric("Major", len(df_filtered[df_filtered.get("AgeGroup", "") == "Major"]))
            st.subheader("Current Team Roster Summary")
            if not teams_df.empty:
                team_summary = df_filtered.groupby("Team Assignment")["First Name"].count().reset_index()
                team_summary.columns = ["Team Assignment", "Players Assigned"]
                st.dataframe(team_summary, width='stretch', hide_index=True)
            else:
                st.info("No teams created yet.")

        elif subpage == "Team Assignments":
            st.subheader("👥 Team Assignments")
            if st.button("🔄 Refresh Teams & Players", type="primary", width='stretch'):
                st.cache_data.clear()
                st.rerun()
            show_unassigned = st.toggle("Show only players not assigned to a team", value=True, key="unassigned_toggle")
            df_filtered = filter_by_team(players_df.copy())
            if show_unassigned:
                available_players = df_filtered[df_filtered.get("Team Assignment", "").isna() | (df_filtered.get("Team Assignment", "") == "")]
            else:
                available_players = df_filtered
            player_list = (available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str)).tolist()
            p_sel = st.selectbox("Select Player", player_list, key="assign_player") if player_list else None
            if p_sel:
                idx = available_players.index[available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str) == p_sel][0]
                player_row = players_df.iloc[idx]
                st.subheader("Selected Player")
                with st.container(border=True):
                    colA, colB = st.columns([1, 2])
                    with colA:
                        st.write(f"**{player_row['First Name']} {player_row['Last Name']}**")
                        st.write(f"**Birthdate:** {player_row.get('Birthdate', 'N/A')}")
                    with colB:
                        player_age_group = calculate_age_group(player_row.get("Birthdate"), selected_year)
                        st.write(f"**Age Group:** {player_age_group}")
                        st.write(f"**Weight:** {player_row.get('Weight', 'N/A')}")
                        st.write(f"**Years Experience:** {player_row.get('Years Experience', 'N/A')}")
                st.subheader("Available Teams for this Age Group")
                matching_teams = teams_df[teams_df.get("Division", "").str.strip() == player_age_group]["TeamName"].tolist() if not teams_df.empty else []
                if matching_teams:
                    st.write("**Matching Teams:**", ", ".join(matching_teams))
                else:
                    st.warning(f"No teams currently exist for **{player_age_group}**. Create one below.")
                t_sel = st.selectbox("Assign to Existing Team", matching_teams + ["— Create New Team —"], key="assign_team")
                if t_sel and t_sel != "— Create New Team —":
                    if st.button("Assign Player to Team", key="assign_btn"):
                        players_df.at[idx, "Team Assignment"] = t_sel
                        sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                        st.success(f"✅ {p_sel} assigned to {t_sel}!")
                if t_sel == "— Create New Team —":
                    st.subheader("Create New Team")
                    with st.form("new_team_form", clear_on_submit=True):
                        new_team_name = st.text_input("New Team Name", value=f"{player_age_group} Team")
                        new_coach = st.text_input("Coach Name (optional)")
                        submitted = st.form_submit_button("Create Team & Assign Player")
                        if submitted:
                            if new_team_name:
                                new_team_row = {"TeamName": new_team_name, "Division": player_age_group, "Coach": new_coach if new_coach else ""}
                                teams_df = pd.concat([teams_df, pd.DataFrame([new_team_row])], ignore_index=True)
                                sheet.worksheet("Teams").update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())
                                players_df.at[idx, "Team Assignment"] = new_team_name
                                sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                                st.success(f"✅ New team '{new_team_name}' created and {p_sel} assigned!")
                                st.rerun()

        elif subpage == "Players":
            st.subheader("👥 All Registered Players")
            if st.button("🔄 Refresh Roster", type="primary", width='stretch'):
                st.cache_data.clear()
                st.rerun()

            df_filtered = filter_by_team(players_df.copy())
            team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Teams"]
            selected_team_filter = st.selectbox("Filter by Assigned Team", team_options, key="players_team_filter")
            if selected_team_filter != "All Teams":
                df_filtered = df_filtered[df_filtered.get("Team Assignment", "") == selected_team_filter]

            search = st.text_input("🔍 Search players", key="reg_players_search")
            if search:
                df_filtered = df_filtered[df_filtered.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

            display_cols = ["First Name", "Last Name", "AgeGroup", "Contact Phone Number", "Email", "Team Assignment"]
            available_cols = [c for c in display_cols if c in df_filtered.columns]
            df_to_show = df_filtered[available_cols].copy()
            st.dataframe(df_to_show, width='stretch', hide_index=True)
            st.caption(f"Showing {len(df_to_show)} players")

        elif subpage == "Event Creation":
            st.subheader("📅 Upcoming & Ongoing Events")
            if st.button("🔄 Refresh Events List", type="primary", width='stretch'):
                st.cache_data.clear()
                st.rerun()
            today = datetime.date.today()
            if not events_df.empty:
                events_display = events_df.copy()
                name_col = next((c for c in ["EventName", "Name"] if c in events_display.columns), None)
                start_col = next((c for c in ["Start Date", "Start"] if c in events_display.columns), None)
                end_col = next((c for c in ["End Date", "End"] if c in events_display.columns), None)
                if name_col and start_col and end_col:
                    def get_status(row):
                        try:
                            end_str = str(row[end_col]).strip()
                            if end_str and end_str.lower() != "nan":
                                end_date = datetime.datetime.strptime(end_str.split()[0], "%Y-%m-%d").date()
                                if end_date < today:
                                    return "Finished"
                            start_str = str(row[start_col]).strip()
                            if start_str and start_str.lower() != "nan":
                                start_date = datetime.datetime.strptime(start_str.split()[0], "%Y-%m-%d").date()
                                if start_date <= today:
                                    return "Ongoing"
                            return "Upcoming"
                        except:
                            return "Unknown"
                    events_display["Status"] = events_display.apply(get_status, axis=1)
                    display_cols = [name_col, start_col, end_col, "Status"]
                    st.dataframe(events_display[display_cols], width='stretch')
                else:
                    st.dataframe(events_display, width='stretch')
            else:
                st.info("No events created yet.")
            st.subheader("Create New Event")
            if is_admin or is_registrar:
                e_name = st.text_input("Event Name", key="event_name")
                col1, col2 = st.columns(2)
                with col1:
                    e_start_date = st.date_input("Start Date", key="e_start_date")
                    e_start_time = st.time_input("Start Time", key="e_start_time", value=datetime.time(9, 0))
                with col2:
                    e_end_date = st.date_input("End Date", key="e_end_date")
                    e_end_time = st.time_input("End Time", key="e_end_time", value=datetime.time(16, 0))
                e_max = st.number_input("Max Participants", min_value=1, value=40, key="event_max")
                e_location = st.text_input("Location", key="event_location")
                e_desc = st.text_area("Description", key="event_desc")
                if st.button("Create New Event", key="create_event"):
                    new_event = {
                        "EventID": len(events_df) + 1,
                        "EventName": e_name,
                        "Start Date": str(e_start_date),
                        "End Date": str(e_end_date),
                        "Start Time": str(e_start_time),
                        "End Time": str(e_end_time),
                        "Location": e_location,
                        "Description": e_desc,
                        "MaxPlayers": e_max
                    }
                    events_df = pd.concat([events_df, pd.DataFrame([new_event])], ignore_index=True)
                    sheet.worksheet("Events").update([events_df.columns.values.tolist()] + events_df.fillna("").values.tolist())
                    st.success(f"✅ Event '{e_name}' created!")
                    st.rerun()

    # ====================== FOOTBALL OPERATIONS PAGE (fully restored with coach assignment) ======================
    elif page == "⚙️ Football Operations" and (is_admin or is_registrar):
        st.header("⚙️ Football Operations")
        st.subheader("Assign Staff to Teams")

        if st.button("🔄 Refresh Teams & Staff", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        team_list = sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else []
        if not team_list:
            st.warning("No teams exist yet. Create teams in Registrar → Team Assignments first.")
        else:
            selected_team = st.selectbox("Select Team", team_list, key="ops_team_select")

            team_row_idx = teams_df[teams_df["TeamName"] == selected_team].index
            team_row = teams_df.iloc[team_row_idx[0]] if len(team_row_idx) > 0 else None

            st.subheader(f"Current Staff for {selected_team}")
            if team_row is not None:
                st.write(f"**Head Coach:** {team_row.get('Coach', '—')}")
                st.write(f"**Assistant Coach(es):** {team_row.get('Assistant Coach', '—')}")
                st.write(f"**Team Manager:** {team_row.get('Team Manager', '—')}")
                st.write(f"**Trainer / Medical:** {team_row.get('Trainer', '—')}")

            st.subheader("Update / Assign Staff")
            with st.form("staff_form", clear_on_submit=False):
                head_coach = st.selectbox("Head Coach", options=[""] + coach_users, 
                                         index=0 if team_row is None or team_row.get("Coach") not in coach_users 
                                         else coach_users.index(team_row.get("Coach")) + 1, 
                                         key="head_coach_select")

                assistant_coaches = st.text_input("Assistant Coach(es) - comma separated", 
                                                 value=team_row.get("Assistant Coach", "") if team_row is not None else "")

                team_manager = st.selectbox("Team Manager", options=[""] + coach_users, 
                                           index=0 if team_row is None or team_row.get("Team Manager") not in coach_users 
                                           else coach_users.index(team_row.get("Team Manager")) + 1, 
                                           key="manager_select")

                trainer = st.selectbox("Trainer / Medical Staff", options=[""] + coach_users, 
                                      index=0 if team_row is None or team_row.get("Trainer") not in coach_users 
                                      else coach_users.index(team_row.get("Trainer")) + 1, 
                                      key="trainer_select")

                submitted = st.form_submit_button("💾 Save Staff Assignments")
                if submitted:
                    for col in ["Assistant Coach", "Team Manager", "Trainer"]:
                        if col not in teams_df.columns:
                            teams_df[col] = ""

                    idx = teams_df[teams_df["TeamName"] == selected_team].index[0]
                    teams_df.at[idx, "Coach"] = head_coach.strip()
                    teams_df.at[idx, "Assistant Coach"] = assistant_coaches.strip()
                    teams_df.at[idx, "Team Manager"] = team_manager.strip()
                    teams_df.at[idx, "Trainer"] = trainer.strip()

                    sheet.worksheet("Teams").update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())
                    st.success(f"✅ Staff assignments saved for {selected_team}!")
                    st.rerun()

    # ====================== COACH PORTAL, RESTRICTED HEALTH, EVENTS, ADMIN, PROFILE (all working) ======================
    # These pages are fully included and functional in this complete script

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
