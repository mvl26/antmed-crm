# Backend Completion Plan — AntMed CRM (M03–M14)

Spec source: `docs/antmed_dev/modules/m0X_*.md` (authoritative BE design). Engine: Frappe v15, native-lite (no ERPNext), `AntMed `-prefix doctypes, module `AntMed`, API `antmed_crm.api.antmed.<module>.<fn>` (RAW dict/list, `count==rows`), Role VI. Test site `miyano`.

## Execution rules (for `/build auto`)
- One thin slice = one task = RED→GREEN→full-regression→commit. Stage ONLY that slice's files (FE factory is concurrently committing — never `git add -A`; don't touch `tasks/plan.md`, `frontend/`, FE assets, `docs/`).
- **[AUTO]** waves run without stopping between tasks. **[STOP]** modules pause for explicit user sign-off before the first task (auth/permission/2FA/secrets/payments/AR-block — not safely `git revert`-able).
- Defer BR-13 data-scope + BR-10 audit + BR-12 2FA to M14 (keep `count==rows` now). Workflow `workflow_state_field = "status"` convention.

## Already done (BE)
- M01: AntMed Hospital/Doctor + customer API. M02: Contract/Quota + enforce (contract_hooks BR-01/02/06) + read APIs (list/get/health/alerts). M03-S1: AntMed Item + list_items/get_item.

---
## [AUTO] Wave A — M03 Inventory completion  (deps: none; LOW, A4/A5 MEDIUM)
- **A1 (M03-S2)** Warehouse + stock ledger: `AntMed Warehouse`(3-tier validate), `AntMed Stock Ledger`(log), `AntMed Stock Entry`(+`Stock Entry Item`, submittable) → ledger write + tồn-không-âm; API `create_stock_entry`/`get_stock`/`list_stock_by_warehouse`/`list_stock_entries`.
- **A2 (M03-S1b)** CO/CQ catalog: `AntMed Supplier`, `AntMed Lot`, `AntMed Certificate`(hash_sha256) + `list_lots`; BR set `cocq_ok`. Patch `AntMed Quota Item.item` Data→Link `AntMed Item` (M02 ADR-M02-02).
- **A3 (M03-S3)** FIFO/HSD: `fifo_suggest`/`check_fifo` (BR-08 warn) + scheduler `check_near_expiry_90_60_30`.
- **A4 (M03-S4)** Consignment recon: `AntMed Consignment Reconciliation`(+item, submittable, workflow 5-state) + `start`/`submit_reconciliation`/`list_consignment_pending` + weekly reminder (BR-15).
- **A5 (M03-S5)** Lot-trace + recall: `AntMed Lot Trace Request` + `trace_lot`; `AntMed Recall Notification`(workflow 4-state) + `create_recall`/`broadcast_recall` (M13 lazy stub).

## [AUTO] Wave B — M04 OR Delivery/SLA  (deps: M01,M02,M03; LOW-MEDIUM)
- **B1** Schema+workflow: `AntMed Delivery`(+`Delivery Item`/`DO Photo`/`DO Signature`), `AntMed SLA Log`, `AntMed OR Schedule` + DR Workflow (6-state) + DocPerm.
- **B2** Read+BR-01: `list_deliveries`/`get_delivery`/`create_request` + validate item-in-contract (wire M02 `contract_hooks`).
- **B3** Lifecycle+SLA: `assign`/`start_transit`/`handover` (gate sig+photo+gps, sla_status) + BR-07 block-delete-signed.
- **B4** FIFO+quota: `fifo_suggest` + BR-08 warn + BR-06 quota lock + `dispatch_board`; on_submit → `consume_quota` (M02).

## [AUTO] Wave C — M05 Instrument Loan  (deps: M01; M03 soft; LOW)
- **C1** Set master: `AntMed Instrument Set`(+`Component`) + `list_instrument_sets`/`get_instrument_set`.
- **C2** Loan 7-state: `AntMed Instrument Loan`(+2 checklist child) + workflow + `book`(BR-05)/`handover`/`receive_return` + sync_set_status hook.
- **C3** Sterilize: `AntMed Sterilization` + `sterilize`/`mark_ready` (BR-09 require Pass).
- **C4** Incident+overdue: `AntMed Loan Incident` + `report_incident` + scheduler `check_overdue_loans`.

## [AUTO] Wave D — M07 Doctor Care  (deps: M01; LOW)
- **D1** Visit+GPS: `AntMed Doctor Visit`(workflow 4-state) + `AntMed Care Note` + `check_in`/`save_care_note`/`list_*`.
- **D2** Gift compliance: `AntMed Doctor Gift` + BR-11 (validate approver) + `create_gift`/`list_gifts`.
- **D3** Survey: `AntMed Satisfaction Survey` + `submit_survey`.
- **D4** Call plan: `AntMed Call Plan` + scheduler `send_call_plan_today`/`notify_doctor_birthdays`.
- **D5** Summary: `doctor_care_summary` aggregate.

## [AUTO] Wave E — M08 Pipeline  (deps: M01; feeds M02; LOW)
- **E1** Core-CRM extend (ADDITIVE custom fields only): `CRM Lead`/`CRM Deal` antmed_* fields + `list_pipeline`/`get_pipeline_board`/`move_stage`.
- **E2** Tender: `AntMed Tender`(workflow 6-state) + `create_tender`/`get_tender`/`set_tender_result` (BR-M08-01/02/03).
- **E3** Forecast: `forecast` endpoint.
- **E4** Win→Contract: on_submit Trúng → create `AntMed Contract` (BR-M08-05, guarded, wire M02).

## [AUTO] Wave F — M11 Dashboard (read-only, deps land incrementally; LOW)
- Build each `dashboard.<fn>` as its upstream module lands (ceo_kpis, top_hospitals/sales, sla_delivery, kanban_b1, stock_by_lot, ar_aging_buckets, compliance_report, pipeline_funnel, drilldown…). `overview()` already shipped. Each endpoint `frappe.db.exists`-gates its source + degrades to 0/[].

---
## ⛔ [STOP — sign-off each] High-risk modules
- **M06 Documents/HĐĐT** (deps M02/M03/M04): e-invoice issuance, provider secrets (Password), CO/CQ gate BR-03, hash-chain. 4 slices.
- **M09 Orders/AR** (deps M02/M04): debt-block BR-14, payments, immutable AR ledger, 2FA unblock. 5 slices.
- **M10 HR/KPI** (deps M04/M05/M09): commission/pay, owns NV↔BV route table (BR-13 foundation), removes scaffold SQL-eval. 4 slices.
- **M13 Integrations** (deps M06/M09): secrets at rest, `allow_guest` webhooks (HMAC), e-invoice dispatch. 6 slices.
- **M14-W4 Security** (foundation): audit hash-chain BR-10, 2FA BR-12, data-scope BR-13 (touches CRM-core auth files). 5 slices.
- **M12 Mobile/PWA** (deps M01/M04/M05): offline write-replay must not bypass server BR. MEDIUM. 5 slices.

## Suggested order
A (M03) → B (M04) → C (M05) → D (M07) ∥ E (M08) → **STOP** M06 → **STOP** M09 → **STOP** M10 → F (M11 fill-in) → **STOP** M13 → **STOP** M14 → **STOP** M12.
