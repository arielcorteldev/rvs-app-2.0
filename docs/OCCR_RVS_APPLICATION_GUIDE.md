# OCCR Records Verification System
## Office Application Guide

## Executive summary

The OCCR Records Verification System (RVS) supports the Office of the City Civil Registrar in organizing and using its civil registry records. It brings together work for live birth, death, and marriage records: locating scanned documents, entering record details so they can be searched, checking record information, preparing forms, recording document releases, and reviewing office activity.

Staff can use RVS to find a record by its details or locate a scanned file, view registry books, monitor digitization work, and generate statistics and reports. It also includes eVerify for identity verification and user and activity controls for accountable office use.

RVS is most useful when staff keep the record details and digitization status up to date. Search results depend on the information and scanned files available to the office. eVerify also depends on access to its verification service and, for QR verification, a working camera.

## What the application helps the office do

- Work with **Live Birth**, **Death**, and **Marriage** records in one application.
- Find records already entered in RVS, or search for scanned documents in the office’s file collections.
- Enter details for scanned records and for records that have not yet been scanned.
- Review scanned registry books and supporting record files.
- Prepare record-based forms and forms for no-record or destroyed-record findings.
- Record which documents were released, to whom, and by whom.
- Monitor scanning and tagging progress, and produce statistics and reports.
- Manage staff access and review a history of important application activity.

## Menus and navigation

After signing in, the **Digitization Status** window opens. Use the navigation panel to reach the other functions. If the panel is showing icons only, expand it to see the menu names.

| Menu | Options | Purpose |
|---|---|---|
| **Verify Records** | **Live Birth**, **Death**, **Marriage** | Find records entered in RVS, review their details, and proceed with record verification or form preparation. |
| **Search Files** | **Live Birth**, **Death**, **Marriage** | Find and open scanned record files by their file names. |
| **eVerify** | Opens eVerify | Verify identity using personal information or a QR code. |
| **Releasing** | **Release Document**, **Releasing Logbook** | Record a document release or review previously recorded releases. |
| **Other Features** | **Generate Statistics**, **Tag Records**, **Book Viewer**, **COMELEC Death Report**, **Digitization Status** | Access reporting, digitization, and registry-book tools. |
| **User Management** | **Manage Users**, **Audit Logbook** | Maintain user accounts. The Audit Logbook is available to superusers only. |
| **Logout** | — | End the current session and return to the sign-in window. |

Within **Tag Records**, choose **Live Birth**, **Death**, or **Marriage** to open the relevant tagging workspace. Manual record entry is available from **Create Form** in the corresponding **Verify Records** window; it is not a separate top-level menu.

## Features and how they work

### 1. Sign-in and user access

Staff sign in with an assigned username and password. The application identifies the signed-in user so that key actions can be associated with the account that performed them. **Logout** asks for confirmation, closes the user's open application windows, and returns to sign-in.

There are two access levels:

- **Standard users** can use the record and office functions available to them and can view and edit their own account details. They cannot create or delete accounts or open the Audit Logbook.
- **Superusers** can create, update, and delete user accounts, assign superuser access, and open the Audit Logbook. They can also maintain the Digitization Status register.

### 2. Verify Records

Choose **Verify Records**, then select **Live Birth**, **Death**, or **Marriage**. These windows search the record details already entered in RVS. Search using a name, date, or registry number. For marriage records, a name search can find either spouse.

From a search result, staff can:

- Open an associated scanned document when one is available.
- Review or edit a record that has been entered but does not yet have a scanned file.
- Add or update remarks for a selected record.
- Use **Create Form** to enter a record that is not yet available in the searchable records.
- Use **Auto-generate Form** to prepare a record-based civil registration form for review.
- Prepare a **No Record** or **Record Destroyed** form where appropriate.

The record-based form is populated from the selected record and opens in a preview for staff review. Check the information against the source record and office procedures before printing or issuing any document.

### 3. Search Files

