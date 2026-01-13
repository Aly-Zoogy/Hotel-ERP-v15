import frappe
from frappe.utils import getdate, date_diff, flt
from frappe import _

def get_dynamic_price(reservation, unit, check_in, check_out, base_rate):
	"""
	Calculates the final price per night based on various dynamic pricing rules.
	"""
	final_rate = flt(base_rate)
	
	# 1. Fetch all active pricing rules, sorted by priority
	rules = frappe.get_all("Hotel Pricing Rule", filters={"docstatus": 0}, order_by="priority desc")
	
	for rule_data in rules:
		rule = frappe.get_doc("Hotel Pricing Rule", rule_data.name)
		
		# Skip rules that don't apply to this rate plan or unit type (if specified)
		if rule.rate_plan and rule.rate_plan != reservation.rate_plan:
			continue
		
		unit_type = frappe.db.get_value("Property Unit", unit, "unit_type")
		if rule.unit_type and rule.unit_type != unit_type:
			continue
			
		applied = False
		
		# Identify if the rule applies
		if rule.apply_on == "Season":
			if is_date_in_season(check_in, rule.season):
				applied = True
				
		elif rule.apply_on == "Special Event":
			if is_date_in_special_event(check_in, rule.special_event):
				applied = True
				
		elif rule.apply_on == "Occupancy":
			occupancy = get_occupancy_percentage(unit_type, check_in)
			if flt(rule.min_occupancy) <= occupancy <= flt(rule.max_occupancy):
				applied = True
				
		elif rule.apply_on == "Early Bird":
			days_advance = date_diff(check_in, getdate(reservation.creation if not reservation.is_new() else frappe.utils.today()))
			if days_advance >= rule.min_days_advance:
				applied = True
				
		elif rule.apply_on == "Last Minute":
			days_advance = date_diff(check_in, getdate(reservation.creation if not reservation.is_new() else frappe.utils.today()))
			if days_advance <= rule.max_days_advance:
				applied = True
				
		elif rule.apply_on == "Length of Stay":
			nights = date_diff(check_out, check_in)
			if nights >= rule.min_stay:
				applied = True
		
		if applied:
			final_rate = apply_action(final_rate, rule.action, rule.value)
			# If we only want to apply the HIGHEST priority rule, we could break here.
			# But usually, rules are additive? The plan said "Priority-based single rule" initially.
			# Let's stick to single rule application for now as per plan.
			break 

	return final_rate

def is_date_in_season(date, season_name):
	season = frappe.get_doc("Hotel Season", season_name)
	return getdate(season.start_date) <= getdate(date) <= getdate(season.end_date)

def is_date_in_special_event(date, event_name):
	event = frappe.get_doc("Hotel Special Event", event_name)
	return getdate(event.start_date) <= getdate(date) <= getdate(event.end_date)

def get_occupancy_percentage(unit_type, date):
	"""
	Calculates occupancy for a specific unit type on a given date.
	"""
	total_units = frappe.db.count("Property Unit", filters={"unit_type": unit_type})
	if not total_units:
		return 0
		
	occupied_units = frappe.db.sql("""
		SELECT COUNT(ru.unit)
		FROM `tabReservation Unit` ru
		JOIN `tabReservation` r ON r.name = ru.parent
		JOIN `tabProperty Unit` pu ON pu.name = ru.unit
		WHERE pu.unit_type = %s
		AND r.docstatus = 1
		AND r.status IN ('Confirmed', 'Checked-In')
		AND %s BETWEEN ru.check_in AND ru.check_out
	""", (unit_type, date))[0][0]
	
	return (flt(occupied_units) / flt(total_units)) * 100

def apply_action(base, action, value):
	if action == "Discount Percentage":
		return base * (1 - flt(value) / 100)
	elif action == "Discount Amount":
		return base - flt(value)
	elif action == "Markup Percentage":
		return base * (1 + flt(value) / 100)
	elif action == "Markup Amount":
		return base + flt(value)
	elif action == "Set Fixed Price":
		return flt(value)
	return base
