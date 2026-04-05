# -*- coding: utf-8 -*-
# Copyright (c) 2026, VRPnext and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class HotelDeposit(Document):
	def on_submit(self):
		if self.status == "Pending":
			self.status = "Paid"
		
		# Update reservation payment summary if needed
		self.update_reservation()

	def on_cancel(self):
		self.update_reservation()

	def update_reservation(self):
		if self.reservation:
			from hotel_management.hotel_management.doctype.reservation.reservation import sync_reservation_payment
			sync_reservation_payment(self.reservation)
