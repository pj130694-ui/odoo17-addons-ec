"""
Extend the account.payment model with helper methods for check printing in Spanish.

These helpers are used by the Trionica and Pacífico cheque layouts to avoid
complex logic in QWeb templates (which cannot call built-in Python functions).
They provide formatted numeric amounts, cents as two-digit strings,
and amounts in words with optional decorative suffixes.
"""

import re
import unicodedata

from num2words import num2words
from odoo import models
from odoo.tools import formatLang


class AccountPayment(models.Model):
    """Inherit account.payment to expose helper methods for check layouts."""

    _inherit = "account.payment"

    # -------------------------------------------------------------------------
    # Numeric formatting helpers
    # -------------------------------------------------------------------------
    def check_amount_num_es(self):
        """Return the amount formatted with two decimals using Spanish locale."""
        self.ensure_one()
        return formatLang(self.env, self.amount, digits=2)

    def check_amount_cents(self):
        """Return the cents part of the amount as a two digit string (00..99)."""
        self.ensure_one()

        amount_float = abs(self.amount or 0.0)

        total_cents = int(round(amount_float * 100))
        cents = total_cents % 100

        if cents < 0:
            cents = 0
        if cents > 99:
            cents = 99

        return f"{cents:02d}"

    # -------------------------------------------------------------------------
    # Amount in words helpers
    # -------------------------------------------------------------------------
    def check_amount_words_es(self):
        """
        Return ONLY the integer part of the amount in Spanish words + DOLAR/DOLARES.
        - No cents in words (cents are added separately as XX/100)
        - No English tokens
        - No tildes/diacritics (avoid PDF encoding issues)
        """
        self.ensure_one()

        amount = abs(self.amount or 0.0)
        units = int(amount)

        words = (num2words(units, lang="es") or "").lower().strip()

        # Spanish grammar adjustments before currency word
        words = re.sub(r"veintiuno\b", "veintiun", words)
        words = re.sub(r" y uno\b", " y un", words)
        words = re.sub(r"\buno\b", "un", words)

        # Remove accents/diacritics
        words = "".join(
            ch for ch in unicodedata.normalize("NFD", words)
            if unicodedata.category(ch) != "Mn"
        )

        currency_word = "DOLAR" if units == 1 else "DOLARES"
        return f"{words.upper()} {currency_word}"

    def check_trionica_amount_words_line(self):
        """Compose the amount in words line for the Trionica layout."""
        self.ensure_one()
        words = self.check_amount_words_es()
        cents = self.check_amount_cents()
        return f"{words} {cents}/100 ***********"

    def check_pacifico_amount_words_line(self):
        """Compose the amount in words line for the Pacífico layout."""
        self.ensure_one()
        words = self.check_amount_words_es()
        cents = self.check_amount_cents()
        return f"{words} {cents}/100"

    # -------------------------------------------------------------------------
    # Beneficiary helpers
    # -------------------------------------------------------------------------
    def check_beneficiary_name(self):
        """Return beneficiary name or fallback to partner name."""
        self.ensure_one()
        val = getattr(self, "beneficiary", False)

        if not val:
            return self.partner_id.name or ""

        if hasattr(val, "name"):
            return val.name or (self.partner_id.name or "")

        return str(val)

    def check_beneficiary_name_upper(self):
        """Uppercase beneficiary name for QWeb templates."""
        self.ensure_one()
        return (self.check_beneficiary_name() or "").upper()

    # -------------------------------------------------------------------------
    # Date helper (PDC Due Date)
    # -------------------------------------------------------------------------
    def _get_pdc_due_date(self):
        """
        Return Due Date from PDC wizard linked to this payment.
        Your PDC module uses: pdc.wizard.payment_id -> account.payment
        """
        self.ensure_one()

        # If account.payment has due_date, use it
        if "due_date" in self._fields:
            dt = getattr(self, "due_date", False)
            if dt:
                return dt

        # Canonical: search PDC wizard by payment_id
        try:
            wiz = self.env["pdc.wizard"].sudo().search(
                [("payment_id", "=", self.id)],
                order="id desc",
                limit=1,
            )
            if wiz and getattr(wiz, "due_date", False):
                return wiz.due_date
        except Exception:
            pass

        return False

    def check_payment_date_str(self):
        """Return formatted date string 'YYYY / MM / DD' using PDC Due Date first."""
        self.ensure_one()

        dt = (
            self._get_pdc_due_date()
            or getattr(self, "date_release", False)
            or getattr(self, "payment_date", False)
            or self.date
        )

        if not dt:
            return ""

        if isinstance(dt, str):
            try:
                from datetime import datetime as dtlib
                dt_obj = dtlib.strptime(dt, "%Y-%m-%d")
            except Exception:
                return dt
        else:
            dt_obj = dt

        try:
            return dt_obj.strftime("%Y / %m / %d")
        except Exception:
            return str(dt)