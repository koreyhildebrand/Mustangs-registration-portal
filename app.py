import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth

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
camp_reg_ws = ensure_worksheet("CampRegistrations", ["CampName","First Name","Last Name","Birthday","Phone Number","Email","Jersey Size","Years Experience","Session Info","Time Slots","CheckIn","CheckInTime","Additional Notes"])

players_df = pd.DataFrame(players_ws.get_all_records())
teams_df = pd.DataFrame(teams_ws.get_all_records())
camps_df = pd.DataFrame(camps_ws.get_all_records())
camp_reg_df = pd.DataFrame(camp_reg_ws.get_all_records())

# Dynamic Age Group
def calculate_age_group(dob_str, season_year):
    try:
        dob = datetime.datetime.strptime(str(dob_str).strip(), "%Y-%m-%d").date()
        birth_year = dob.year
        age = season_year - birth_year
        if 9 <= age <= 10:
            return "U10 Cruncher"
        elif 11 <= age <= 12:
            return "U12 Atom"
        elif 13 <= age <= 14:
            return "U14 PeeWee"
        elif 15 <= age <= 16:
            return "U16 Bantam"
        return f"Outside {season_year} Eligibility"
    except:
        return "Invalid DOB"

if "Date of Birth" in players_df.columns:
    players_df["AgeGroup"] = players_df["Date of Birth"].apply(lambda x: calculate_age_group(x, datetime.date.today().year))

# ====================== USER ROLES ======================
user_records = pd.DataFrame(users_ws.get_all_records()).to_dict("records")
user_row = next((u for u in user_records
