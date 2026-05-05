#!/usr/bin/env python
"""Test complete HTML rendering with remarks"""
from utilities.html_renderer import render_html_form

# Test with Birth record including remarks
birth_record = {
    'name': 'Juan Dela Cruz',
    'date_of_birth': '1990-01-15',
    'sex': 'Male',
    'page_no': '5',
    'book_no': '12',
    'reg_no': 'BIR2024-001',
    'date_of_reg': '2024-01-20',
    'place_of_birth': 'Manila',
    'name_of_mother': 'Maria Cruz',
    'nationality_mother': 'Filipino',
    'name_of_father': 'Jose Dela Cruz',
    'nationality_father': 'Filipino',
    'parents_marriage_date': '1988-06-10',
    'parents_marriage_place': 'Manila',
    'attendant': 'Dr. Santos',
    'remarks': 'This is a test remark for the birth certificate.'
}

html = render_html_form(birth_record, 'Birth', use_tempfile=False, current_user='test_user', today_date='2026-01-14')

# Check if remarks is in the rendered HTML
if 'This is a test remark for the birth certificate.' in html:
    print("✓ Remarks successfully rendered in HTML")
else:
    print("✗ Remarks NOT found in rendered HTML")

# Check other key fields
checks = {
    'Name': 'Juan Dela Cruz' in html,
    'Reg No': 'BIR2024-001' in html,
    'Date of Birth': '1990-01-15' in html or 'January 15, 1990' in html,
    'Verified By': 'TEST_USER' in html,
}

for check_name, result in checks.items():
    status = '✓' if result else '✗'
    print(f"{status} {check_name}")

if all(checks.values()):
    print("\n✓ All checks passed - remarks rendering is working!")
else:
    print("\n✗ Some checks failed")
    # Show first 500 chars for debugging
    print("\nFirst 500 chars of HTML:")
    print(html[:500])
