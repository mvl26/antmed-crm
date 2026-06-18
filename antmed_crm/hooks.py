app_name = "antmed_crm"
app_title = "AntMed CRM"
app_publisher = "AntMed"
app_description = "AntMed CRM — quản lý kinh doanh thiết bị & vật tư y tế"
app_email = "info@miyano.com.vn"
app_license = "AGPLv3"
app_icon_url = "/assets/antmed_crm/images/logo.svg"
app_icon_title = "AntMed CRM"
app_icon_route = "/crm"

# Apps
# ------------------

# required_apps = []
add_to_apps_screen = [
	{
		"name": "antmed_crm",
		"logo": "/assets/antmed_crm/images/logo.svg",
		"title": "AntMed CRM",
		"route": "/crm",
		"has_permission": "antmed_crm.api.check_app_permission",
	}
]

get_site_info = "antmed_crm.activation.get_site_info"

export_python_type_annotations = True
require_type_annotated_api_methods = True

# Fixtures
# --------
# AntMed (M01 bootstrap) — seed 3 Role RBAC, reproduce qua `bench migrate`.
# CHỈ filter đúng 3 Role AntMed (KHÔNG export toàn bộ Role của site).
fixtures = [
	{
		"doctype": "Role",
		"filters": {
			"name": [
				"in",
				["NV kinh doanh", "Thủ kho", "Quản lý"],
			]
		},
	},
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/antmed_crm/css/crm.css"
# app_include_js = "/assets/antmed_crm/js/crm.js"

# include js, css files in header of web template
# web_include_css = "/assets/antmed_crm/css/crm.css"
# web_include_js = "/assets/antmed_crm/js/crm.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "crm/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# "Role": "home_page"
# }

website_route_rules = [
	{"from_route": "/crm/<path:app_path>", "to_route": "crm"},
]

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# "methods": "antmed_crm.utils.jinja_methods",
# "filters": "antmed_crm.utils.jinja_filters"
# }

# Setup wizard
# setup_wizard_requires = "assets/crm/js/setup_wizard.js"
# setup_wizard_stages = "antmed_crm.setup.setup_wizard.setup_wizard.get_setup_stages"
setup_wizard_complete = "antmed_crm.demo.api.create_demo_data"
# setup_wizard_test = "antmed_crm.setup.setup_wizard.test_setup_wizard.run_setup_wizard_test"

# Installation
# ------------

before_install = "antmed_crm.install.before_install"
after_install = "antmed_crm.install.after_install"

# Uninstallation
# ------------

before_uninstall = "antmed_crm.uninstall.before_uninstall"
# after_uninstall = "antmed_crm.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "antmed_crm.utils.before_app_install"
# after_app_install = "antmed_crm.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "antmed_crm.utils.before_app_uninstall"
# after_app_uninstall = "antmed_crm.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "antmed_crm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"CRM Lead": "antmed_crm.permissions.org_hierarchy.get_lead_permission_query_conditions",
	"CRM Deal": "antmed_crm.permissions.org_hierarchy.get_deal_permission_query_conditions",
}

