// Copyright (c) 2025, VRPnext and contributors
// For license information, please see license.txt

frappe.ui.form.on('Reservation', {
	refresh: function (frm) {
		// Set status indicator
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, get_status_color(frm.doc.status));
		}

		// Add workflow buttons
		if (frm.doc.docstatus === 1) {
			if (frm.doc.status === "Confirmed") {
				frm.add_custom_button(__('Check In'), function () {
					// ✅ SOLUTION: Call whitelisted function with reservation name
					frappe.call({
						method: 'hotel_management.hotel_management.doctype.reservation.reservation.check_in_reservation',
						args: {
							reservation_name: frm.doc.name
						},
						callback: function (r) {
							if (r.message && r.message.success) {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'green'
								}, 5);
								frm.reload_doc();
							}
						}
					});
				}).addClass('btn-primary');
			}

			if (frm.doc.status === "Checked-In") {
				frm.add_custom_button(__('Check Out'), function () {
					// ✅ SOLUTION: Call whitelisted function with reservation name
					frappe.call({
						method: 'hotel_management.hotel_management.doctype.reservation.reservation.check_out_reservation',
						args: {
							reservation_name: frm.doc.name
						},
						callback: function (r) {
							if (r.message && r.message.success) {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'green'
								}, 5);
								frm.reload_doc();
							}
						}
					});
				}).addClass('btn-primary');
			}
		}

		// View linked invoice
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__('View Invoice'), function () {
				frappe.set_route('Form', 'Sales Invoice', frm.doc.sales_invoice);
			});
		}

		// View customer
		if (frm.doc.customer) {
			frm.add_custom_button(__('View Customer'), function () {
				frappe.set_route('Form', 'Customer', frm.doc.customer);
			});
		}

		// Request Deposit Button
		if (frm.doc.docstatus < 2 && (frm.doc.status === "Draft" || frm.doc.status === "Confirmed")) {
			frm.add_custom_button(__('Request Deposit'), function () {
				frm.trigger('create_deposit_dialog');
			}, __('Actions'));
		}

		// Sync Payment Button
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Sync Payment'), function () {
				frappe.call({
					method: 'hotel_management.hotel_management.doctype.reservation.reservation.sync_reservation_payment',
					args: {
						reservation_name: frm.doc.name
					},
					callback: function (r) {
						if (r.message) {
							frm.reload_doc();
							frappe.show_alert({ message: __('Payment synced'), indicator: 'green' });
						}
					}
				});
			}, __('Actions'));
		}

		// Extend Stay Button
		if (frm.doc.status === "Checked-In") {
			frm.add_custom_button(__('Extend Stay'), function () {
				frm.trigger('extend_stay_dialog');
			}, __('Actions'));

			frm.add_custom_button(__('Change Room'), function () {
				frm.trigger('change_room_dialog');
			}, __('Actions'));
		}
	},

	extend_stay_dialog: function (frm) {
		let d = new frappe.ui.Dialog({
			title: __('Extend Stay'),
			fields: [
				{
					label: __('New Check-out Date'),
					fieldname: 'new_checkout',
					fieldtype: 'Date',
					default: frappe.datetime.add_days(frm.doc.check_out, 1),
					reqd: 1
				}
			],
			primary_action_label: __('Extend'),
			primary_action(values) {
				frappe.call({
					method: 'hotel_management.hotel_management.doctype.reservation.reservation.extend_stay',
					args: {
						reservation_name: frm.doc.name,
						new_checkout: values.new_checkout
					},
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.show_alert({ message: r.message.message, indicator: 'green' });
							d.hide();
							frm.reload_doc();
						}
					}
				});
			}
		});
		d.show();
	},

	change_room_dialog: function (frm) {
		// First, get currently occupied unit to allow user to pick which one to change (if multiple)
		const units = frm.doc.units_reserved.map(u => u.unit);

		let d = new frappe.ui.Dialog({
			title: __('Change Room'),
			fields: [
				{
					label: __('Current Room'),
					fieldname: 'old_unit',
					fieldtype: 'Select',
					options: units,
					default: units[0],
					reqd: 1
				},
				{
					label: __('New Room'),
					fieldname: 'new_unit',
					fieldtype: 'Link',
					options: 'Property Unit',
					get_query: function () {
						return {
							filters: {
								'status': 'Available'
							}
						};
					},
					reqd: 1
				},
				{
					label: __('Reason for Change'),
					fieldname: 'reason',
					fieldtype: 'Small Text',
					reqd: 1
				}
			],
			primary_action_label: __('Switch Room'),
			primary_action(values) {
				frappe.call({
					method: 'hotel_management.hotel_management.doctype.reservation.reservation.change_room',
					args: {
						reservation_name: frm.doc.name,
						old_unit: values.old_unit,
						new_unit: values.new_unit,
						reason: values.reason
					},
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.show_alert({ message: r.message.message, indicator: 'green' });
							d.hide();
							frm.reload_doc();
						}
					}
				});
			}
		});
		d.show();
	},

	create_deposit_dialog: function (frm) {
		// Fetch Hotel Settings
		frappe.db.get_single_value('Hotel Settings', 'deposit_percentage').then(pct => {
			const default_pct = pct || 25;
			const suggested_amount = flt(frm.doc.total_amount) * (default_pct / 100);

			let d = new frappe.ui.Dialog({
				title: __('Request Deposit'),
				fields: [
					{
						label: __('Deposit Amount'),
						fieldname: 'amount',
						fieldtype: 'Currency',
						default: suggested_amount,
						reqd: 1
					},
					{
						label: __('Payment Method'),
						fieldname: 'method',
						fieldtype: 'Select',
						options: 'Cash\nCard\nBank Transfer\nOnline',
						default: 'Online'
					},
					{
						label: __('Reference'),
						fieldname: 'reference',
						fieldtype: 'Data'
					}
				],
				primary_action_label: __('Create Deposit'),
				primary_action(values) {
					frappe.call({
						method: 'frappe.client.insert',
						args: {
							doc: {
								doctype: 'Hotel Deposit',
								reservation: frm.doc.name,
								deposit_amount: values.amount,
								payment_method: values.method,
								payment_reference: values.reference,
								status: 'Pending'
							}
						},
						callback: function (r) {
							if (r.message) {
								frappe.show_alert({ message: __('Deposit Request Created'), indicator: 'green' });
								d.hide();
								frappe.set_route('Form', 'Hotel Deposit', r.message.name);
							}
						}
					});
				}
			});
			d.show();
		});
	},

	check_in: function (frm) {
		// Auto-calculate nights
		if (frm.doc.check_in && frm.doc.check_out) {
			frm.trigger('calculate_nights');
		}
	},

	check_out: function (frm) {
		// Auto-calculate nights
		if (frm.doc.check_in && frm.doc.check_out) {
			frm.trigger('calculate_nights');
		}
	},

	calculate_nights: function (frm) {
		if (frm.doc.check_in && frm.doc.check_out) {
			const nights = frappe.datetime.get_day_diff(frm.doc.check_out, frm.doc.check_in);
			frm.set_value('nights', nights);

			// Update child table nights
			if (frm.doc.units_reserved) {
				frm.doc.units_reserved.forEach(function (row) {
					frappe.model.set_value(row.doctype, row.name, 'check_in', frm.doc.check_in);
					frappe.model.set_value(row.doctype, row.name, 'check_out', frm.doc.check_out);
					frappe.model.set_value(row.doctype, row.name, 'qty_nights', nights);
				});
			}
		}
	},

	primary_guest: function (frm) {
		// Auto-fetch customer from guest
		if (frm.doc.primary_guest) {
			frappe.db.get_value('Guest', frm.doc.primary_guest, 'customer', function (r) {
				if (r && r.customer) {
					frm.set_value('customer', r.customer);
				}
			});

			// Auto-add to guests table if not exists
			if (frm.doc.guests) {
				const guest_exists = frm.doc.guests.some(g => g.guest === frm.doc.primary_guest);
				if (!guest_exists) {
					const row = frm.add_child('guests');
					frappe.model.set_value(row.doctype, row.name, 'guest', frm.doc.primary_guest);
					frappe.model.set_value(row.doctype, row.name, 'relation', 'Self');
					frappe.model.set_value(row.doctype, row.name, 'is_primary', 1);
					frm.refresh_field('guests');
				}
			}
		}
	}
});