Choose **Search Files**, then select the record type. This feature searches the names of scanned files in the relevant year folder; it is different from **Verify Records**, which searches record details entered in RVS.

Enter the registration year or book number, select **Name**, **Date**, or **Reg No.**, provide the search text, and run the search. Open a result to view its scanned document. The search can look through folders beneath the selected year folder, but the year folder must exist and the file must be available in the office collection.

The Search Files window also provides **Create Form**, **Create No Record Form**, and **Create Record Destroyed Form** actions. eVerify can pass a verified name to a search window and start a name search.

### 4. Tag Records

Use **Other Features → Tag Records** to index details from scanned files. Choose Live Birth, Death, or Marriage, select the folder containing the PDFs, and select a file. The workspace displays the scanned document alongside one or more record-entry cards. Selecting a file shows any entries already saved for it; staff can add a card for another record on the same file.

Each record card supports **Save Entry**, **Edit**, and **Delete Entry**. The details vary by record type:

- **Live Birth:** child’s name, sex, birth date and place, birth type, mother and father details, parents’ marriage information, attendant, and registration details.
- **Death:** name, sex, birth and death dates, age, civil status, nationality, residence, place and cause of death, disposal, attendant, and registration details.
- **Marriage:** husband and wife details, marriage date and place, ceremony information, and registration details.

The information saved by tagging becomes available in **Verify Records** searches. Review the entry against the scanned source before saving.

### 5. Manual record entry

Use **Verify Records → [record type] → Create Form** when entering a record that is not already available in RVS. Before entering it, the application prompts staff to search for the record and check the Digitization Status register. This helps avoid creating a duplicate entry when a scanned or indexed record already exists.

The entry form collects registry identifiers and relevant details for the selected record:

- **Live Birth:** registry references; child’s name, sex, birth date and place; birth type; parent details; parents’ marriage information; attendant; and registration details.
- **Death:** registry references; name, sex, birth and death dates; age; place and cause of death; civil status, nationality and residence; disposal; attendant; and registration details.
- **Marriage:** registry references; husband and wife details; marriage date and place; ceremony type; and registration details.

Cards provide **Save Entry**, **Edit**, and **Delete Entry** actions. If the Registry No. is missing, the application warns staff, but allows them to choose whether to save. Manual entries do not have a scanned document attached. If a scan is added later, staff must use the appropriate office process to connect or reconcile it; entering the record alone does not attach it.

### 6. Digitization Status

The Digitization Status window is a register maintained by staff. It is not an automatic count of every scanned file or every record tagged in RVS.

Each register entry identifies a record type (**Live Birth**, **Death**, or **Marriage**), a category (**Book** or **Certificate**), and a label. Staff can mark whether the item is **Scanned** and **Tagged**. The register displays its last-updated time and can be filtered by record type and category or searched by label.

All users can view and search the register. Superusers can add entries, update their scanned and tagged flags, and delete entries. When updating an existing entry, its record type, category, and label cannot be changed. Use the register to identify work still needed; use **Verify Records** to search entered records and **Book Viewer** to browse scanned registry books.

### 7. Book Viewer

**Other Features → Book Viewer** opens scanned registry books for browsing. Select a PDF to view it, move between files with **Previous** and **Next**, and use the zoom controls to make pages easier to read. The viewer displays the selected file’s position in the list.

Book Viewer is for viewing documents. Use **Tag Records** to save searchable details from a scan.

### 8. Generate Statistics

**Other Features → Generate Statistics** produces counts and summaries for Live Birth, Death, and Marriage records. Choose **Total Count** or **Breakdown**, select a field or category, and set the relevant date range. A total count can be narrowed using a value, an age range where applicable, and an optional secondary filter.

Available summaries include overall or monthly totals and record-specific breakdowns such as sex, place, nationality, age, ceremony type, or late registration. Staff can export the results as a PDF report. The figures reflect the records and dates entered in RVS and the filters selected for the report.

### 9. COMELEC Death Report

**Other Features → COMELEC Death Report** prepares a death-record listing for transmittal. The report can be filtered by a date range and exported as a PDF. **Transmittal Letter** opens a letter for review.

