#!/usr/bin/env python
import re

# Read the file
with open('/workspace/tasks/views.py', 'r') as f:
    content = f.read()

# Replace the markAsRead function part
def replace_markasread_logic(content):
    # Pattern to match the specific section we want to replace
    pattern = r'(\s+task_id = parts\[0\]\n\s+client_id = parts\[1\] \n\s+user_id = parts\[2\]\n\s+date_str = parts\[3\].*?\n\s+# Create or update the read status\n\s+read_status, created = SurveyAnswerGroupReadStatus.objects.get_or_create\(\n\s+task_id=task_id,\n\s+client_id=client_id,\n\s+user_id=user_id,\n\s+date_created=date_str,)'
    
    replacement = r'                    task_id = parts[0]\n                    client_id = parts[1] \n                    user_id = parts[2]\n                    time_part = parts[3]  # This could be either a date string or a timestamp\n                    \n                    # Determine if this is the old format (date) or new format (timestamp)\n                    from datetime import datetime\n                    try:\n                        # Try to parse as timestamp (new format)\n                        timestamp = int(time_part) * 60  # Convert minutes back to seconds\n                        date_created = datetime.fromtimestamp(timestamp).date()\n                    except ValueError:\n                        # It\'s the old format (just date)\n                        date_created = time_part\n                    \n                    # Create or update the read status\n                    read_status, created = SurveyAnswerGroupReadStatus.objects.get_or_create(\n                        task_id=task_id,\n                        client_id=client_id,\n                        user_id=user_id,\n                        date_created=date_created,'
    
    # Replace the pattern
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    return updated_content

# Update the content
updated_content = replace_markasread_logic(content)

# Write the updated content back to the file
with open('/workspace/tasks/views.py', 'w') as f:
    f.write(updated_content)

print("File updated successfully!")