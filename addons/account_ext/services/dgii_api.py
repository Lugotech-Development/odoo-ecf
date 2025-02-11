import requests
import logging

_logger = logging.getLogger(__name__)

DGII_API_URL = "https://lab-encf.azurewebsites.net/api/Emision/FacturasElectronicasv4"

def send_invoice_to_dgii(invoice_json):
    try:
        headers = {
            'x-api-key': '6613a68eaf997027c794ab7a2a9d6b869283863ae1a27ad38a40bc636d7bae56'
        }
        response = requests.post(DGII_API_URL, headers=headers, json=invoice_json, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        _logger.error(f"Error sending invoice to DGII: {e}")
        return {"status": "error", "message": str(e)}