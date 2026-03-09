"""
Google Sheets integration services for daily tasks.
"""
import gspread
from google.oauth2.service_account import Credentials
from django.conf import settings
from users.models import CustomUser
from clients.models import Client
from .models import DailyTask
from datetime import datetime, date
import re


class GoogleSheetsService:
    """
    Service class for interacting with Google Sheets API.
    """
    
    def __init__(self):
        """
        Initialize the Google Sheets service with credentials.
        """
        # Define the required scopes
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Load credentials from settings
        credentials_info = getattr(settings, 'GOOGLE_SHEETS_CREDENTIALS', {})
        if not credentials_info:
            raise ValueError("Google Sheets credentials not found in settings")
        
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes
        )
        
        # Authorize the client
        self.client = gspread.authorize(credentials)
        
        # Get the spreadsheet ID from settings
        self.spreadsheet_id = getattr(settings, 'GOOGLE_SHEETS_SPREADSHEET_ID', '')
        if not self.spreadsheet_id:
            raise ValueError("Google Sheets spreadsheet ID not found in settings")
    
    def get_sheet_names(self):
        """
        Get all sheet names from the spreadsheet.
        """
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            worksheets = spreadsheet.worksheets()
            # Clean sheet names: remove spaces, dots, commas, and normalize case
            cleaned_names = []
            for ws in worksheets:
                clean_name = re.sub(r'[.,\s]', '', ws.title.lower())
                cleaned_names.append({
                    'original': ws.title,
                    'cleaned': clean_name
                })
            return cleaned_names
        except Exception as e:
            print(f"Error getting sheet names: {e}")
            return []
    
    def get_assignees_from_sheets(self):
        """
        Get list of assignees from sheet names.
        """
        sheet_names = self.get_sheet_names()
        assignees = []
        
        for sheet in sheet_names:
            # Find users whose username or full name matches the sheet name
            # (case-insensitive, ignoring spaces, dots, commas)
            clean_name = sheet['cleaned']
            
            # Look for users with matching usernames or full names
            users = CustomUser.objects.filter(
                role='EMPLOYEE'
            ).filter(
                # Username matches
                username__iregex=f'^{re.escape(clean_name)}$' if clean_name else ''
            )
            
            # If no exact match, try partial match
            if not users.exists():
                users = CustomUser.objects.filter(
                    role='EMPLOYEE'
                ).filter(
                    username__icontains=clean_name
                )
            
            for user in users:
                if user not in assignees:
                    assignees.append({
                        'id': user.id,
                        'username': user.username,
                        'full_name': user.get_full_name() or user.username,
                        'sheet_original_name': sheet['original']
                    })
        
        return assignees
    
    def add_task_to_sheet(self, daily_task):
        """
        Add a daily task to the appropriate sheet based on the assignee.
        """
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # Find the worksheet for the assignee
            assignee_name = daily_task.assignee.get_full_name() or daily_task.assignee.username
            clean_assignee_name = re.sub(r'[.,\s]', '', assignee_name.lower())
            
            worksheets = spreadsheet.worksheets()
            target_worksheet = None
            
            for ws in worksheets:
                clean_ws_name = re.sub(r'[.,\s]', '', ws.title.lower())
                if clean_ws_name == clean_assignee_name:
                    target_worksheet = ws
                    break
            
            if not target_worksheet:
                # If no matching sheet found, use the first sheet as fallback
                target_worksheet = worksheets[0] if worksheets else None
                
                if not target_worksheet:
                    raise Exception("No worksheets found in the spreadsheet")
            
            # Find the date column by scanning the first few rows
            date_col_index = None
            all_values = target_worksheet.get_all_values()
            
            if all_values:
                # Look for a date column header in the first row
                first_row = all_values[0] if all_values else []
                for idx, cell in enumerate(first_row):
                    if any(keyword in cell.lower() for keyword in ['дата', 'date', 'число']):
                        date_col_index = idx
                        break
                
                # If no date column header found, assume it's column A (index 0)
                if date_col_index is None:
                    date_col_index = 0
            
            # Find the row with the matching date or closest date
            target_row_idx = None
            date_column_values = target_worksheet.col_values(date_col_index + 1)  # 1-indexed
            
            for idx, cell_value in enumerate(date_column_values):
                try:
                    # Try to parse the date from the cell
                    cell_date = self.parse_date_string(cell_value)
                    if cell_date and cell_date.date() == daily_task.date:
                        target_row_idx = idx + 1  # 1-indexed
                        break
                except:
                    continue
            
            # If date not found, find the closest date
            if target_row_idx is None:
                closest_row_idx = None
                min_diff = float('inf')
                
                for idx, cell_value in enumerate(date_column_values[1:], 1):  # Skip header
                    try:
                        cell_date = self.parse_date_string(cell_value)
                        if cell_date:
                            diff = abs((cell_date.date() - daily_task.date).days)
                            if diff < min_diff:
                                min_diff = diff
                                closest_row_idx = idx
                    except:
                        continue
                
                target_row_idx = closest_row_idx if closest_row_idx else len(date_column_values) + 1
            
            # Determine columns for client and plan
            client_col_idx = None
            plan_col_idx = None
            
            if all_values and len(all_values) > 0:
                first_row = all_values[0]
                for idx, cell in enumerate(first_row):
                    if any(keyword in cell.lower() for keyword in ['контрагент', 'клиент', 'client']):
                        client_col_idx = idx
                    elif any(keyword in cell.lower() for keyword in ['план', 'plan', 'задача', 'task']):
                        plan_col_idx = idx
                
                # If not found, use default positions (assuming client is B, plan is C)
                if client_col_idx is None:
                    client_col_idx = 1  # Column B
                if plan_col_idx is None:
                    plan_col_idx = 2  # Column C
            
            # Prepare the data to insert
            row_data = [''] * max(client_col_idx + 1, plan_col_idx + 1)
            
            if client_col_idx is not None:
                row_data[client_col_idx] = daily_task.client.name
            
            if plan_col_idx is not None:
                # Format: (author) description
                author = daily_task.creator.get_full_name() or daily_task.creator.username
                row_data[plan_col_idx] = f"({author}) {daily_task.description}"
            
            # Insert the row below the target row
            target_worksheet.insert_row(row_data, target_row_idx + 1)
            
            return True
            
        except Exception as e:
            print(f"Error adding task to sheet: {e}")
            return False
    
    def parse_date_string(self, date_str):
        """
        Parse various date formats from Google Sheets.
        """
        if not date_str:
            return None
        
        # Common date formats in Russian and international formats
        formats = [
            '%d.%m.%Y',  # 01.01.2023
            '%d/%m/%Y',  # 01/01/2023
            '%Y-%m-%d',  # 2023-01-01
            '%d.%m.%y',  # 01.01.23
            '%d/%m/%y',  # 01/01/23
            '%m/%d/%Y',  # 01/01/2023 (US format)
            '%m/%d/%y',  # 01/01/23 (US format)
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                return parsed_date
            except ValueError:
                continue
        
        # If none of the formats worked, return None
        return None
    
    def sync_task_results_from_sheet(self):
        """
        Synchronize task results from Google Sheets periodically.
        This method checks for updates in the comment/result fields and updates the DailyTask records.
        """
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # Get all daily tasks that are not completed
            incomplete_tasks = DailyTask.objects.filter(status__in=['active', 'hidden'])
            
            for task in incomplete_tasks:
                # Find the worksheet for the assignee
                assignee_name = task.assignee.get_full_name() or task.assignee.username
                clean_assignee_name = re.sub(r'[.,\s]', '', assignee_name.lower())
                
                worksheets = spreadsheet.worksheets()
                target_worksheet = None
                
                for ws in worksheets:
                    clean_ws_name = re.sub(r'[.,\s]', '', ws.title.lower())
                    if clean_ws_name == clean_assignee_name:
                        target_worksheet = ws
                        break
                
                if not target_worksheet:
                    continue
                
                # Find the task in the sheet
                all_values = target_worksheet.get_all_values()
                
                if not all_values:
                    continue
                
                # Find the row with the matching client and date
                target_row = None
                client_col_idx = None
                result_col_idx = None
                
                # Find column indices
                first_row = all_values[0]
                for idx, cell in enumerate(first_row):
                    if any(keyword in cell.lower() for keyword in ['контрагент', 'клиент', 'client']):
                        client_col_idx = idx
                    elif any(keyword in cell.lower() for keyword in ['комментарий', 'comment', 'результат', 'result']):
                        result_col_idx = idx
                
                if client_col_idx is None:
                    continue
                
                # Find the row with matching client and date
                for row_idx, row in enumerate(all_values[1:], 1):  # Skip header
                    if len(row) > client_col_idx and row[client_col_idx] == task.client.name:
                        # Check if the date matches
                        date_cell = row[0] if len(row) > 0 else None
                        try:
                            cell_date = self.parse_date_string(date_cell)
                            if cell_date and cell_date.date() == task.date:
                                target_row = row
                                break
                        except:
                            continue
                
                if target_row and result_col_idx is not None and len(target_row) > result_col_idx:
                    # Update the task result if it has changed
                    sheet_result = target_row[result_col_idx]
                    if sheet_result and sheet_result != task.result:
                        task.result = sheet_result
                        task.save()
            
            return True
            
        except Exception as e:
            print(f"Error syncing task results from sheet: {e}")
            return False


def get_assignees_from_google_sheets():
    """
    Public function to get assignees from Google Sheets.
    """
    try:
        service = GoogleSheetsService()
        return service.get_assignees_from_sheets()
    except Exception as e:
        print(f"Error getting assignees from Google Sheets: {e}")
        # Fallback: return all employees
        employees = CustomUser.objects.filter(role='EMPLOYEE')
        return [{
            'id': emp.id,
            'username': emp.username,
            'full_name': emp.get_full_name() or emp.username,
            'sheet_original_name': emp.get_full_name() or emp.username
        } for emp in employees]


def add_daily_task_to_google_sheet(daily_task):
    """
    Public function to add a daily task to Google Sheet.
    """
    try:
        service = GoogleSheetsService()
        return service.add_task_to_sheet(daily_task)
    except Exception as e:
        print(f"Error adding task to Google Sheet: {e}")
        return False


def sync_daily_task_results_from_google_sheet():
    """
    Public function to sync task results from Google Sheet.
    """
    try:
        service = GoogleSheetsService()
        return service.sync_task_results_from_sheet()
    except Exception as e:
        print(f"Error syncing task results from Google Sheet: {e}")
        return False


def schedule_periodic_sync():
    """
    Schedule periodic synchronization of task results from Google Sheets.
    This function sets up a scheduled task to run every 20 minutes.
    """
    import threading
    import time
    from datetime import datetime
    
    def sync_loop():
        while True:
            try:
                print(f"[{datetime.now()}] Starting periodic sync from Google Sheets...")
                sync_daily_task_results_from_google_sheet()
                print(f"[{datetime.now()}] Sync completed. Waiting 20 minutes...")
                # Wait for 20 minutes (1200 seconds)
                time.sleep(1200)
            except KeyboardInterrupt:
                print("Periodic sync interrupted by user.")
                break
            except Exception as e:
                print(f"Error in periodic sync: {e}")
                # Wait for 5 minutes before retrying if there was an error
                time.sleep(300)
    
    # Start the sync loop in a separate thread
    sync_thread = threading.Thread(target=sync_loop, daemon=True)
    sync_thread.start()
    
    return sync_thread