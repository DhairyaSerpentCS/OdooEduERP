# See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StudentTransport(models.Model):
    _name = "student.transport"
    _description = "Transport Information"


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _description = "Driver Information"

    licence_no = fields.Char("License No", help="Enter License No.")
    is_driver = fields.Boolean("IS driver", help="Check if employee is driver")
    transport_vehicle = fields.One2many(
        "transport.vehicle",
        "driver_id",
        "Vehicles",
        help="Select transport vehicle",
    )

    @api.constrains("licence_no")
    def check_licence_number(self):
        """Constraint for unique licence number"""
        driver_rec = self.search(
            [("licence_no", "=", self.licence_no), ("id", "not in", self.ids)]
        )
        if driver_rec:
            raise ValidationError(
                _(
                    """
                        The licence number you have entered already exist.
                        Please enter different licence number!"""
                )
            )


class TransportPoint(models.Model):
    """for points on root."""

    _name = "transport.point"
    _description = "Transport Point Information"

    name = fields.Char(
        "Point Name", required=True, help="Transport point name"
    )
    amount = fields.Float("Amount", default=0.0, help="Enter amount here")

    @api.constrains("amount")
    def _check_point_amount(self):
        """Constraint for negative amount"""
        if self.amount < 0:
            raise ValidationError(_("""Amount cannot be negative value!"""))

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        """Inherited method to assign domain for transport participant"""
        if self._context.get("name"):
            transport_obj = self.env["student.transport"]
            point_ids = [
                point_id.id
                for point_id in transport_obj.browse(
                    self._context.get("name")
                ).trans_point_ids
            ]
            args.append(("id", "in", point_ids))
        return super(TransportPoint, self)._search(
            args=args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class TransportVehicle(models.Model):
    """for vehicle detail."""

    _name = "transport.vehicle"
    _rec_name = "vehicle"
    _description = "Transport vehicle Information"

    @api.depends("vehi_participants_ids")
    def _compute_participants(self):
        """Method to get number participant."""
        for rec in self:
            rec.participant = len(rec.vehi_participants_ids)

    driver_id = fields.Many2one(
        "hr.employee", "Driver Name", required=True, help="Enter Drive Name"
    )
    vehicle = fields.Char(
        "Vehicle No", required=True, help="Enter Vehicle No."
    )
    capacity = fields.Integer("Capacity", help="Enter capacity of vehicle")
    participant = fields.Integer(
        compute="_compute_participants",
        string="Total Participants",
        readonly=True,
        help="Students registered in root",
    )
    vehi_participants_ids = fields.Many2many(
        "transport.participant",
        "vehicle_participant_student_rel",
        "vehicle_id",
        "student_id",
        " vehicle Participants",
        help="Select vehicle participants",
    )

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        """Override method to get vehicles of selected transport root."""
        if self._context.get("name"):
            transport_obj = self.env["student.transport"]
            vehicle_ids = [
                std_id.id
                for std_id in transport_obj.browse(
                    self._context.get("name")
                ).trans_vehicle_ids
            ]
            args.append(("id", "in", vehicle_ids))
        return super(TransportVehicle, self)._search(
            args=args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class TransportParticipant(models.Model):
    """for participants."""

    _name = "transport.participant"
    _rec_name = "stu_pid_id"
    _description = "Transport Participant Information"

    name = fields.Many2one(
        "student.student",
        "Participant Name",
        readonly=True,
        required=True,
        help="Select student as transport participant",
    )
    amount = fields.Float("Amount", readonly=True, help="Enter amount")
    transport_id = fields.Many2one(
        "student.transport",
        "Transport Root",
        readonly=True,
        required=True,
        help="Select student transport",
    )
    stu_pid_id = fields.Char(
        "Personal Identification Number",
        required=True,
        help="Enter student PI No.",
    )
    tr_reg_date = fields.Date(
        "Transportation Registration Date", help="Start date of registration"
    )
    tr_end_date = fields.Date(
        "Registration End Date", help="End date of registration"
    )
    months = fields.Integer(
        "Registration For Months", help="Registration for months"
    )
    vehicle_id = fields.Many2one(
        "transport.vehicle", "Vehicle No", help="Enter vehicle no."
    )
    point_id = fields.Many2one(
        "transport.point", "Point Name", help="Name of point"
    )
    state = fields.Selection(
        [("running", "Running"), ("over", "Over")],
        "State",
        readonly=True,
        help="State of the transport participant",
    )
    active = fields.Boolean(
        "Active",
        default=True,
        help="""Marked transport
                            participant as active/deactive""",
    )

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        """Inherited method to get domain from student transportation"""
        if self._context.get("name"):
            student_obj = self.env["student.student"]
            student_rec = student_obj.browse(self._context.get("name"))
            for student_data in student_rec:
                transport_ids = [
                    transport_id.id
                    for transport_id in student_data.transport_ids
                ]
                args.append(("id", "in", transport_ids))
        return super(TransportParticipant, self)._search(
            args=args,
            offset=offset,
            limit=limit,
            count=count,
            access_rights_uid=access_rights_uid,
        )

    def set_over(self):
        """Method to change state to over"""
        self.state = "over"

    def unlink(self):
        """Inherited method to check state at record deletion"""
        for rec in self:
            if rec.state == "running":
                raise ValidationError(
                    _(
                        """
                            You cannot delete record in running state!."""
                    )
                )
        return super(TransportParticipant, self).unlink()


class StudentTransports(models.Model):
    """for root detail."""

    _name = "student.transport"
    _description = "Student Transport Information"

    @api.depends("trans_participants_ids")
    def _compute_total_participants(self):
        """Method to compute total participant"""
        for rec in self:
            rec.total_participantes = len(rec.trans_participants_ids)

    name = fields.Char(
        "Transport Root Name", required=True, help="Enter Transport Root Name"
    )
    start_date = fields.Date(
        "Start Date", required=True, help="Enter start date"
    )
    contact_per_id = fields.Many2one(
        "hr.employee", "Contact Person", help="Contact Person"
    )
    end_date = fields.Date("End Date", required=True, help="Enter end date")
    total_participantes = fields.Integer(
        compute="_compute_total_participants",
        method=True,
        string="Total Participants",
        readonly=True,
        help="Total participant",
    )
    trans_participants_ids = fields.Many2many(
        "transport.participant",
        "transport_participant_rel",
        "participant_id",
        "transport_id",
        "Participants",
        readonly=True,
        help="Enter participant",
    )
    trans_vehicle_ids = fields.Many2many(
        "transport.vehicle",
        "transport_vehicle_rel",
        "vehicle_id",
        "transport_id",
        "vehicles",
        help="Select transport vehicles",
    )
    trans_point_ids = fields.Many2many(
        "transport.point",
        "transport_point_rel",
        "point_id",
        "root_id",
        " Points",
        help="Select transport points",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("open", "Open"), ("close", "Close")],
        "State",
        readonly=True,
        default="draft",
        help="State of student transport",
    )

    def transport_open(self):
        """Method to change state open."""
        self.state = "open"

    def transport_close(self):
        """Method to change state to close."""
        self.state = "close"

    @api.model
    def participant_expire(self):
        """Schedular to change in participant state when registration date.

        is over.
        """
        current_date = fields.datetime.today()
        trans_parti_obj = self.env["transport.participant"]
        trans_parti_rec = trans_parti_obj.search(
            [("tr_end_date", "<", current_date)]
        )
        for partitcipants in trans_parti_rec:
            partitcipants.state = "over"

    @api.constrains("start_date", "end_date")
    def check_dates(self):
        """Constraint to check start-end date"""
        for rec in self:
            """Constraint ot check start/end date and duration"""
            delta = rec.end_date - rec.start_date
            if rec.start_date > rec.end_date:
                raise ValidationError(
                    _(
                        """
                                Start date should be less than end date!"""
                    )
                )
            if delta.days < 30:
                raise ValidationError(_("Enter duration of month!"))

    def unlink(self):
        """Inherited method to check state at record deletion"""
        for rec in self:
            if rec.state == "open":
                raise ValidationError(
                    _(
                        """
            You can delete record in draft state or cancel state only!"""
                    )
                )
        return super(StudentTransports, self).unlink()


class StudentStudent(models.Model):
    _inherit = "student.student"
    _description = "Student Information"

    transport_ids = fields.Many2many(
        "transport.participant",
        "std_transport",
        "trans_id",
        "stud_id",
        "Transport",
        help="Student transportation",
    )

    def set_alumni(self):
        """Override method to make record of student transport active false.

        when student is set to alumni state.
        """
        for rec in self:
            trans_student_rec = self.env["transport.participant"].search(
                [("name", "=", rec.id)]
            )
            trans_regi_rec = self.env["transport.registration"].search(
                [("part_name", "=", rec.id)]
            )
            if trans_regi_rec:
                trans_regi_rec.write({"state": "cancel"})
            if trans_student_rec:
                trans_student_rec.write({"active": False})
        return super(StudentStudent, self).set_alumni()


class TransportRegistration(models.Model):
    """for registration."""

    _name = "transport.registration"
    _description = "Transport Registration"

    @api.depends("state")
    def _compute_get_user_groups(self):
        """Method to compute transport user boolean field"""
        transport_user_group = self.env.ref(
            "school_transport.group_transportation_user"
        )
        grps = [group.id for group in self.env.user.groups_id]
        self.transport_user = False
        if transport_user_group.id in grps:
            self.transport_user = True

    @api.depends("m_amount", "for_month")
    def _compute_transport_fees(self):
        """Method to compute transport fees"""
        self.transport_fees = self.m_amount * self.for_month

    name = fields.Many2one(
        "student.transport",
        "Transport Root Name",
        domain=[("state", "=", "open")],
        required=True,
        help="Enter transport root name",
    )
    part_name = fields.Many2one(
        "student.student", "Student Name", required=True, help="Student Name"
    )
    reg_date = fields.Date(
        "Registration Date",
        readonly=True,
        help="Start Date of registration",
        default=fields.Date.context_today,
    )
    reg_end_date = fields.Date(
        "Registration End Date",
        readonly=True,
        help="Start Date of registration",
    )
    for_month = fields.Integer("Registration For Months")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirm"),
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("cancel", "Cancel"),
        ],
        "State",
        readonly=True,
        default="draft",
        help="""State of the transport
                             registration form""",
    )
    vehicle_id = fields.Many2one(
        "transport.vehicle",
        "Vehicle No",
        required=True,
        help="Enter transport vehicle",
    )
    point_id = fields.Many2one(
        "transport.point",
        "Point",
        required=True,
        help="Select transport point",
    )
    m_amount = fields.Float(
        "Monthly Amount", readonly=True, help="Enter monthly amount"
    )
    paid_amount = fields.Float("Paid Amount", help="Amount Paid")
    remain_amt = fields.Float("Due Amount", help="Amount Remaining")
    transport_fees = fields.Float(
        compute="_compute_transport_fees",
        string="Transport Fees",
        help="Transport fees",
    )
    amount = fields.Float("Final Amount", readonly=True, help="Final amount")
    count_inv = fields.Integer(
        "Invoice Count", compute="_compute_invoice", help="Total invoice"
    )
    transport_user = fields.Boolean(
        compute="_compute_get_user_groups",
        string="Transport user",
        help="""Activate/Deactivate as following
                                    user is transport user or not""",
    )

    @api.model
    def create(self, vals):
        """Inherited create method to call onchange methods"""
        ret_val = super(TransportRegistration, self).create(vals)
        if ret_val:
            ret_val.onchange_point_id()
            ret_val.onchange_for_month()
        return ret_val

    def unlink(self):
        """Inherited method to check state at record deletion"""
        for rec in self:
            if rec.state in ["confirm", "pending", "paid"]:
                raise ValidationError(
                    _(
                        """
        You can delete record in unconfirm state and cancel state only!"""
                    )
                )
        return super(TransportRegistration, self).unlink()

    def transport_fees_pay(self):
        """Method to generate invoice of participant."""
        invoice_obj = self.env["account.move"]
        for rec in self:
            rec.state = "pending"
            partner = rec.part_name and rec.part_name.partner_id
            vals = {
                "partner_id": partner.id,
                "move_type": "out_invoice",
                "transport_student_id": rec.id,
            }
            invoice = invoice_obj.create(vals)
            journal = invoice.journal_id
            acct_journal_id = journal.default_account_id.id
            account_view_id = self.env.ref("account.view_move_form")
            line_vals = {
                "name": "Transport Fees",
                "account_id": acct_journal_id,
                "quantity": rec.for_month,
                "price_unit": rec.m_amount,
            }
            invoice.write({"invoice_line_ids": [(0, 0, line_vals)]})
            return {
                "name": _("Pay Transport Fees"),
                "view_mode": "form",
                "res_model": "account.move",
                "view_id": account_view_id.id,
                "type": "ir.actions.act_window",
                "nodestroy": True,
                "target": "current",
                "res_id": invoice.id,
                "context": {},
            }

    def view_invoice(self):
        """Method to view invoice of participant."""
        invoice_obj = self.env["account.move"]
        for rec in self:
            invoices = invoice_obj.search(
                [("transport_student_id", "=", rec.id)]
            )
            action = rec.env.ref(
                "account.action_move_out_invoice_type"
            ).read()[0]
            if len(invoices) > 1:
                action["domain"] = [("id", "in", invoices.ids)]
            elif len(invoices) == 1:
                action["views"] = [
                    (rec.env.ref("account.view_move_form").id, "form")
                ]
                action["res_id"] = invoices.ids[0]
            else:
                action = {"type": "ir.actions.act_window_close"}
            return action

    def _compute_invoice(self):
        """Method to compute number of invoice of participant."""
        inv_obj = self.env["account.move"]
        for rec in self:
            rec.count_inv = inv_obj.search_count(
                [("transport_student_id", "=", rec.id)]
            )

    @api.onchange("point_id")
    def onchange_point_id(self):
        """Method to get amount of point selected."""
        self.m_amount = False
        if self.point_id:
            self.m_amount = self.point_id.amount or 0.0

    @api.onchange("for_month")
    def onchange_for_month(self):
        """Method to compute registration end date."""
        tr_start_date = fields.Date.today()
        tr_end_date = tr_start_date + relativedelta(months=self.for_month)
        self.reg_end_date = tr_end_date

    def trans_regi_cancel(self):
        """Method to set state to cancel."""
        self.state = "cancel"

    def trans_regi_confirm(self):
        """Method to confirm registration."""
        trans_obj = self.env["student.transport"]
        prt_obj = self.env["student.student"]
        stu_prt_obj = self.env["transport.participant"]
        vehi_obj = self.env["transport.vehicle"]
        for rec in self:
            # registration months must one or more then one
            if rec.for_month <= 0:
                raise UserError(
                    _(
                        """Error!
                    Registration months must be 1 or more then one month!"""
                    )
                )
            # First Check Is there vacancy or not
            person = int(rec.vehicle_id.participant) + 1
            if rec.vehicle_id.capacity < person:
                raise UserError(_("There is No More vacancy on this vehicle!"))

            rec.write({"state": "confirm", "remain_amt": rec.transport_fees})
            # calculate amount and Registration End date
            amount = rec.point_id.amount * rec.for_month
            tr_start_date = rec.reg_date
            ed_date = rec.name.end_date
            tr_end_date = tr_start_date + relativedelta(months=rec.for_month)
            if tr_end_date > ed_date:
                raise UserError(
                    _(
                        """
For this much Months Registration is not Possible because Root
end date is Early!"""
                    )
                )
            # make entry in Transport
            dict_prt = {
                "stu_pid_id": str(rec.part_name.pid),
                "amount": amount,
                "transport_id": rec.name.id,
                "tr_end_date": tr_end_date,
                "name": rec.part_name.id,
                "months": rec.for_month,
                "tr_reg_date": rec.reg_date,
                "point_id": rec.point_id.id,
                "state": "running",
                "vehicle_id": rec.vehicle_id.id,
            }
            temp = stu_prt_obj.sudo().create(dict_prt)
            # make entry in Transport vehicle.
            vehi_participants_list = []
            for prt in rec.vehicle_id.vehi_participants_ids:
                vehi_participants_list.append(prt.id)
            flag = True
            for prt in vehi_participants_list:
                data = stu_prt_obj.browse(prt)
                if data.name.id == rec.part_name.id:
                    flag = False
            if flag:
                vehi_participants_list.append(temp.id)
            vehicle_rec = vehi_obj.browse(rec.vehicle_id.id)
            vehicle_rec.sudo().write(
                {"vehi_participants_ids": [(6, 0, vehi_participants_list)]}
            )
            # make entry in student.
            transport_list = []
            for root in rec.part_name.transport_ids:
                transport_list.append(root.id)
            transport_list.append(temp.id)
            part_name_rec = prt_obj.browse(rec.part_name.id)
            part_name_rec.sudo().write(
                {"transport_ids": [(6, 0, transport_list)]}
            )
            # make entry in transport.
            trans_participants_list = []
            for prt in rec.name.trans_participants_ids:
                trans_participants_list.append(prt.id)
            trans_participants_list.append(temp.id)
            stu_tran_rec = trans_obj.browse(rec.name.id)
            stu_tran_rec.sudo().write(
                {"trans_participants_ids": [(6, 0, trans_participants_list)]}
            )


class AccountInvoice(models.Model):
    _inherit = "account.move"

    transport_student_id = fields.Many2one(
        "transport.registration",
        string="Transport Student",
        help="Transport records",
    )


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        """Method to compute paid amount and due amount."""
        res = super(AccountPayment, self).action_post()
        for rec in self:
            invoice = rec.move_id
            vals = {}
            if (
                invoice.transport_student_id
                and invoice.payment_state == "paid"
            ):
                fees_payment = (
                    invoice.transport_student_id.paid_amount + rec.amount
                )
                vals.update(
                    {
                        "state": "paid",
                        "paid_amount": fees_payment,
                        "remain_amt": 0.0,
                    }
                )
            elif (
                invoice.transport_student_id
                and invoice.payment_state == "not_paid"
            ):
                fees_payment = (
                    invoice.transport_student_id.paid_amount + rec.amount
                )
                vals.update(
                    {
                        "state": "pending",
                        "paid_amount": fees_payment,
                        "remain_amt": invoice.amount_residual,
                    }
                )
            invoice.transport_student_id.write(vals)
        return res