// Reservation Unit child table
frappe.ui.form.on('Reservation Unit', {
	unit: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.unit) {
			// Fetch rate from Property Unit
			frappe.db.get_value('Property Unit', row.unit, 'rate_per_night', function (r) {
				if (r && r.rate_per_night) {
					frappe.model.set_value(cdt, cdn, 'rate_per_night', r.rate_per_night);
				}
			});

			// Set dates from parent
			if (frm.doc.check_in) {
				frappe.model.set_value(cdt, cdn, 'check_in', frm.doc.check_in);
			}
			if (frm.doc.check_out) {
				frappe.model.set_value(cdt, cdn, 'check_out', frm.doc.check_out);
			}
			if (frm.doc.nights) {
				frappe.model.set_value(cdt, cdn, 'qty_nights', frm.doc.nights);
			}
		}
	},

	rate_per_night: function (frm, cdt, cdn) {
		calculate_unit_total(frm, cdt, cdn);
	},

	qty_nights: function (frm, cdt, cdn) {
		calculate_unit_total(frm, cdt, cdn);
	},

	units_reserved_remove: function (frm) {
		calculate_reservation_total(frm);
	}
});

// Reservation Service child table
frappe.ui.form.on('Reservation Service', {
	service_item: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.service_item) {
			// Fetch item rate and description
			frappe.db.get_value('Item', row.service_item, ['standard_rate', 'description'], function (r) {
				if (r) {
					if (r.standard_rate) {
						frappe.model.set_value(cdt, cdn, 'rate', r.standard_rate);
					}
					if (r.description) {
						frappe.model.set_value(cdt, cdn, 'description', r.description);
					}
				}
			});
		}
	},

	qty: function (frm, cdt, cdn) {
		calculate_service_amount(frm, cdt, cdn);
	},

	rate: function (frm, cdt, cdn) {
		calculate_service_amount(frm, cdt, cdn);
	},

	services_consumed_remove: function (frm) {
		calculate_reservation_total(frm);
	}
});

function calculate_unit_total(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (row.rate_per_night && row.qty_nights) {
		const total = row.rate_per_night * row.qty_nights;
		frappe.model.set_value(cdt, cdn, 'total_amount', total);
		calculate_reservation_total(frm);
	}
}

function calculate_service_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (row.qty && row.rate) {
		const amount = row.qty * row.rate;
		frappe.model.set_value(cdt, cdn, 'amount', amount);
		calculate_reservation_total(frm);
	}
}

function calculate_reservation_total(frm) {
	let total = 0;

	// Sum units
	if (frm.doc.units_reserved) {
		frm.doc.units_reserved.forEach(function (row) {
			if (row.total_amount) {
				total += row.total_amount;
			}
		});
	}

	// Sum services
	if (frm.doc.services_consumed) {
		frm.doc.services_consumed.forEach(function (row) {
			if (row.amount) {
				total += row.amount;
			}
		});
	}

	frm.set_value('total_amount', total);
}

function get_status_color(status) {
	const colors = {
		'Draft': 'gray',
		'Confirmed': 'blue',
		'Checked-In': 'orange',
		'Checked-Out': 'green',
		'Cancelled': 'red'
	};
	return colors[status] || 'gray';
}