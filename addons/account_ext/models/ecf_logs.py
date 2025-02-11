from odoo import models, fields

class ECFLogs(models.Model):
    _name = "ecf.logs"
    _description = "Logs for DGII Responses"
    _order = "create_date desc"

    account_move_id = fields.Many2one("account.move", string="Invoice", ondelete="cascade")
    track_id = fields.Char(string="Track ID")
    url = fields.Char(string="DGII URL")
    codigo_seguridad = fields.Char(string="Security Code")
    fecha_hora_firma = fields.Datetime(string="Signature Date")
    encf = fields.Char(string="ENCF")
    fecha_vencimiento_secuencia = fields.Date(string="Sequence Expiration Date")
    track_guid = fields.Char(string="Track GUID")
    response_id = fields.Integer(string="Response ID")
    encf_restantes = fields.Integer(string="Remaining ENCF")