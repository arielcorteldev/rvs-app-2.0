# MAY 14 2025
- Converted the audit_log table from SQLite to PostgreSQL
- Converted the verifications dbase from SQLite to PostgreSQL
- Created rvs_dbase to store all data tables related to the app
- Updated application codes to use PostgreSQL instead of SQLite


# MAY 15 2025
- Created releasing_log table to record all documents released
- Created releasing_docs file to handle the releasing of documents functionality
- Created Releasing Logbook to view the logs of released docs
- Created an Audit Log Viewer 
- Edited the eVERIFY flow for search, app and releasing docs
- Added refresh button to Releasing Logbook and Audit Log Viewer

# MAY 16 2025
- Converted users.db to PostgreSQL
- Updated the manage_users.py, app.py, audit_logger.py, and other files to using the PostgreSQL users
- Converted recordsstatus.db to PostgreSQL
- Updated the recordstatus.py to use the PostgreSQL searchable_records


- DESIGNED NEW UI WEW

# MAY 19 2025
- Continued updating the UI and Design

# MAY 20 2025
- Fixed the bug with the eVERIFY and Search connection
- Cleaned up the UI
- Centralized all windows to the Main Window
- Created an Export PDF function for Releasing Logbook and Audit Logs

# MAY 21 2025
- Updated logos and icons
- Configure PostgreSQL config to allow access across LAN

# MAY 26 2025
- Updated the color scheme to a neutral colors
- Created and .env file for API Keys for security
- Fixed some UI bugs


# MAY 27-28 2025
- Finalized the UI Design
- Setup a Static IP

# JUNE 3 2025
- Fixed IP address error

# JUNE 4 2025
- Created birth_index, death_index, marriage_index
- But have not implemented it yet
- Fixed error with saving Face Keys but have not tested yet

# JUNE 5 2025
- Created demo version of app
- Finalized the birth_index, death_index, and marriage_index columns

# JUNE 6 2025
- Imported new database with updated birth_index, death_index, and marriage_index in laptop
- Added City Seal and Office logo as footer in Main Window

# JUNE 9 2025
- Packaged the app for v2.2.1 (with city seal nad office logo)
- Revised the Tagging Functionality
- Created a Tagging Main Window to open individual windows for tagging for each live birth, death and marriage
- Created the tagging functionality for Live Birth

# JUNE 10 2025
- Created the tagging functionality for Marriage and Death

# JUNE 11 2025
- Created new search windows for book records
- Revised search logic to use database instead file name
- Started creating the auto-populate functionality for Certification Forms

# JUNE 13 2025
- Created auto-form module; Separated FormPreviewWindow from search_books
- Added auto-form button
- Edited the form images and finalized the sizing
- Continued laying out the line edits to the forms

# JUNE 16 2025
- Continued laying out positions for line edits 
- Finished Form 1-A layout
- Added if conditions for Place of Birth Hospitals
- Added remarks text edits
- Added functionality to remove the background image of forms and background color of fields when printing

# JUNE 17 2025
- Finished laying out field positions for Marriage and Death
- Added functionality to format the dates to "January 1, 2025" except Date Paid
- Change Cause of Death to a QTextEdit with 2 lines
- Fixed bug where tags for death_index are saved twice

# JUNE 18 2025
- Added auto logging function to FormPreviewWindow
- Set the Issued by field to the name of the current user
- Finalized the values of the field
- Rename the search certificates to search by file name

# JUNE 19 2025
- Rename search_data.py to verify.py and change the classes to Verify__
- Rearrange the layout for the old search method and the new search method, changing the new search method to Verify and the old search method Filename Search
- Deleted all code about Searchable Records as well as the Database
- Added new icon for Verify

# JUNE 25, 2025
- Edited the Remarks field
- Finalized the auto-form.py file and FormPreviewWindow
- Packaged the app for deployment

# JUNE 30, 2025
- Added remarks/annotations columns to the birth_index, death_index and marriage_index
- Added option to save the remarks entered on the Form Preview Window

# JULY 2, 2025
- Revised the database implementation for Statistics Feature to use the new postgre dbase
- Added an option to select the type of record
- Changed the Keys to be generated statistics from
- Packaged the app for deployment

# JULY 10, 2025
- Added the Book Viewer functionality to allow staff to view book pages digitally
- Packaged eVerify SDK

# July 11, 2025
- Finalized and prepared my everify module