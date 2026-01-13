import frappe
from frappe.model.document import Document
from frappe import _

class HotelSeason(Document):
	def validate(self):
		if self.start_date > self.end_date:
			frappe.throw(_("Start Date cannot be after End Date"))
		
		# Check for overlapping seasons
		overlapping_season = frappe.db.sql("""
			select name from `tabHotel Season`
			where name != %s
			and (
				(%s between start_date and end_date)
				or (%s between start_date and end_date)
				or (start_date between %s and %s)
			)
		""", (self.name, self.start_date, self.end_date, self.start_date, self.end_date))
		
		if overlapping_season:
			frappe.throw(_("Season overlaps with {0}").format(overlapping_season[0][0]))
