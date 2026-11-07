{
    "name": "Email Tracker",
    "summary": "Know when customers open your emails: chatter log and "
               "notification to the responsible user",
    "description": """
Email Tracker
=============
Adds an invisible tracking pixel to emails sent from any document chatter.
When a recipient opens the email, the first open is logged on the document
chatter and, optionally, the sender / responsible user is notified.
""",
    "version": "18.0.1.1.0",
    "category": "Productivity/Discuss",
    "author": "Leofren Technologies",
    "website": "https://www.leofren.com",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/email_tracker_security.xml",
        "data/ir_config_parameter_data.xml",
        "views/email_tracker_recipient_views.xml",
        "views/mail_message_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "email_tracker/static/src/**/*",
        ],
        "web.assets_tests": [
            "email_tracker/static/tests/tours/**/*",
        ],
    },
    "images": ["static/description/banner/email_tracker_cover.png"],
    "installable": True,
    "application": False,
}
