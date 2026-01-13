from frappe.model.document import Document
import frappe
from frappe import _

class HotelSpecialEvent(Document):
	def validate(self):
		if self.start_date > self.end_date:
			frappe.throw(_("Start Date cannot be after End Date"))