The report applies preset eligibility filters: it includes records for people aged 18 or older, whose residence contains “Maasin,” and whose registration date falls within the selected period. It is therefore a specific report, not a listing of every death record. Review the results before transmittal.

### 10. eVerify

Open **eVerify** from the navigation panel, or start it from supported search, verification, and release workflows. The window offers two ways to proceed:

- **Personal Information:** provide the person's first and last name, birth date, and optional middle name or suffix.
- **Scan QR Code:** scan a supported QR code using the computer's camera.

The verification process can include a face-liveness check and confirmation with the external verification service. When verification succeeds, the verified name can be returned to the calling workflow—for example, to fill the recipient name in a release or to search for a record. A successful result can also be previewed and printed as a National ID Verification Form.

eVerify requires the external service and network connection to be available. QR scanning requires camera access, and the liveness step must complete. If those prerequisites are unavailable or the service cannot verify the information, eVerify cannot complete the check.

### 11. Releasing and Releasing Logbook

Use **Releasing → Release Document** to record a document issued by the office. Enter the document owner's name, document type, number of copies, recipient, and the staff member releasing it. The recipient can be entered manually or filled through eVerify. All fields are required, and the copy count must be between 1 and 999.

Available document types include certified true copies for birth, death, and marriage records; Forms 1-A, 1-B, 1-C, 2-A, 2-B, 2-C, 3-A, 3-B, and 3-C; and annotated 1-A, 2-A, and 3-A forms. Submitting the form records the release and confirms it on screen. The workflow records the transaction; it does not produce a separate receipt.

Use **Releasing → Releasing Logbook** to review release history. Filter the log by document owner, type, released-by, received-by, and date range. The logbook also provides **Apply Filters**, **Reset**, **Refresh**, and **Export PDF**.

### 12. Manage Users and Audit Logbook

**User Management → Manage Users** displays account information and provides **Add**, **Edit**, **Update**, and **Delete** actions. Superusers can manage user accounts and assign superuser access. Standard users see their own account and can edit it, but cannot add or delete accounts.

**User Management → Audit Logbook** is for superusers. It lists recorded activity with the username, action, details, and time. Filter entries by username, action, or date range, then use **Apply Filters**, **Reset**, or **Refresh**. The filtered log can be exported as a PDF. Access to the Audit Logbook is restricted to superusers.

## Benefits to the office

- **Faster record retrieval:** Staff can search entered record details or find a scanned file without browsing every book manually.
- **Better access to historical documents:** Book Viewer and file search make existing scans easier to locate and review.
- **More consistent indexing:** Tagging uses structured entry cards, making scanned records easier to find later.
- **A path for records not yet scanned:** Manual entry allows details to be recorded and searched while the office works through digitization.
- **Fewer avoidable duplicate entries:** The manual-entry workflow encourages staff to search and check digitization status before creating a new record.
- **More informed service:** Record-based forms, no-record or destroyed-record forms, and eVerify support common verification and document workflows.
- **Clearer document-release history:** Releasing and its logbook record the document, recipient, number of copies, and releasing staff member.
- **Visibility into digitization work:** The status register helps staff see which books or certificates are marked scanned and tagged, and what still needs attention.
- **Support for office reporting:** Statistics and the COMELEC Death Report help prepare summaries and transmittal materials from available records.
- **Accountability:** User access levels and the Audit Logbook help the office manage permissions and review important activity.

## Practical reminders

- A search can only find information present in the scanned files or records entered in RVS. If a result is missing, check the source file, year folder, and digitization status.
- Verify record details against the original or scanned source and follow office review procedures before issuing a form or certificate.
- Manual entry does not attach a scanned file. Keep the entry and the later scanning/tagging work aligned through the office’s established process.
- The Digitization Status register is maintained by staff; update it as work is completed so that it remains useful.
- eVerify depends on an external service. Camera, network, or service availability can affect QR and identity checks.
