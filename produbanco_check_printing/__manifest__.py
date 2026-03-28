{
    "name": "Produbanco Cheque Layout (account_check_printing)",
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "summary": "Cheque printing layout for Produbanco (Ecuador) using account_check_printing",
    "depends": ["account_check_printing"],
    "data": [
        # Core report definitions and paper format
        "report/report.xml",
        # Legacy Produbanco layout (enhanced for Spanish language)
        "report/produbanco_check.xml",
        # Additional cheque layouts for other Ecuadorian banks
        "report/trionica_check.xml",
        "report/pacifico_check.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
