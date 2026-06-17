# AntMed CRM — API package (in-place trong app `crm`).
#
# Đường gọi endpoint: crm.api.antmed.<module>.<fn>
#   vd: crm.api.antmed.health.ping
#
# Quy ước (Frappe-standard): @frappe.whitelist(methods=[...]) tường minh verb,
# trả RAW dict/list (KHÔNG envelope _ok/_err, KHÔNG MSG.*); lỗi nghiệp vụ =
# frappe.throw(_("BR-XX: <thông điệp tiếng Việt>")). Hàm phải type-annotate
# (crm/hooks.py: require_type_annotated_api_methods = True).
