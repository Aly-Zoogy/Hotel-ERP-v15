import frappe
from frappe.utils import today, add_days, getdate
import unittest
from hotel_management.hotel_management.pricing import get_dynamic_price

class TestDynamicPricing(unittest.TestCase):
	def setUp(self):
		self.cleanup()
		self.create_test_data()

	def cleanup(self):
		frappe.db.sql("delete from `tabHotel Pricing Rule`")
		frappe.db.sql("delete from `tabHotel Season`")
		frappe.db.sql("delete from `tabHotel Special Event`")
		# We don't delete Reservations etc. to avoid breaking other tests, 
		# but since we use unique names or rollback it should be fine.

	def create_test_data(self):
		# Create Property
		if not frappe.db.exists("Property", "TEST-Hotel-001"):
			frappe.get_doc({
				"doctype": "Property",
				"property_name": "Test Hotel",
				"name": "TEST-Hotel-001"
			}).insert(ignore_permissions=True)

		# Create Unit Type
		if not frappe.db.exists("Unit Type", "Deluxe"):
			frappe.get_doc({
				"doctype": "Unit Type",
				"unit_type_name": "Deluxe",
				"property_type": "Hotel"
			}).insert(ignore_permissions=True)

		# Create Unit
		if not frappe.db.exists("Property Unit", "D-101"):
			frappe.get_doc({
				"doctype": "Property Unit",
				"unit_id": "D-101",
				"property": "TEST-Hotel-001",
				"unit_type": "Deluxe",
				"status": "Available",
				"rate_per_night": 200
			}).insert(ignore_permissions=True)
		
		# Create Customer Group
		if not frappe.db.exists("Customer Group", "Individual"):
			frappe.get_doc({
				"doctype": "Customer Group",
				"customer_group_name": "Individual",
				"is_group": 0
			}).insert(ignore_permissions=True)
		
		# Create Territory
		if not frappe.db.exists("Territory", "All Territories"):
			frappe.get_doc({
				"doctype": "Territory",
				"territory_name": "All Territories",
				"is_group": 0
			}).insert(ignore_permissions=True)

		# Create Customer
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "Test Pricing Customer",
			"customer_type": "Individual",
			"customer_group": "Individual",
			"territory": "All Territories"
		}).insert(ignore_if_duplicate=True)
		self.customer = customer.name
		
		# Create Guest
		guest = frappe.get_doc({
			"doctype": "Guest",
			"guest_name": "Ahmed Test Pricing",
			"phone": "99988877766",
			"email": "ahmed@pricing.com",
			"customer": self.customer
		}).insert(ignore_if_duplicate=True)
		self.guest = guest.name

	def test_season_pricing(self):
		# 1. Create Season
		season = frappe.get_doc({
			"doctype": "Hotel Season",
			"season_name": "Summer 2026",
			"season_type": "High",
			"start_date": "2026-06-01",
			"end_date": "2026-08-31"
		}).insert()

		# 2. Create Pricing Rule
		rule = frappe.get_doc({
			"doctype": "Hotel Pricing Rule",
			"rule_name": "Summer High Season Markup",
			"apply_on": "Season",
			"season": "Summer 2026",
			"action": "Markup Percentage",
			"value": 20,
			"priority": 10
		}).insert()

		# 3. Test logic directly
		check_in = "2026-07-01"
		check_out = "2026-07-05"
		base_rate = 200
		
		# Mocking reservation object enough for the function
		reservation = frappe._dict({
			"rate_plan": None,
			"is_new": lambda: True
		})
		
		final_rate = get_dynamic_price(reservation, "D-101", check_in, check_out, base_rate)
		
		# Calculation: 200 * 1.2 = 240
		self.assertEqual(final_rate, 240)

	def test_occupancy_pricing(self):
		# 1. Create Pricing Rule for High Occupancy
		rule = frappe.get_doc({
			"doctype": "Hotel Pricing Rule",
			"rule_name": "High Occupancy Markup",
			"apply_on": "Occupancy",
			"min_occupancy": 80,
			"max_occupancy": 100,
			"unit_type": "Deluxe",
			"action": "Markup Amount",
			"value": 50,
			"priority": 20
		}).insert()

		# We need to simulate occupancy. 
		# For simplicity, since the function uses DB queries, we would need to insert reservations.
		# Instead, let's just verify the rule selects correctly if we mock get_occupancy_percentage.
		
		from hotel_management.hotel_management import pricing
		original_get_occupancy = pricing.get_occupancy_percentage
		pricing.get_occupancy_percentage = lambda ut, date: 90
		
		try:
			reservation = frappe._dict({"rate_plan": None, "is_new": lambda: True})
			final_rate = get_dynamic_price(reservation, "D-101", today(), add_days(today(), 1), 200)
			self.assertEqual(final_rate, 250)
		finally:
			pricing.get_occupancy_percentage = original_get_occupancy

	def test_reservation_integration(self):
		# 1. Create Season and Rule
		frappe.get_doc({
			"doctype": "Hotel Season",
			"season_name": "Summer 2026",
			"season_type": "High",
			"start_date": "2026-06-01",
			"end_date": "2026-08-31"
		}).insert()

		frappe.get_doc({
			"doctype": "Hotel Pricing Rule",
			"rule_name": "Summer High Season Markup",
			"apply_on": "Season",
			"season": "Summer 2026",
			"action": "Markup Percentage",
			"value": 20,
			"priority": 10
		}).insert()

		# 2. Create Reservation
		res = frappe.get_doc({
			"doctype": "Reservation",
			"customer": self.customer,
			"primary_guest": self.guest,
			"check_in": "2026-07-01",
			"check_out": "2026-07-05",
			"units_reserved": [{
				"unit": "D-101",
				"check_in": "2026-07-01",
				"check_out": "2026-07-05",
				"rate_per_night": 0 # Should be auto-filled
			}]
		})

		res.insert()
		
		# Verify the rate in the child table
		self.assertEqual(res.units_reserved[0].rate_per_night, 240)
		self.assertEqual(res.total_amount, 240 * 4)

	def tearDown(self):
		frappe.db.rollback()