has_permission = {
	"CRM Lead": "antmed_crm.permissions.org_hierarchy.has_lead_permission",
	"CRM Deal": "antmed_crm.permissions.org_hierarchy.has_deal_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Contact": "antmed_crm.overrides.contact.CustomContact",
	"Email Template": "antmed_crm.overrides.email_template.CustomEmailTemplate",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Contact": {
		"validate": ["antmed_crm.api.contact.validate"],
	},
	"ToDo": {
		"after_insert": ["antmed_crm.api.todo.after_insert"],
		"on_update": ["antmed_crm.api.todo.on_update"],
	},
	"Communication": {
		"after_insert": ["antmed_crm.utils.on_communication_insert"],
		"on_update": ["antmed_crm.utils.on_communication_update"],
	},
	"Comment": {
		"after_insert": ["antmed_crm.utils.on_comment_insert"],
		"on_update": ["antmed_crm.api.comment.on_update"],
	},
	"WhatsApp Message": {
		"validate": ["antmed_crm.api.whatsapp.validate"],
		"on_update": ["antmed_crm.api.whatsapp.on_update"],
	},
	"CRM Deal": {
		"on_update": [
			"antmed_crm.fcrm.doctype.erpnext_crm_settings.erpnext_crm_settings.create_customer_in_erpnext"
		],
	},
	"User": {
		"before_validate": ["antmed_crm.api.live_demo.validate_user"],
		"validate_reset_password": ["antmed_crm.api.live_demo.validate_reset_password"],
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": ["antmed_crm.api.event.trigger_offset_event_notifications"],
	"hourly": ["antmed_crm.api.event.trigger_hourly_event_notifications"],
	"daily": [
		"antmed_crm.api.event.trigger_daily_event_notifications",
		"antmed_crm.fcrm.doctype.crm_view_settings.crm_view_settings.clear_old_versions",
		"antmed_crm.api.antmed.instrument_loan.check_overdue_loans",
		"antmed_crm.api.antmed.doctor_care.send_call_plan_today",
		"antmed_crm.api.antmed.doctor_care.notify_doctor_birthdays",
		"antmed_crm.api.antmed.inventory.notify_expiry_alerts",
	],
	"weekly": ["antmed_crm.api.event.trigger_weekly_event_notifications"],
	"daily_long": ["antmed_crm.lead_syncing.background_sync.sync_leads_from_sources_daily"],
	"hourly_long": ["antmed_crm.lead_syncing.background_sync.sync_leads_from_sources_hourly"],
	"monthly_long": ["antmed_crm.lead_syncing.background_sync.sync_leads_from_sources_monthly"],
	"cron": {
		"*/5 * * * *": ["antmed_crm.lead_syncing.background_sync.sync_leads_from_sources_5_minutes"],
		"*/10 * * * *": ["antmed_crm.lead_syncing.background_sync.sync_leads_from_sources_10_minutes"],
		"*/15 * * * *": ["antmed_crm.lead_syncing.background_sync.sync_leads_from_sources_15_minutes"],
	},
}

# Testing
# -------

before_tests = "antmed_crm.tests.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# "frappe.desk.doctype.event.event.get_events": "antmed_crm.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# "Task": "antmed_crm.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

ignore_links_on_delete = ["Failed Lead Sync Log"]

# Request Events
# ----------------
# before_request = ["antmed_crm.utils.before_request"]
# after_request = ["antmed_crm.utils.after_request"]

# Job Events
# ----------
# before_job = ["antmed_crm.utils.before_job"]
# after_job = ["antmed_crm.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# {
# "doctype": "{doctype_1}",
# "filter_by": "{filter_by}",
# "redact_fields": ["{field_1}", "{field_2}"],
# "partial": 1,
# },
# {
# "doctype": "{doctype_2}",
# "filter_by": "{filter_by}",
# "partial": 1,
# },
# {
# "doctype": "{doctype_3}",
# "strict": False,
# },
# {
# "doctype": "{doctype_4}"
# }
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# "antmed_crm.auth.validate"
# ]

after_migrate = [
	"antmed_crm.fcrm.doctype.fcrm_settings.fcrm_settings.after_migrate",
	"antmed_crm.api.whatsapp.add_roles",
]

standard_dropdown_items = [
	{
		"name1": "app_selector",
		"label": "Apps",
		"type": "Route",
		"route": "#",
		"is_standard": 1,
	},
	{
		"name1": "settings",
		"label": "Settings",
		"type": "Route",
		"icon": "settings",
		"route": "#",
		"is_standard": 1,
	},
	{
		"name1": "login_to_fc",
		"label": "Login to Frappe Cloud",
		"type": "Route",
		"route": "#",
		"is_standard": 1,
	},
	{
		"name1": "about",
		"label": "About",
		"type": "Route",
		"icon": "info",
		"route": "#",
		"is_standard": 1,
	},
	{
		"name1": "separator",
		"label": "",
		"type": "Separator",
		"is_standard": 1,
	},
	{
		"name1": "logout",
		"label": "Log out",
		"type": "Route",
		"icon": "log-out",
		"route": "#",
		"is_standard": 1,
	},
]
