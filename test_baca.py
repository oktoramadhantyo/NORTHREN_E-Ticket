import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(
    "modern-triumph-506502-u0-2b11a7b4943a.json", scopes=SCOPES
)
client = gspread.authorize(creds)

SHEET_ID = "1dXZpM8aqtalwxSImF4H34Q9_zwtIuGB7cGzpZx0_2VA"
sheet = client.open_by_key(SHEET_ID)
worksheet = sheet.get_worksheet(0)

data = worksheet.get("A1:H5")
for row in data:
    print(row)