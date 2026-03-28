Produbanco Check Layout (Odoo 17 Community)
================================================

This addon adds a cheque layout option for Ecuador / Produbanco using Odoo's `account_check_printing`.

1) Copy the folder `produbanco_check_printing` into your custom addons path.
2) Restart Odoo and update apps list.
3) Install the addon.
4) Replace `static/src/img/produbanco_check_bg.png` with your real cheque background/template.
5) In Settings -> Companies -> (your company) choose "Produbanco (EC)" as cheque layout.
6) Fine-tune alignment using company fields:
   - Produbanco Check X Offset (mm)
   - Produbanco Check Y Offset (mm)

NOTE:
- Paper size in report/report.xml is a placeholder (210x102mm). Adjust to your real cheque size.
