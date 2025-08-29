import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from settings import GOOGLE_SHEET_ID


def _get_client():
    """Authenticate and return a gspread client."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds)


def upload_data_to_sheet(data, sheet_name: str):
    """
    upload data (list of dicts) to a specified sheet (tab) in the Google Sheet.
    """
    df = pd.DataFrame(data)
    client = _get_client()
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=str(len(df)), cols=str(len(df.columns)))

    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# def append_data_to_sheet(data, sheet_name: str):
#     """
#     Append data (list of dicts) to a specified sheet (tab) in the Google Sheet.
#     If the sheet doesn't exist, create it.
#     """
#     df = pd.DataFrame(data)
#     client = _get_client()
#     spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

#     try:
#         # Try to open existing worksheet
#         worksheet = spreadsheet.worksheet(sheet_name)
#     except gspread.exceptions.WorksheetNotFound:
#         # If not found, create a new worksheet
#         worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=str(len(df)+1), cols=str(len(df.columns)))

#         # Write header and data
#         worksheet.update([df.columns.values.tolist()] + df.values.tolist())
#         return

#     # If sheet exists, append data
#     existing_data = worksheet.get_all_values()
#     next_row = len(existing_data) + 1
#     worksheet.update(f"A{next_row}", df.values.tolist())



# def clear_entire_sheet(sheet_name: str = None):
#     """
#     Removes all content from all worksheets (tabs) in the Google Sheet.
#     """
#     client = _get_client()
#     spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

#     for worksheet in spreadsheet.worksheets(sheet_name):
#         worksheet.clear()

