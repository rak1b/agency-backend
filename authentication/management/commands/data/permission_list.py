"""
Centralized permission seed data used by management commands.

This structure is intentionally aligned with the backend seeding logic:
- section_name: module name shown as a section
- permissions[].code: machine-readable permission key used in authorization checks
"""

PERMISSION_LIST = [
    {
        "section_name": "Dashboard",
        "description": "Allows the user to access dashboard features.",
        "permissions": [
            {
                "name": "View Dashboard",
                "code": "view_dashboard",
                "description": "Allows the user to view dashboard data.",
            },
        ],
    },
    {
        "section_name": "Report",
        "description": "Allows the user to access report features.",
        "permissions": [
            {
                "name": "View Report",
                "code": "view_report",
                "description": "Allows the user to view reports.",
            },
        ],
    },
    {
        "section_name": "Agencies",
        "description": "Allows the user to manage agency records.",
        "permissions": [
            {
                "name": "View Agencies",
                "code": "view_agencies",
                "description": "Allows the user to view agencies.",
            },
            {
                "name": "Create Agency",
                "code": "create_agencies",
                "description": "Allows the user to create an agency.",
            },
            {
                "name": "Edit Agency",
                "code": "edit_agencies",
                "description": "Allows the user to edit an agency.",
            },
            {
                "name": "Delete Agency",
                "code": "delete_agencies",
                "description": "Allows the user to delete an agency.",
            },
        ],
    },
    {
        "section_name": "Student File",
        "description": "Allows the user to manage student file records.",
        "permissions": [
            {
                "name": "View Student Files",
                "code": "view_student_files",
                "description": "Allows the user to view student files.",
            },
            {
                "name": "Create Student File",
                "code": "create_student_files",
                "description": "Allows the user to create a student file.",
            },
            {
                "name": "Edit Student File",
                "code": "edit_student_files",
                "description": "Allows the user to edit a student file.",
            },
            {
                "name": "Update Student File",
                "code": "update_student_files",
                "description": "Allows the user to update a student file.",
            },
            {
                "name": "Delete Student File",
                "code": "delete_student_files",
                "description": "Allows the user to delete a student file.",
            },
        ],
    },
    {
        "section_name": "Universities",
        "description": "Allows the user to manage university records.",
        "permissions": [
            {
                "name": "View Universities",
                "code": "view_universities",
                "description": "Allows the user to view universities.",
            },
            {
                "name": "Create University",
                "code": "create_universities",
                "description": "Allows the user to create a university.",
            },
            {
                "name": "Edit University",
                "code": "edit_universities",
                "description": "Allows the user to edit a university.",
            },
            {
                "name": "Delete University",
                "code": "delete_universities",
                "description": "Allows the user to delete a university.",
            }
           
        
            
        ],
    },
     {
        "section_name": "Programs",
        "description": "Allows the user to manage university records.",
        "permissions": [
        
            {
                "name": "View programs",
                "code": "view_programs",
                "description": "Allows the user to view programs.",
            },
             {
                "name": "Create program",
                "code": "create_programs",
                "description": "Allows the user to create a program.",
            },
            {
                "name": "Edit program",
                "code": "edit_programs",
                "description": "Allows the user to edit a program.",
            },
            {
                "name": "Delete program",
                "code": "delete_programs",
                "description": "Allows the user to delete a program.",
            }
           
        
            
        ],
    },
    {
        "section_name": "Office Cost",
        "description": "Allows the user to manage office cost records.",
        "permissions": [
            {
                "name": "View Office Costs",
                "code": "view_office_costs",
                "description": "Allows the user to view office costs.",
            },
            {
                "name": "Create Office Cost",
                "code": "create_office_costs",
                "description": "Allows the user to create an office cost.",
            },
            {
                "name": "Edit Office Cost",
                "code": "edit_office_costs",
                "description": "Allows the user to edit an office cost.",
            },
            {
                "name": "Delete Office Cost",
                "code": "delete_office_costs",
                "description": "Allows the user to delete an office cost.",
            },
        ],
    },
    {
        "section_name": "Student Cost",
        "description": "Allows the user to manage student cost records.",
        "permissions": [
            {
                "name": "View Student Costs",
                "code": "view_student_costs",
                "description": "Allows the user to view student costs.",
            },
            {
                "name": "Create Student Cost",
                "code": "create_student_costs",
                "description": "Allows the user to create a student cost.",
            },
            {
                "name": "Edit Student Cost",
                "code": "edit_student_costs",
                "description": "Allows the user to edit a student cost.",
            },
            {
                "name": "Delete Student Cost",
                "code": "delete_student_costs",
                "description": "Allows the user to delete a student cost.",
            },
        ],
    },
    {
        "section_name": "Invoices",
        "description": "Allows the user to manage invoice records.",
        "permissions": [
            {
                "name": "View Invoices",
                "code": "view_invoices",
                "description": "Allows the user to view invoices.",
            },
            {
                "name": "Create Invoice",
                "code": "create_invoices",
                "description": "Allows the user to create an invoice.",
            },
            {
                "name": "Edit Invoice",
                "code": "edit_invoices",
                "description": "Allows the user to edit an invoice.",
            },
            {
                "name": "Delete Invoice",
                "code": "delete_invoices",
                "description": "Allows the user to delete an invoice.",
            },
        ],
    },
    {
        "section_name": "Roles",
        "description": "Allows the user to manage role records.",
        "permissions": [
            {
                "name": "View Roles",
                "code": "view_roles",
                "description": "Allows the user to view roles.",
            },
            {
                "name": "Create Role",
                "code": "create_roles",
                "description": "Allows the user to create a role.",
            },
            {
                "name": "Edit Role",
                "code": "edit_roles",
                "description": "Allows the user to edit a role.",
            },
            {
                "name": "Delete Role",
                "code": "delete_roles",
                "description": "Allows the user to delete a role.",
            },
        ],
    },
    {
        "section_name": "Users",
        "description": "Allows the user to manage user records.",
        "permissions": [
            {
                "name": "View Users",
                "code": "view_users",
                "description": "Allows the user to view users.",
            },
            {
                "name": "Create User",
                "code": "create_users",
                "description": "Allows the user to create a user.",
            },
            {
                "name": "Edit User",
                "code": "edit_users",
                "description": "Allows the user to edit a user.",
            },
            {
                "name": "Delete User",
                "code": "delete_users",
                "description": "Allows the user to delete a user.",
            },
        ],
    },
]