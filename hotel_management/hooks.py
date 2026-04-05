app_name = "hotel_management"
app_title = "Hotel Management"
app_publisher = "VRPnext"
app_description = "Complete ERP for Hotels integrated with ERPNext"
app_email = "support@vrpnext.com"
app_license = "MIT"
app_version = "1.0.0"

required_apps = ["erpnext"]

# Fixtures - Export custom fields with the app
fixtures = [
	{
		"doctype": "Custom Field",
		"filters": [
			["dt", "in", ["Sales Invoice Item", "Purchase Invoice Item"]],
			["fieldname", "=", "property_unit"]
		]
	}
]

# Document Events - Trigger functions on document actions
doc_events = {
	"Reservation": {
		"on_update_after_submit": "hotel_management.hotel_management.doctype.guest.guest.update_guest_statistics"
	},
	"Sales Invoice": {
		"on_submit": "hotel_management.hotel_management.doctype.reservation.reservation.sync_from_invoice",
		"on_cancel": "hotel_management.hotel_management.doctype.reservation.reservation.sync_from_invoice",
		"on_update_after_submit": "hotel_management.hotel_management.doctype.reservation.reservation.sync_from_invoice"
	},
	"Payment Entry": {
		"on_submit": "hotel_management.hotel_management.doctype.reservation.reservation.sync_from_payment",
		"on_cancel": "hotel_management.hotel_management.doctype.reservation.reservation.sync_from_payment"
	}
}

# Scheduled Tasks - Run periodic jobs
scheduler_events = {
	# Run on 1st day of every month at 3 AM
	"cron": {
		"0 3 1 * *": [
			"hotel_management.hotel_management.doctype.owner_settlement.owner_settlement.auto_generate_monthly_settlements"
		]
	},
	
	# Alternative: Run daily check (more flexible)
	"daily": [
		"hotel_management.hotel_management.doctype.owner_settlement.owner_settlement.check_and_generate_settlements"
	],
	"hourly": [
		"hotel_management.hotel_management.channel_manager.channel_manager.sync_all_channels"
	]
}

# Installation hooks
after_install = "hotel_management.install.after_install"

# Permissions (Optional - can be defined here or in DocType)
# permission_query_conditions = {
# 	"Owner Settlement": "hotel_management.hotel_management.doctype.owner_settlement.owner_settlement.get_permission_query_conditions"
# }

# Boot Session (Optional - for loading custom data on login)
# boot_session = "hotel_management.boot.boot_session"

# Website context (Optional - for web pages)
# update_website_context = "hotel_management.utils.update_website_context"

# Jinja filters (Optional - custom template filters)
# jinja = {
# 	"methods": "hotel_management.utils.jinja_methods"
# }
# App JS
# ------
app_include_js = [
    "/assets/hotel_management/hotel_management/doctype/reservation/reservation_enhanced.js"
]