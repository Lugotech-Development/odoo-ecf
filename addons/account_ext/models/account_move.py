from odoo.addons.account_ext.services.dgii_api import send_invoice_to_dgii
from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import logging
import uuid
from datetime import datetime
import pytz

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    encf_type = fields.Selection(
        selection=[
            ('E32', 'Factura de Consumo Electrónica'),
            ('E31', 'Factura de Crédito Fiscal Electrónica'),
            ('E44', 'Comprobante Electrónico para Regímenes Especiales'),
            ('E45', 'Comprobante Electrónico Gubernamental')
        ],
        string="Tipo de NCF",
    )

    is_confirm = fields.Boolean(string="Confirmed in DGII", default=False)

    def action_post(self):
        res = super(AccountMove, self).action_post()

        _logger.info(f"Invoice {self.name} confirmed, preparing JSON for DGII...")
        dgii_json_data = self.prepare_dgii_json()
        _logger.info(f"JSON sent to DGII: {json.dumps(dgii_json_data, indent=4, default=str)}")

        response = send_invoice_to_dgii(dgii_json_data)
        _logger.info(f"JSON response from DGII: {json.dumps(response, indent=4, default=str)}")

        # If we get a trackId, assume a valid response was returned
        if response.get("trackId"):
            self.save_dgii_response(response)

        self.is_confirm = True
        return res

    def prepare_dgii_json(self):
        self.ensure_one()

        company = self.company_id
        customer = self.partner_id
        indicador_monto_gravado = 1 if any(line.tax_ids for line in self.invoice_line_ids) else 0
        local_tz = pytz.timezone(self.env.user.tz or 'America/Santo_Domingo')

        fecha_emision = self.invoice_date and local_tz.localize(datetime.combine(self.invoice_date, datetime.min.time()))
        fecha_limite_pago = self.invoice_date_due and local_tz.localize(datetime.combine(self.invoice_date_due, datetime.min.time()))

        dgii_json = {
            "ipPrivada": "",
            "macAddress": "",
            "pcUsada": "",
            "merchantId": 6,
            "branchId": 2,
            "tipoeCF": self.encf_type.lstrip('E') if self.encf_type else None,
            "indicadorMontoGravado": indicador_monto_gravado,
            "eNCF": None,
            "tipoIngresos": "01",
            "tipoPago": 1 if self.invoice_payment_term_id and self.invoice_payment_term_id.id == 1 else 2,
            "fechaLimitePago": fecha_limite_pago.isoformat() if fecha_limite_pago else None,
            "rncEmisor": company.vat or None,
            "razonSocialEmisor": company.name[:150],
            "direccionEmisor": company.street[:100] if company.street else "",
            "fechaEmision": fecha_emision.isoformat() if fecha_emision else None,
            "rncComprador": customer.vat if self.amount_total > 250000 else None,
            "montoTotal": self.amount_total,
            "montoGravadoI1": sum(line.price_subtotal for line in self.invoice_line_ids if line.tax_ids),
            "montoGravadoTotal": sum(line.price_subtotal for line in self.invoice_line_ids),
            "trackGuid": str(uuid.uuid4()),
            "items": [
                {
                    "numeroLinea": index + 1,
                    "IndicadorFacturacion": 1,
                    "nombreItem": line.product_id.name if line.product_id else "N/A",
                    "IndicadorBienoServicio": 1 if line.product_id and line.product_id.type in ["product", "consu"] else 2,
                    "cantidadItem": line.quantity,
                    "precioUnitarioItem": line.price_unit,
                    "descuentoMonto": line.discount or 0.0,
                    "subDescuento": [{
                        "tipoSubDescuento": "%" if line.discount else "$",
                        "subDescuentoPorcentaje": line.discount if line.discount else 0.0,
                        "montoSubDescuento": (
                            line.price_unit * line.quantity * (line.discount / 100)) if line.discount else 0.0
                    }] if line.discount else [],
                    "montoItbisItem": sum(tax.amount for tax in line.tax_ids) if line.tax_ids else 0.0,
                    "montoItem": line.price_subtotal
                }
                for index, line in enumerate(self.invoice_line_ids)
            ]
        }
        return dgii_json

    def save_dgii_response(self, response_data):
        """Save the DGII response in the ECF Logs model."""
        try:
            # Convert the 'fechaHoraFirma' string to a datetime object.
            fecha_hora_firma = response_data.get("fechaHoraFirma")
            if fecha_hora_firma:
                # Slice the string to remove fractional seconds and timezone information if needed.
                # For example: "2025-02-10T16:25:17.7022719-04:00" -> "2025-02-10T16:25:17"
                fecha_hora_firma = datetime.strptime(fecha_hora_firma[:19], "%Y-%m-%dT%H:%M:%S")

            self.env["ecf.logs"].sudo().create({
                "account_move_id": self.id,
                "track_id": response_data.get("trackId"),
                "url": response_data.get("url"),
                "codigo_seguridad": response_data.get("codigoSeguridad"),
                "fecha_hora_firma": fecha_hora_firma,
                "encf": response_data.get("encf"),
                "fecha_vencimiento_secuencia": response_data.get("fechaVencimientoSecuencia"),
                "track_guid": response_data.get("trackGuid"),
                "response_id": response_data.get("id"),
                "encf_restantes": response_data.get("encfRestantes"),
            })
            _logger.info(f"Saved DGII response for Invoice {self.name}")
        except Exception as e:
            _logger.error(f"Error saving DGII response: {e}")
            raise UserError(f"Error saving DGII response: {str(e)}")