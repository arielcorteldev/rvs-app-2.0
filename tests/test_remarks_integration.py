#!/usr/bin/env python
"""Test remarks integration"""
from utilities.html_field_map import build_template_context

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

context = build_template_context(birth_record, 'Birth', current_user='test_user', today_date='2026-01-14')

# Check if remarks is in the context
if 'remarks' in context:
    print(f"✓ Remarks found in context: \"{context['remarks']}\"")
else:
    print("✗ Remarks not found in context")

# Verify all key fields are present
required_fields = ['name', 'reg_no', 'remarks', 'verified_by']
missing = [f for f in required_fields if f not in context]
if missing:
    print(f"✗ Missing fields: {missing}")
else:
    print(f"✓ All required fields present")
    print(f"✓ Name: {context['name']}")
    print(f"✓ Reg No: {context['reg_no']}")
    print(f"✓ Remarks: {context['remarks']}")
    print(f"✓ Verified By: {context['verified_by']}")
