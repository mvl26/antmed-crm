# AntMed CRM — Agent Instructions

> Nguồn sự thật đầy đủ ở **[CLAUDE.md](./CLAUDE.md)** (đọc trước khi sửa/quyết định) +
> quy tắc chi tiết trong **`.claude/rules/`**. File này chỉ tóm tắt để các tool khác (Codex…) định vị.

## Tóm tắt
- App RIÊNG **`antmed_crm`** (fork Frappe CRM, KHÔNG in-place `crm`). Site dev = **`miyano`**.
- Python: `antmed_crm/`. Endpoint: `antmed_crm.api.antmed.<module>.<fn>`. Doctype prefix `AntMed `. KHÔNG ERPNext.
- FE: Vue 3 + frappe-ui, `frontend/src/`, base `/crm`, route `/antmed/*`.

## Quy tắc sống-còn (chi tiết: `.claude/rules/`)
1. Sửa BE `.py` → reload web (`sudo supervisorctl restart frappe-bench-web:`, HARD-STOP user); verify
   `bench execute` (417=stale / 403=auth / 200). → `01-backend-deploy.md`
2. Sửa FE → user xóa cache PWA + unregister SW (rebuild không đủ). createResource GET đừng truyền object/
   `undefined` thô (→ "[object Object]"/"undefined" → trang trống); `__("{0}")` luôn kèm `[args]`. → `02-frontend.md`
3. AntMed = app riêng: không lẫn role/data/branding app khác (assetcore…); không remnant Frappe CRM. → `03-app-isolation.md`
4. Verify bằng data thật + rollback; nhiều phiên Claude chạy song song → check mtime trước khi sửa file chung,
   KHÔNG kill phiên khác, KHÔNG commit trừ khi user yêu cầu. → `04-verify-concurrency.md`

## Test / build
```bash
cd frontend && yarn build && npx vitest run tests/unit/
bench --site miyano run-tests --module antmed_crm.tests.test_antmed_<module>
```

## Commit
Chỉ commit khi user yêu cầu (skill `antmed-commit`). Nhiều commit logic nhỏ, tách BE/FE. Pre-commit hook chạy
prettier/eslint — nếu nó sửa file thì `git add` lại.
