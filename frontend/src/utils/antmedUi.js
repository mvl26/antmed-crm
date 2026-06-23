/**
 * AntMed prototype — UI helper thuần (palette mockup → token Tailwind dự án).
 *
 * Tham chiếu: docs/antmed_crm/docs/AntMed_CRM_Full_Mockups.html.
 * Mockup palette → Tailwind:
 *   brand #0EA5A4 → teal-600 · brand-dark #134E4A → teal-900 · brand-soft #E0F2F1 → teal-50
 *   accent #F97316 → orange-500 · danger #DC2626 → red-600 · ok #16A34A → green-600 · warn #F59E0B → amber-500
 *
 * Đây là tầng thuần (không Vue) để unit-test trực tiếp — component chỉ bind class trả về.
 */

/** Pill trạng thái (mockup .pill.{ok|warn|danger|info|neutral}). Kèm CHỮ — không chỉ màu (WCAG). */
export const PILL_THEME = {
  ok: 'bg-green-100 text-green-800',
  warn: 'bg-amber-100 text-amber-800',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  neutral: 'bg-ink-gray-2 text-ink-gray-7',
}

/** Class pill theo theme; theme lạ → neutral (an toàn, không vỡ render). */
export function pillClass(theme) {
  return PILL_THEME[theme] || PILL_THEME.neutral
}

/** Thanh bar tiến độ (mockup .bar / .bar.warn / .bar.danger). */
export const BAR_THEME = {
  default: 'bg-teal-600',
  warn: 'bg-amber-500',
  danger: 'bg-red-500',
}
export function barFillClass(theme) {
  return BAR_THEME[theme] || BAR_THEME.default
}

/**
 * M02 quota — % ĐÃ DÙNG từ remaining_pct của BE ("% CÒN LẠI").
 * usedPct = 100 - remaining_pct, clamp 0–100. remaining_pct null/NaN → 0 (xanh, không vỡ).
 * Spec FROZEN m02_contract_quota.md §1ter.3.
 */
export function quotaUsedPct(remainingPct) {
  // null/undefined/'' = chưa có dữ liệu quota → coi như chưa dùng (0% → xanh, không vỡ).
  if (
    remainingPct === null ||
    remainingPct === undefined ||
    remainingPct === ''
  )
    return 0
  const r = Number(remainingPct)
  if (!Number.isFinite(r)) return 0
  const used = 100 - r
  if (used < 0) return 0
  if (used > 100) return 100
  return used
}

/**
 * M02 quota — theme thanh % theo NGƯỠNG % đã dùng (khớp mockup A2):
 *   usedPct >= 95 → 'danger' (đỏ) · >= 72 → 'warn' (cam) · còn lại → 'default' (brand xanh).
 * Trả key cho BAR_THEME (dùng cùng barFillClass). Spec FROZEN §1ter.3.
 */
export function quotaBarTheme(usedPct) {
  const u = Number(usedPct)
  if (Number.isFinite(u) && u >= 95) return 'danger'
  if (Number.isFinite(u) && u >= 72) return 'warn'
  return 'default'
}

/**
 * Tiện ích gộp: từ remaining_pct của BE → class fill thanh quota (theme theo ngưỡng).
 * Component chỉ bind class trả về (tầng thuần để unit-test trực tiếp).
 */
export function quotaBarClass(remainingPct) {
  return barFillClass(quotaBarTheme(quotaUsedPct(remainingPct)))
}

/**
 * M02-6 "Tiêu hao HĐ theo tháng" (mockup A1 bar chart) — chiều cao % của 1 cột bar:
 *   barHeightPct = round(qty / maxQty * 100), clamp 0–100.
 *   maxQty <= 0 (mọi cột 0) → 0 (KHÔNG ZeroDivisionError / NaN).
 *   qty/maxQty null/undefined/NaN → 0 (cột rỗng, không vỡ render).
 *   qty > maxQty → 100 (clamp, không vượt khung).
 * Pure (không Vue) — unit-test trực tiếp; component chỉ :style height = barHeightPct + '%'.
 * FE KHÔNG tự tính bucket/tháng/SUM — chỉ chuyển qty (BE đã gộp) sang chiều cao bar.
 *
 * @param {number|string|null|undefined} qty
 * @param {number|string|null|undefined} maxQty
 * @returns {number} 0–100 (đã round).
 */
export function barHeightPct(qty, maxQty) {
  const q = Number(qty)
  const m = Number(maxQty)
  if (!Number.isFinite(q) || !Number.isFinite(m) || m <= 0) return 0
  let pct = (q / m) * 100
  if (pct < 0) pct = 0
  if (pct > 100) pct = 100
  return Math.round(pct)
}

// (funnelBarWidth + funnelBarClass + TENDER_STAGE_THEME : xem §M08 funnel cuối file —
//  định nghĩa DUY NHẤT ở đó, dùng token Tailwind teal nhạt dần thay hex thô.)

/**
 * M02-2 "Sức khoẻ Hợp đồng" (mockup A2) — ánh xạ TRỰC TIẾP cờ màu BE → class fill thanh % Quota.
 *
 * BE (antmed_crm.api.antmed.contract.get_contract_health._health_color) ĐÃ quyết định màu theo §7:
 *   'green'  (≤80% đã dùng)  → default (brand teal)
 *   'orange' (>80–100%)      → warn (cam)
 *   'red'    (>100% HOẶC còn ≤30 ngày tới hạn) → danger (đỏ)
 * FE KHÔNG tự tính ngưỡng lại (BR sống ở BE) — chỉ map health_color → key BAR_THEME rồi bind class.
 * Cờ lạ/rỗng → default (xanh, không vỡ render). Tầng thuần — unit-test trực tiếp.
 *
 * @param {('green'|'orange'|'red'|string|null|undefined)} healthColor
 * @returns {string} class Tailwind cho fill thanh (BAR_THEME.default|warn|danger).
 */
export const HEALTH_COLOR_THEME = {
  green: 'default',
  orange: 'warn',
  red: 'danger',
}
export function healthBarClass(healthColor) {
  return barFillClass(HEALTH_COLOR_THEME[healthColor] || 'default')
}

/**
 * M02-2 — nhãn cảnh báo hết hạn HĐ từ days_to_expiry (BE: (valid_to - hôm nay).days, None nếu thiếu).
 *   0 ≤ d ≤ 30  → 'Sắp hết hạn N ngày' (chip cảnh báo đỏ, kể cả d=0 = "Sắp hết hạn 0 ngày").
 *   d < 0       → 'Đã hết hạn'.
 *   d > 30 / null/undefined/NaN → '' (không cảnh báo).
 * Pure (không Vue) để unit-test trực tiếp; component chỉ render chuỗi trả về + style đỏ khi != ''.
 *
 * @param {number|null|undefined} days
 * @returns {string} nhãn VI hoặc '' khi không cần cảnh báo.
 */
export function expiryLabel(days) {
  if (days === null || days === undefined || days === '') return ''
  const d = Number(days)
  if (!Number.isFinite(d)) return ''
  if (d < 0) return 'Đã hết hạn'
  if (d <= 30) return `Sắp hết hạn ${d} ngày`
  return ''
}

/**
 * M02-3 "Cảnh báo điều hành" (mockup A1 widget ⚠) — helper THUẦN cho 1 alert của
 * antmed_crm.api.antmed.contract.list_quota_alerts (shape 10-key, kind 'quota'|'expiry').
 *
 * ⚠️ FE KHÔNG tự tính lại ngưỡng từ used_pct — dùng cờ BE (threshold cho quota; dấu/giá trị
 * days_to_expiry cho expiry). BR sống ở BE; FE chỉ MAP cờ → theme/label/câu VI hiển thị.
 *
 * alertPillTheme: màu pill (PILL_THEME key) theo mockup A1:
 *   quota: threshold 100|90 → 'danger' (đỏ) · 70 → 'warn' (cam).
 *   expiry: days_to_expiry < 0 (đã quá hạn) → 'danger' (đỏ) · 0..30 → 'warn' (cam).
 *   alert lạ/thiếu cờ → 'warn' (an toàn, không vỡ render).
 *
 * @param {object|null|undefined} alert
 * @returns {('danger'|'warn')}
 */
export function alertPillTheme(alert) {
  if (!alert || typeof alert !== 'object') return 'warn'
  if (alert.kind === 'quota') {
    const t = Number(alert.threshold)
    if (Number.isFinite(t) && t >= 90) return 'danger'
    return 'warn'
  }
  if (alert.kind === 'expiry') {
    const d = Number(alert.days_to_expiry)
    if (Number.isFinite(d) && d < 0) return 'danger'
    return 'warn'
  }
  return 'warn'
}

/**
 * M02-3 — nhãn CHỮ trên pill (WCAG: không phân biệt chỉ bằng màu):
 *   quota → 'QUOTA'.
 *   expiry: days_to_expiry < 0 → 'ĐÃ HẾT HẠN' · ≥ 0 → 'HẾT HẠN'.
 *   alert lạ → 'CẢNH BÁO' (fallback, vẫn là chữ).
 *
 * @param {object|null|undefined} alert
 * @returns {string}
 */
export function alertPillLabel(alert) {
  if (!alert || typeof alert !== 'object') return 'CẢNH BÁO'
  if (alert.kind === 'quota') return 'QUOTA'
  if (alert.kind === 'expiry') {
    const d = Number(alert.days_to_expiry)
    return Number.isFinite(d) && d < 0 ? 'ĐÃ HẾT HẠN' : 'HẾT HẠN'
  }
  return 'CẢNH BÁO'
}

/**
 * M02-3 — câu nội dung VI cho 1 alert (2 mẫu, theo acceptance A1):
 *   quota:  '<contract_no> · <hospital_name> — VT <item_name> đã dùng <used_pct>% (ngưỡng <threshold>%)'.
 *   expiry: '<contract_no> · <hospital_name> — còn <days_to_expiry> ngày'        (days ≥ 0)
 *           '<contract_no> · <hospital_name> — đã quá hạn <|days|> ngày'         (days < 0).
 * Hiển thị *_name (tên BV/VT) — KHÔNG mã. Thiếu tên → fallback contract_no/'—' (không lộ ID thô).
 * Pure (không Vue) — unit-test trực tiếp; component chỉ render chuỗi trả về.
 *
 * @param {object|null|undefined} alert
 * @returns {string}
 */
export function alertText(alert) {
  if (!alert || typeof alert !== 'object') return ''
  const cno = alert.contract_no || alert.contract || '—'
  const hosp = alert.hospital_name || '—'
  const head = `${cno} · ${hosp}`
  if (alert.kind === 'quota') {
    const item = alert.item_name || '—'
    return `${head} — VT ${item} đã dùng ${alert.used_pct}% (ngưỡng ${alert.threshold}%)`
  }
  if (alert.kind === 'expiry') {
    const d = Number(alert.days_to_expiry)
    if (Number.isFinite(d) && d < 0)
      return `${head} — đã quá hạn ${Math.abs(d)} ngày`
    return `${head} — còn ${alert.days_to_expiry} ngày`
  }
  return head
}

/**
 * M11 quota ring (mockup A1 .ring) — theme theo NGƯỠNG % đã dùng, cùng ngưỡng quotaBarTheme:
 *   usedPct >= 95 → 'danger' (đỏ) · >= 72 → 'warn' (cam) · còn lại → 'default' (brand teal).
 * Trả key dùng chung BAR_THEME/RING_COLOR_VAR. usedPct null/NaN → 'default' (xanh, không vỡ).
 */
export function quotaRingTheme(usedPct) {
  return quotaBarTheme(usedPct)
}

/**
 * Màu fill ring theo theme — dùng CSS var token frappe-ui (KHÔNG hex thô):
 *   default → brand teal · warn → accent cam · danger → đỏ. (mockup A1 §10 token.)
 * Theme lạ → teal (an toàn). Dùng cho conic-gradient ở component (inline style).
 */
export const RING_COLOR_VAR = {
  default: 'var(--teal-600)',
  warn: 'var(--orange-500)',
  danger: 'var(--red-600)',
}
export function ringColorVar(theme) {
  return RING_COLOR_VAR[theme] || RING_COLOR_VAR.default
}

/**
 * Style inline cho vòng ring conic-gradient (mockup A1 .ring): phần đã-dùng tô màu theo
 * ngưỡng, phần còn lại xám nhạt (token). pct clamp 0–100; null/NaN → 0 (vòng trống, xanh).
 * Component chỉ :style bind object trả về (tầng thuần — unit-test trực tiếp, không Vue).
 */
export function quotaRingStyle(usedPct) {
  let p = Number(usedPct)
  if (!Number.isFinite(p)) p = 0
  if (p < 0) p = 0
  if (p > 100) p = 100
  const color = ringColorVar(quotaRingTheme(p))
  const deg = (p / 100) * 360
  return {
    background: `conic-gradient(${color} ${deg}deg, var(--gray-200) ${deg}deg 360deg)`,
  }
}

/** Heatmap cell mức 1..5 (mockup .h1c..h5c — đỏ tăng dần). */
export const HEAT_CLASS = {
  1: 'bg-red-100 text-red-800',
  2: 'bg-red-200 text-red-900',
  3: 'bg-red-300 text-red-900',
  4: 'bg-red-400 text-white',
  5: 'bg-red-500 text-white',
}
export function heatClass(level) {
  return HEAT_CLASS[level] || ''
}

/** Một chặng lifecycle/steps (mockup .lifecycle div.done/.cur, .step.done/.current). */
export function stageClass(status) {
  if (status === 'done') return 'bg-green-100 text-green-800 font-semibold'
  if (status === 'current' || status === 'cur')
    return 'bg-teal-600 text-white font-semibold'
  return 'bg-ink-gray-2 text-ink-gray-5'
}

/** Alert box theme (mockup .alert-box / .info / .danger). */
export const ALERT_THEME = {
  info: 'bg-blue-50 border-blue-400 text-blue-800',
  warn: 'bg-amber-50 border-amber-500 text-amber-800',
  danger: 'bg-red-50 border-red-500 text-red-800',
}
export function alertClass(theme) {
  return ALERT_THEME[theme] || ALERT_THEME.warn
}

/** Viền trái accent cho kanban card (mockup .kcard.urgent/.warn/.ok). */
export const KANBAN_ACCENT = {
  urgent: 'border-l-4 border-l-red-500',
  warn: 'border-l-4 border-l-orange-500',
  ok: 'border-l-4 border-l-green-600',
}
export function kanbanAccentClass(accent) {
  return KANBAN_ACCENT[accent] || ''
}

/**
 * M03-1 (widget kho "Phiếu xuất gần đây") — format tiền VN gọn: 'X,Y tr' / 'X,Y tỷ'.
 *   < 1 triệu        → số nguyên đồng có phân tách (vd 950.000).
 *   1 triệu – < 1 tỷ → 'X,Y tr' (1 chữ số thập phân, dấu phẩy VI). 1.900.000 → '1,9 tr'.
 *   ≥ 1 tỷ           → 'X,Y tỷ'. 1.200.000.000 → '1,2 tỷ'.
 *   null/undefined/'' / NaN → '— ' (em-dash + space, đồng nhất placeholder thiếu giá trị).
 * Pure (không Vue) — unit-test trực tiếp; component chỉ render chuỗi trả về.
 *
 * @param {number|string|null|undefined} value
 * @returns {string}
 */
export function formatVnMoney(value) {
  if (value === null || value === undefined || value === '') return '— '
  const n = Number(value)
  if (!Number.isFinite(n)) return '— '
  const fmt = (x) => {
    // 1 chữ số thập phân, bỏ '.0', đổi '.' → ',' (dấu thập phân VI).
    const s = (Math.round(x * 10) / 10).toFixed(1).replace(/\.0$/, '')
    return s.replace('.', ',')
  }
  if (Math.abs(n) >= 1_000_000_000) return `${fmt(n / 1_000_000_000)} tỷ`
  if (Math.abs(n) >= 1_000_000) return `${fmt(n / 1_000_000)} tr`
  return n.toLocaleString('vi-VN', { maximumFractionDigits: 0 })
}

/**
 * M03-1 — format thời điểm phiếu kho: 'HH:mm dd/MM/yyyy' (giờ trước, ngày sau — khớp mockup).
 * value thiếu / parse fail → '—'. Pure (không Vue) — unit-test trực tiếp.
 *
 * @param {string|Date|null|undefined} value
 * @returns {string}
 */
export function formatStockTime(value) {
  if (!value) return '—'
  const d = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const p = (x) => String(x).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())} ${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`
}

/**
 * M03-1 — theme Badge cho entry_type phiếu kho. KEY khớp EXACT options DocType
 * `AntMed Stock Entry.entry_type` (VI có dấu): Nhập NCC / Xuất cho NV / Chuyển kho /
 * Nhập ký gửi BV / Điều chỉnh. Badge LUÔN kèm label chữ (không phân biệt chỉ bằng màu — WCAG).
 * Loại lạ/rỗng → 'gray' (an toàn, không vỡ render).
 */
export const ENTRY_TYPE_THEME = {
  'Nhập NCC': 'green',
  'Xuất cho NV': 'blue',
  'Chuyển kho': 'orange',
  'Nhập ký gửi BV': 'teal',
  'Điều chỉnh': 'gray',
}
export function entryTypeChipTheme(entryType) {
  return ENTRY_TYPE_THEME[entryType] || 'gray'
}

/**
 * M03-6 (mockup D3 right-card "Cây truy vết") — nhãn VI cho 1 event theo entry_type.
 * KEY khớp EXACT options DocType `AntMed Stock Entry.entry_type` (VI có dấu) — chỉ MAP nhãn
 * hiển thị, KHÔNG đổi key tra cứu BE:
 *   'Nhập NCC' → 'Nhập từ NCC' · 'Xuất cho NV' → 'Xuất cho NV' · 'Chuyển kho' → 'Chuyển kho' ·
 *   'Nhập ký gửi BV' → 'Nhập ký gửi BV' · 'Điều chỉnh' → 'Điều chỉnh'.
 * entry_type lạ/rỗng → trả thẳng giá trị (hoặc 'Di chuyển' khi rỗng) — fallback an toàn (vẫn chữ VI).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component chỉ render chuỗi trả về.
 *
 * @param {('Nhập NCC'|'Xuất cho NV'|'Chuyển kho'|'Nhập ký gửi BV'|'Điều chỉnh'|string|null|undefined)} entryType
 * @returns {string} nhãn tiếng Việt.
 */
export const ENTRY_DIRECTION_LABEL = {
  'Nhập NCC': 'Nhập từ NCC',
  'Xuất cho NV': 'Xuất cho NV',
  'Chuyển kho': 'Chuyển kho',
  'Nhập ký gửi BV': 'Nhập ký gửi BV',
  'Điều chỉnh': 'Điều chỉnh',
}
export function entryDirectionLabel(entryType) {
  return ENTRY_DIRECTION_LABEL[entryType] || entryType || 'Di chuyển'
}

/**
 * M03-6 — chip CHIỀU di chuyển (direction) → class pill (PILL_THEME, tái dùng pillClass).
 * KEY khớp EXACT direction BE trả (antmed_crm.api.antmed.inventory.lot_trace):
 *   'in'  (qty_change>0, nhập/nhận) → success/green (PILL_THEME.ok)
 *   'out' (qty_change<0, xuất/chuyển đi) → warn (PILL_THEME.warn)
 * direction lạ/rỗng → neutral (an toàn, không vỡ render). Chip LUÔN kèm CHỮ (Nhập/Xuất) —
 * không phân biệt chỉ bằng màu (WCAG AA). Pure (không import frappe-ui) — unit-test trực tiếp.
 *
 * @param {('in'|'out'|string|null|undefined)} direction
 * @returns {string} class Tailwind pill (PILL_THEME.ok | PILL_THEME.warn | PILL_THEME.neutral).
 */
export const TRACE_DIRECTION_THEME = {
  in: 'ok',
  out: 'warn',
}
export function traceDirectionChipTheme(direction) {
  return TRACE_DIRECTION_THEME[direction] || 'neutral'
}
export function traceDirectionChipClass(direction) {
  return pillClass(traceDirectionChipTheme(direction))
}

/**
 * M03-6 — nhãn VI ngắn cho chip chiều (kèm chữ — WCAG, không chỉ màu).
 *   'in' → 'Nhập' · 'out' → 'Xuất' · lạ/rỗng → 'Di chuyển'.
 */
export function traceDirectionLabel(direction) {
  if (direction === 'in') return 'Nhập'
  if (direction === 'out') return 'Xuất'
  return 'Di chuyển'
}

/**
 * M03-2 (mockup D3 "Thông tin lot") — format ngày 'dd/MM/yyyy' (NSX/HSD).
 * Nhận chuỗi ISO 'yyyy-MM-dd' (Frappe Date) hoặc Date. Thiếu / parse fail → '—'.
 * Parse ISO yyyy-MM-dd THỦ CÔNG (KHÔNG new Date(str) — tránh lệch timezone UTC trừ 1 ngày).
 * Pure (không Vue) — unit-test trực tiếp; component chỉ render chuỗi trả về.
 *
 * @param {string|Date|null|undefined} value
 * @returns {string}
 */
export function fmtDate(value) {
  if (!value) return '—'
  const p = (x) => String(x).padStart(2, '0')
  if (typeof value === 'string') {
    // 'yyyy-MM-dd' (kèm phần giờ tuỳ chọn) → tách thủ công, không qua Date (tránh lệch TZ).
    const m = value.match(/^(\d{4})-(\d{2})-(\d{2})/)
    if (m) return `${m[3]}/${m[2]}/${m[1]}`
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return '—'
    return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`
  }
  const d = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`
}

/**
 * M03-2 (mockup D3) — chip trạng thái thu hồi (recall_status) → class pill (PILL_THEME).
 * KEY khớp EXACT options DocType `AntMed Lot.recall_status` (VI có dấu):
 *   'Bình thường' → neutral (xám) · 'Theo dõi' → warn (cam) · 'Đã thu hồi' → danger (đỏ).
 * Trạng thái lạ/rỗng → neutral (an toàn, không vỡ render). Tái dùng token chip có sẵn.
 * Chip LUÔN kèm CHỮ (label = recall_status) — không phân biệt chỉ bằng màu (WCAG AA).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component chỉ bind class trả về.
 *
 * @param {('Bình thường'|'Theo dõi'|'Đã thu hồi'|string|null|undefined)} recallStatus
 * @returns {string} class Tailwind pill (PILL_THEME.neutral|warn|danger).
 */
export const RECALL_THEME = {
  'Bình thường': 'neutral',
  'Theo dõi': 'warn',
  'Đã thu hồi': 'danger',
}
export function recallChipTheme(recallStatus) {
  return RECALL_THEME[recallStatus] || 'neutral'
}
export function recallChipClass(recallStatus) {
  return pillClass(recallChipTheme(recallStatus))
}

/**
 * M03-7 (mockup D3 action "⚠ Khởi tạo Recall theo lot này") — tập mức recall HỢP LỆ khi Thủ kho
 * KHỞI TẠO recall (option của dropdown 'Mức recall' trong confirm-modal). KHÔNG gồm 'Bình thường'
 * (không recall ngược về bình thường ở đây). Đồng bộ EXACT với BE export
 * antmed_crm.api.antmed.inventory.RECALL_STATUS_OPTIONS == ('Theo dõi', 'Đã thu hồi').
 * Mặc định chọn 'Đã thu hồi' (mockup D3: mức mặc định khi bấm nút recall).
 * KEY khớp EXACT options DocType AntMed Lot.recall_status (VI có dấu) — gửi đi == key BE, không nhãn.
 */
export const RECALL_INITIATE_STATUSES = ['Theo dõi', 'Đã thu hồi']
/** Mức recall mặc định trong confirm-modal (mockup D3). */
export const RECALL_INITIATE_DEFAULT = 'Đã thu hồi'

/**
 * M03-3 (mockup D2 "Kho ký gửi tại Bệnh viện") — chip trạng thái HSD cận date.
 * Cùng ngưỡng 90 ngày với KPI (cờ near_expiry đã do BE quyết — FE chỉ map class/nhãn).
 *   near=true  → danger (đỏ, 'Cận date')   · near=false → ok (xanh, 'Bình thường').
 * Giá trị lạ (null/undefined) → ok (an toàn, không vỡ render). Tái dùng token chip PILL_THEME.
 * Chip LUÔN kèm CHỮ (nearExpiryLabel) — không phân biệt chỉ bằng màu (WCAG AA).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component chỉ bind class/nhãn trả về.
 *
 * @param {boolean|null|undefined} near - cờ near_expiry từ BE.
 * @returns {string} class Tailwind pill (PILL_THEME.danger | PILL_THEME.ok).
 */
export function nearExpiryChipClass(near) {
  return pillClass(near ? 'danger' : 'ok')
}

/**
 * Nhãn VI cho chip HSD cận date (kèm chữ — WCAG, không chỉ màu).
 * near=true → 'Cận date' · near=false/null/undefined → 'Bình thường'.
 */
export function nearExpiryLabel(near) {
  return near ? 'Cận date' : 'Bình thường'
}

/**
 * M03-4 (mockup D1 "⚠ Cảnh báo HSD") — chip MỨC ĐỘ cận date theo severity BE.
 * KEY khớp EXACT severity BE trả (antmed_crm.api.antmed.inventory.expiry_alerts):
 *   'expired' (đã quá hạn, <0)  → 'danger' (đỏ)
 *   'd30'     (≤30 ngày, 0..30) → 'danger' (đỏ — sát hạn = nguy cấp)
 *   'd60'     (≤60 ngày, 31..60)→ 'warn'   (cam)
 *   'd90'     (≤90 ngày, 61..90)→ 'neutral'(xám — cảnh báo nhẹ)
 * Severity lạ/rỗng → 'neutral' (an toàn, không vỡ render). FE KHÔNG tự tính tầng (BE đã quyết) —
 * chỉ MAP key → theme/nhãn. Chip LUÔN kèm CHỮ (expirySeverityLabel) — không chỉ màu (WCAG AA).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component bind theme/nhãn trả về.
 *
 * @param {('expired'|'d30'|'d60'|'d90'|string|null|undefined)} sev
 * @returns {('danger'|'warn'|'neutral')} key cho PILL_THEME (dùng cùng pillClass).
 */
export const EXPIRY_SEVERITY_THEME = {
  expired: 'danger',
  d30: 'danger',
  d60: 'warn',
  d90: 'neutral',
}
export function expirySeverityChipTheme(sev) {
  return EXPIRY_SEVERITY_THEME[sev] || 'neutral'
}

/**
 * M03-4 — nhãn VI cho chip MỨC ĐỘ cận date (kèm chữ — WCAG, không chỉ màu).
 * KEY khớp EXACT severity BE:
 *   'expired' → 'Đã hết hạn' · 'd30' → '≤30 ngày' · 'd60' → '≤60 ngày' · 'd90' → '≤90 ngày'.
 * Severity lạ/rỗng → 'Cận date' (fallback an toàn, vẫn là chữ VI). Pure (không Vue).
 *
 * @param {('expired'|'d30'|'d60'|'d90'|string|null|undefined)} sev
 * @returns {string} nhãn tiếng Việt.
 */
export const EXPIRY_SEVERITY_LABEL = {
  expired: 'Đã hết hạn',
  d30: '≤30 ngày',
  d60: '≤60 ngày',
  d90: '≤90 ngày',
}
export function expirySeverityLabel(sev) {
  return EXPIRY_SEVERITY_LABEL[sev] || 'Cận date'
}

/**
 * M03-4 — class chip cận date theo severity (gộp theme → pill class). Component bind thẳng.
 */
export function expirySeverityChipClass(sev) {
  return pillClass(expirySeverityChipTheme(sev))
}

/**
 * M03-3 — định dạng HSD theo 'MM/YYYY' (mockup D2 cột HSD).
 * Chuỗi 'yyyy-MM-dd' (kèm phần giờ tuỳ chọn) → tách thủ công, KHÔNG qua Date (tránh lệch TZ).
 * Date object → MM/YYYY theo local. null/''/parse-fail → '' (null-guard, KHÔNG ZeroDiv/crash).
 *
 * @param {string|Date|null|undefined} value
 * @returns {string} 'MM/YYYY' hoặc '' khi không hợp lệ.
 */
export function formatExpiryMonthYear(value) {
  if (!value) return ''
  const p = (x) => String(x).padStart(2, '0')
  if (typeof value === 'string') {
    const m = value.match(/^(\d{4})-(\d{2})-(\d{2})/)
    if (m) return `${m[2]}/${m[1]}`
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return ''
    return `${p(d.getMonth() + 1)}/${d.getFullYear()}`
  }
  const d = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return `${p(d.getMonth() + 1)}/${d.getFullYear()}`
}

/**
 * M03-8 (mockup C2 Wizard bước 3 — card "Vật tư đã chuẩn bị") — số lượng (SL) cột bảng vật tư.
 * Số nguyên/thập phân VI có phân tách (1.000); thiếu / NaN → '—'. Pure (không Vue) — unit-test trực tiếp.
 *
 * @param {number|string|null|undefined} value
 * @returns {string}
 */
export function fmtQty(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}

/**
 * M03-8 (mockup C2 — cột "CO-CQ") — chip chứng từ CO/CQ theo cờ cocq_ok của dòng vật tư (BE quyết).
 *   cocq_ok === true        → theme 'ok'   (xanh)  · nhãn 'CO/CQ ✓'   (đủ chứng từ).
 *   cocq_ok false / null / undefined → theme 'warn' (cam) · nhãn 'Thiếu CO/CQ' (chưa đủ — cảnh báo).
 * Tái dùng PILL_THEME (pillClass) — chip LUÔN kèm CHỮ (nhãn), không phân biệt chỉ bằng màu (WCAG AA).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component bind theme/class/nhãn trả về.
 *
 * @param {boolean|null|undefined} cocqOk - cờ cocq_ok từ BE (dòng vật tư đã đủ CO/CQ chưa).
 * @returns {('ok'|'warn')} key cho PILL_THEME.
 */
export function cocqChipTheme(cocqOk) {
  return cocqOk === true ? 'ok' : 'warn'
}
/** Class chip CO/CQ (gộp theme → PILL_THEME class). Component bind thẳng. */
export function cocqChipClass(cocqOk) {
  return pillClass(cocqChipTheme(cocqOk))
}
/** Nhãn VI chip CO/CQ (kèm chữ — WCAG, không chỉ màu). true→'CO/CQ ✓'; còn lại→'Thiếu CO/CQ'. */
export function cocqChipLabel(cocqOk) {
  return cocqOk === true ? 'CO/CQ ✓' : 'Thiếu CO/CQ'
}

/**
 * M03-S4 (mockup C2 Wizard "Xuất cho NV") — dòng vật tư THIẾU CO/CQ → chặn xuất (HARD-BLOCK ở FE,
 * BR-03 BE chỉ set cờ cocq_ok derived + warn; spec gate hard-block ở wizard). Dòng bị chặn khi
 * `requires_cocq` (VTYT bắt buộc CO/CQ) VÀ `cocq_ok !== true` (chưa đủ chứng từ). FE KHÔNG tự suy
 * requires_cocq/cocq_ok (BE đã quyết qua scan_lot) — chỉ ĐỌC cờ để bật alert + disable nút.
 *
 * @param {object|null|undefined} row - 1 dòng đã quét (có requires_cocq + cocq_ok từ scan_lot).
 * @returns {boolean} true = dòng bị chặn (thiếu CO/CQ bắt buộc).
 */
export function rowBlockedByCocq(row) {
  if (!row || typeof row !== 'object') return false
  const requires = Number(row.requires_cocq) === 1 || row.requires_cocq === true
  return requires && row.cocq_ok !== true
}

/**
 * M03-S4 — danh sách dòng bị chặn vì thiếu CO/CQ (dùng cho alert đỏ + disable nút 'Xuất').
 * Mảng rỗng / không phải mảng → [] (không vỡ).
 *
 * @param {Array<object>|null|undefined} rows
 * @returns {Array<object>} các dòng bị chặn.
 */
export function blockedCocqRows(rows) {
  if (!Array.isArray(rows)) return []
  return rows.filter(rowBlockedByCocq)
}

/**
 * M03-S5 (mockup "📊 Kiểm kê") — chênh lệch live của 1 dòng = counted − system (FE tính TRÌNH BÀY;
 * variance authoritative do BE controller tính tại submit). null/NaN → 0 (không vỡ).
 *
 * @param {number|string|null|undefined} countedQty
 * @param {number|string|null|undefined} systemQty
 * @returns {number} chênh lệch (có thể âm).
 */
export function countVariance(countedQty, systemQty) {
  // null/undefined/'' = chưa nhập → coi như 0 chênh lệch (KHÔNG Number(null)===0 ra chênh sai).
  const empty = (x) => x === null || x === undefined || x === ''
  if (empty(countedQty) || empty(systemQty)) return 0
  const c = Number(countedQty)
  const s = Number(systemQty)
  if (!Number.isFinite(c) || !Number.isFinite(s)) return 0
  return c - s
}

/** M03-S5 — class màu chênh lệch: >0 xanh · <0 đỏ · =0 trung tính (kèm số → không chỉ màu). */
export function varianceTextClass(variance) {
  const v = Number(variance)
  if (Number.isFinite(v) && v > 0) return 'text-green-700'
  if (Number.isFinite(v) && v < 0) return 'text-red-700'
  return 'text-ink-gray-7'
}

/**
 * M03-S5 — nhãn docstatus phiếu Kiểm kê (Frappe docstatus 0/1/2 → VI). KEY khớp docstatus chuẩn
 * Frappe (KHÔNG chuỗi EN ra UI): 0 → 'Nháp' · 1 → 'Đã chốt' · 2 → 'Đã huỷ'. Lạ → 'Nháp'.
 */
export const DOCSTATUS_LABEL = {
  0: 'Nháp',
  1: 'Đã chốt',
  2: 'Đã huỷ',
}
export function docstatusLabel(docstatus) {
  return DOCSTATUS_LABEL[Number(docstatus)] || 'Nháp'
}
/** M03-S5 — theme Badge docstatus: 0 nháp(gray) · 1 chốt(green) · 2 huỷ(red). */
export function docstatusTheme(docstatus) {
  const d = Number(docstatus)
  if (d === 1) return 'green'
  if (d === 2) return 'red'
  return 'gray'
}

/**
 * M02-7 — width style cho thanh "Cơ cấu doanh thu" (widget CEO, mockup A2). PURE:
 *   width = clamp(pct, 0, 100) + '%'. null/undefined/NaN/chuỗi-không-số → 0% (không vỡ).
 * KHÔNG đổi màu theo lớp (cơ cấu doanh thu = 1 màu brand, KHÔNG ngưỡng green/orange/red như
 * health) — màu đặt qua class cố định trên thanh ở component. KHÔNG sort/tính lại ở FE
 * (BE trả cố định 4 dòng A→B→C→D + pct). Không import Vue/frappe-ui → unit-test trực tiếp.
 *
 * @param {number|string|null|undefined} pct
 * @returns {{ width: string }}
 */
export function revenueMixBarStyle(pct) {
  const p = Number(pct)
  const clamped = Number.isFinite(p) ? Math.max(0, Math.min(100, p)) : 0
  return { width: `${clamped}%` }
}

/**
 * M02-7 — format tiền VI ĐẦY ĐỦ CHỮ cho widget "Cơ cấu doanh thu" (mockup A2 §10):
 *   ≥ 1 tỷ           → 'X,Y tỷ'    (1 chữ số thập phân, dấu phẩy VI). 2_100_000_000 → '2,1 tỷ'.
 *   1 triệu – < 1 tỷ → 'X,Y triệu'.                                  186_400_000 → '186,4 triệu'.
 *   < 1 triệu        → số nguyên đồng có phân tách (vd 950.000 đ → '950.000').
 *   0                → '0 đ'  (lớp doanh thu 0 vẫn render — KHÔNG '— ').
 *   null/undefined/'' / NaN → '— ' (placeholder thiếu giá trị, đồng nhất formatVnMoney).
 * KHÁC formatVnMoney (dùng viết tắt 'tr'): widget A2 dùng CHỮ ĐẦY ĐỦ 'triệu'/'tỷ' theo mockup.
 * Pure (không Vue) — unit-test trực tiếp; component chỉ render chuỗi trả về.
 *
 * @param {number|string|null|undefined} value
 * @returns {string}
 */
export function formatCurrencyVi(value) {
  if (value === null || value === undefined || value === '') return '— '
  const n = Number(value)
  if (!Number.isFinite(n)) return '— '
  if (n === 0) return '0 đ'
  const fmt = (x) => {
    // 1 chữ số thập phân, bỏ '.0' đuôi, đổi '.' → ',' (dấu thập phân VI).
    const s = (Math.round(x * 10) / 10).toFixed(1).replace(/\.0$/, '')
    return s.replace('.', ',')
  }
  if (Math.abs(n) >= 1_000_000_000) return `${fmt(n / 1_000_000_000)} tỷ`
  if (Math.abs(n) >= 1_000_000) return `${fmt(n / 1_000_000)} triệu`
  return n.toLocaleString('vi-VN', { maximumFractionDigits: 0 })
}

// ── M08 funnel "Pipeline gói thầu" (mockup A1 Hàng 3) ───────────────────────

/** Floor % width tối thiểu của bar funnel — đủ rộng để nhãn + count còn đọc được. */
export const FUNNEL_BAR_MIN_FLOOR = 36

/**
 * Tính % WIDTH của 1 bar funnel theo tỉ lệ count/maxCount (giảm dần theo bậc).
 *
 * Quy tắc (PURE — không Vue, unit-test trực tiếp):
 *   - maxCount <= 0 (hoặc không hữu hạn)  → 0   (funnel rỗng — component xử lý empty-state riêng).
 *   - count >= maxCount                   → 100 (tầng đỉnh full width).
 *   - count <= 0 (mà maxCount > 0)        → minFloor (vẫn render được nhãn của tầng rỗng).
 *   - còn lại: count/maxCount*100, KẸP trong [minFloor .. 100] (không nhỏ hơn floor để đọc nhãn,
 *     không vượt 100).
 *
 * @param {number} count       số đếm tầng hiện tại
 * @param {number} maxCount    số đếm lớn nhất trong funnel (mẫu số tỉ lệ)
 * @param {number} [minFloor]  % tối thiểu (mặc định FUNNEL_BAR_MIN_FLOOR)
 * @returns {number} % width trong [0, 100]
 */
export function funnelBarWidth(
  count,
  maxCount,
  minFloor = FUNNEL_BAR_MIN_FLOOR,
) {
  const max = Number(maxCount)
  if (!Number.isFinite(max) || max <= 0) return 0
  const c = Number(count)
  if (!Number.isFinite(c) || c <= 0) return minFloor
  if (c >= max) return 100
  const pct = (c / max) * 100
  return Math.min(100, Math.max(minFloor, pct))
}

/**
 * Dải màu brand teal NHẠT DẦN theo bậc funnel (tầng đỉnh đậm → tầng cuối nhạt) — token Tailwind,
 * KHÔNG hex thô. Index theo thứ tự stages BE (lead→survey→quote→bid→won). Tái dùng cho :class bar.
 * Tầng ngoài range → token nhạt nhất (an toàn).
 */
export const TENDER_STAGE_THEME = [
  'bg-teal-600 text-white',
  'bg-teal-500 text-white',
  'bg-teal-400 text-teal-900',
  'bg-teal-300 text-teal-900',
  'bg-teal-200 text-teal-900',
]

/** Lớp nền dải teal nhạt dần cho bar funnel ở bậc index (fallback nhạt nhất). */
export function funnelBarClass(index) {
  return (
    TENDER_STAGE_THEME[index] ??
    TENDER_STAGE_THEME[TENDER_STAGE_THEME.length - 1]
  )
}

// ── M10-1 "Quản lý Đội ngũ" (mockup B2) — helper THUẦN bảng KPI đội ngũ ───────

/**
 * M10-1 — class fill thanh "DS tháng" theo bar_theme BE (antmed_crm.api.antmed.sales_team.team_roster).
 * KEY khớp EXACT bar_theme BE trả (green/warn/danger — ngưỡng 70/50, BE đã quyết, FE KHÔNG tính lại):
 *   'green'  (>=70% so đỉnh đội) → default (brand teal)
 *   'warn'   (>=50%)             → warn (cam)
 *   'danger' (<50%)              → danger (đỏ)
 * Tái dùng BAR_THEME/barFillClass (map green → default-teal). theme lạ/rỗng → default (xanh, không vỡ).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component chỉ bind class trả về.
 *
 * @param {('green'|'warn'|'danger'|string|null|undefined)} barTheme
 * @returns {string} class Tailwind cho fill thanh (BAR_THEME.default|warn|danger).
 */
export const TEAM_BAR_THEME = {
  green: 'default',
  warn: 'warn',
  danger: 'danger',
}
export function teamBarClass(barTheme) {
  return barFillClass(TEAM_BAR_THEME[barTheme] || 'default')
}

/**
 * M10-1 — class chip CẢNH BÁO doanh số. KEY khớp EXACT alert BE trả:
 *   'DS thấp' → pill danger (đỏ — sales_pct < 50%).
 *   '' (rỗng / null / undefined) → '' (KHÔNG render chip — đội đủ chỉ tiêu).
 * Tái dùng pillClass(PILL_THEME). Pure (không import frappe-ui) — unit-test trực tiếp.
 *
 * @param {('DS thấp'|''|string|null|undefined)} alert
 * @returns {string} class pill danger, hoặc '' khi không có cảnh báo.
 */
export function teamAlertChipClass(alert) {
  if (!alert) return ''
  return pillClass('danger')
}

/**
 * M10-1 — nhãn VI chip cảnh báo (kèm chữ — WCAG, không chỉ màu). BE đã trả chuỗi VI 'DS thấp'
 * → hiển thị thẳng; rỗng → '' (không render chip).
 *
 * @param {('DS thấp'|''|string|null|undefined)} alert
 * @returns {string}
 */
export function teamAlertLabel(alert) {
  return alert || ''
}

// ── M10-3 "Hồ sơ NV kinh doanh" (mockup B2 left-card) — helper THUẦN ──────────

/**
 * M10-3 — class chip trạng thái deal trên bảng "Khách hàng phụ trách" theo status_theme BE
 * (antmed_crm.api.antmed.sales_team.rep_profile). KEY khớp EXACT status_theme BE trả:
 *   'ok'     (Won)          → pill ok (xanh)
 *   'danger' (Lost)         → pill danger (đỏ)
 *   'info'   (Open/Ongoing) → pill info (xanh dương)
 * Tái dùng pillClass(PILL_THEME). theme lạ/rỗng → neutral (an toàn, không vỡ). FE KHÔNG tự suy
 * diễn theme từ status (BE đã quyết — đồng nhất phân loại Won/Lost với roster/dispatch).
 * Chip LUÔN kèm CHỮ (status) — không phân biệt chỉ bằng màu (WCAG AA).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component chỉ bind class trả về.
 *
 * @param {('ok'|'danger'|'info'|string|null|undefined)} statusTheme
 * @returns {string} class Tailwind pill.
 */
export function repStatusChipClass(statusTheme) {
  return pillClass(statusTheme || 'neutral')
}

/**
 * M10-3 — format ngày vào làm (joined_on = User.creation, ISO 'yyyy-MM-dd' hoặc datetime).
 * Tái dùng fmtDate (dd/MM/yyyy, parse ISO thủ công tránh lệch TZ). null/thiếu → '—'
 * (KHÔNG bịa — phần không có nguồn render empty). Pure — unit-test trực tiếp.
 *
 * @param {string|Date|null|undefined} value
 * @returns {string} 'dd/MM/yyyy' hoặc '—'.
 */
export function formatJoinDate(value) {
  return fmtDate(value)
}

// ── M10-2 "Bảng điều phối" (mockup B1) — helper THUẦN kanban pipeline ─────────

/**
 * M10-2 — class fill thanh "khả năng chốt" (probability) trên card kanban theo bar_theme BE
 * (antmed_crm.api.antmed.sales_team.dispatch_board). KEY khớp EXACT bar_theme BE trả
 * (green/warn/danger — ngưỡng probability 70/40, BE đã quyết, FE KHÔNG tính lại):
 *   'green'  (>=70) → default (brand teal)
 *   'warn'   (>=40) → warn (cam)
 *   'danger' (<40)  → danger (đỏ)
 * Tái dùng BAR_THEME/barFillClass (map green → default-teal). theme lạ/rỗng → default (xanh, không vỡ).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component chỉ bind class trả về.
 *
 * @param {('green'|'warn'|'danger'|string|null|undefined)} barTheme
 * @returns {string} class Tailwind cho fill thanh (BAR_THEME.default|warn|danger).
 */
export function dispatchBarClass(barTheme) {
  return barFillClass(TEAM_BAR_THEME[barTheme] || 'default')
}

// ── M02-8 "Doanh thu tháng" (mockup A1 KPI hàng 1) — helper THUẦN dòng phụ MoM ─

/**
 * M02-8 — dòng phụ KPI "Doanh thu tháng": ghép month_label + ' · ' + so sánh MoM (vs tháng trước).
 * BE (monthly_revenue) đã tính delta_pct (round 1 chữ số; null khi previous==0). FE CHỈ format +
 * chọn mũi tên theo DẤU (KHÔNG tính lại current/previous/delta — BR rollup ở BE):
 *   delta_pct == null  → 'T<m>/<yyyy> · — vs tháng trước'   (KHÔNG mũi tên, KHÔNG NaN — previous==0)
 *   delta_pct  > 0     → 'T<m>/<yyyy> · ▲ X% vs tháng trước' (tăng — xanh ở view)
 *   delta_pct  < 0     → 'T<m>/<yyyy> · ▼ X% vs tháng trước' (giảm — cam ở view)
 *   delta_pct == 0     → 'T<m>/<yyyy> · 0% vs tháng trước'   (KHÔNG mũi tên)
 * X = Math.abs(delta_pct) (số đã làm tròn 1 chữ số từ BE). monthLabel rỗng/thiếu → bỏ tiền tố
 * (chỉ render phần MoM). Pure (không import frappe-ui) — unit-test trực tiếp.
 *
 * @param {string|null|undefined} monthLabel - 'T<m>/<yyyy>' từ BE.
 * @param {number|null|undefined} deltaPct - delta MoM (%) từ BE; null = previous==0.
 * @returns {string} dòng phụ hiển thị dưới value KPI.
 */
export function formatRevenueSub(monthLabel, deltaPct) {
  let mom
  if (deltaPct === null || deltaPct === undefined) {
    mom = '— vs tháng trước'
  } else {
    const arrow = deltaPct > 0 ? '▲ ' : deltaPct < 0 ? '▼ ' : ''
    mom = `${arrow}${Math.abs(deltaPct)}% vs tháng trước`
  }
  return monthLabel ? `${monthLabel} · ${mom}` : mom
}

// ── M02-9 "Doanh thu theo Nhóm vật tư" (mockup A3 stacked-bar CEO) — màu segment + chiều cao % ──

/**
 * Màu segment 5 nhóm phân loại VTYT (mockup A3 palette teal-thương-hiệu đậm dần → accent → neutral).
 * Map classification (KEY khớp BE 100%) → { bar: class fill segment, swatch: class ô màu legend }.
 * KHÔNG hardcode hex (token Tailwind dự án bám design token §10). Nhóm lạ → fallback 'Khác' (an toàn).
 *   Loại A → teal-700 (brand đậm) · Loại B → teal-500 (brand) · Loại C → teal-300 (brand nhạt) ·
 *   Loại D → amber-400 (accent-warn nhạt) · Khác → neutral ink-gray-4.
 * Pure (không Vue) — component chỉ bind class trả về.
 */
export const REVENUE_GROUP_COLORS = {
  'Loại A': { bar: 'bg-teal-700', swatch: 'bg-teal-700' },
  'Loại B': { bar: 'bg-teal-500', swatch: 'bg-teal-500' },
  'Loại C': { bar: 'bg-teal-300', swatch: 'bg-teal-300' },
  'Loại D': { bar: 'bg-amber-400', swatch: 'bg-amber-400' },
  Khác: { bar: 'bg-ink-gray-4', swatch: 'bg-ink-gray-4' },
}

/**
 * Class fill của 1 segment nhóm trong stacked bar (mockup A3). classification lạ/thiếu → 'Khác'.
 * @param {string} classification - KEY nhóm khớp BE (Loại A/B/C/D/Khác).
 * @returns {string} class Tailwind nền segment.
 */
export function revenueGroupBarClass(classification) {
  return (REVENUE_GROUP_COLORS[classification] || REVENUE_GROUP_COLORS['Khác'])
    .bar
}

/**
 * Class ô màu legend của 1 nhóm (mockup A3). classification lạ/thiếu → 'Khác'.
 * @param {string} classification - KEY nhóm khớp BE.
 * @returns {string} class Tailwind nền ô legend.
 */
export function revenueGroupSwatchClass(classification) {
  return (REVENUE_GROUP_COLORS[classification] || REVENUE_GROUP_COLORS['Khác'])
    .swatch
}

/**
 * Chiều cao % của 1 segment trong cột stacked bar (mockup A3):
 *   heightPct = round(value / columnMax * 100), clamp 0–100.
 *   columnMax <= 0 (mọi cột 0) → 0 (KHÔNG ZeroDivisionError / NaN — KHÔNG vỡ render).
 *   value/columnMax null/undefined/NaN → 0 (segment rỗng).
 *   value > columnMax → 100 (clamp, không vượt khung).
 * columnMax = TỔNG cao nhất trong 12 cột (truyền từ component — FE KHÔNG aggregate dữ liệu BE,
 * chỉ tính tỉ lệ trình bày). Pure (không Vue) — unit-test trực tiếp.
 *
 * @param {number|string|null|undefined} value - giá trị segment (1 nhóm trong 1 tháng).
 * @param {number|string|null|undefined} columnMax - giá trị tổng cao nhất giữa 12 cột.
 * @returns {number} 0–100 (đã round).
 */
export function stackSegmentHeightPct(value, columnMax) {
  const v = Number(value)
  const m = Number(columnMax)
  if (!Number.isFinite(v) || !Number.isFinite(m) || m <= 0) return 0
  let pct = (v / m) * 100
  if (pct < 0) pct = 0
  if (pct > 100) pct = 100
  return Math.round(pct)
}

/**
 * Tổng giá trị mỗi cột tháng (= chiều cao tổng cột stacked bar) — THUẦN TRÌNH BÀY (scale trục Y),
 * KHÔNG phải doanh thu nghiệp vụ (số đã do BE gộp; đây chỉ cộng các segment đã có để quy đổi % cao).
 *   columnTotals[i] = Σ groups[g].monthly[i] (cộng dọc 5 nhóm cho cột i).
 * groups thiếu/lỗi shape → mảng 0 độ dài monthsLen (KHÔNG vỡ). Pure (không Vue) — unit-test trực tiếp.
 *
 * @param {Array<{monthly:number[]}>} groups - groups từ BE (đọc thẳng, KHÔNG sort/sửa).
 * @param {number} monthsLen - số cột (12).
 * @returns {number[]} tổng từng cột.
 */
export function stackColumnTotals(groups, monthsLen) {
  const n = Number(monthsLen)
  const len = Number.isFinite(n) && n > 0 ? Math.floor(n) : 0
  const totals = new Array(len).fill(0)
  if (!Array.isArray(groups)) return totals
  for (const g of groups) {
    const monthly = g && Array.isArray(g.monthly) ? g.monthly : []
    for (let i = 0; i < len; i++) {
      const v = Number(monthly[i])
      if (Number.isFinite(v)) totals[i] += v
    }
  }
  return totals
}

/**
 * Giá trị cột cao nhất (= mốc 100% chiều cao stacked bar) — THUẦN TRÌNH BÀY (scale trục Y).
 * Mọi cột 0 / input lỗi → 0 (stackSegmentHeightPct trả 0 → không vỡ, no ZeroDivision).
 * Pure (không Vue) — unit-test trực tiếp.
 *
 * @param {number[]} columnTotals - tổng từng cột (từ stackColumnTotals).
 * @returns {number} max ≥ 0.
 */
export function stackColumnMax(columnTotals) {
  if (!Array.isArray(columnTotals) || !columnTotals.length) return 0
  let max = 0
  for (const t of columnTotals) {
    const v = Number(t)
    if (Number.isFinite(v) && v > max) max = v
  }
  return max
}

// ── M02-10 "Doanh thu theo NV Kinh doanh × Bệnh viện" (heatmap A3, Dashboard CEO) ─

/**
 * Map mức heat BE (h2c/h3c/h4c/h5c — HEAT_LEVELS) → class nền+chữ cell (mockup A3 .h2c..h5c).
 * 4 mức đỏ tăng dần theo ngưỡng tương đối trên max_cell (Thấp/TB/Cao/Rất cao):
 *   h2c #FECACA → bg-red-200 (Thấp)  · h3c #FCA5A5 → bg-red-300 (TB)
 *   h4c #F87171 → bg-red-400 (Cao)   · h5c #EF4444 → bg-red-500 (Rất cao).
 * heat null/undefined (cell rỗng) → '' (cell '—' không tô màu). KEY khớp EXACT BE export
 * (sales_team.HEAT_LEVELS) — KHÔNG đổi key. KHÔNG hardcode hex (token Tailwind).
 */
export const HEAT_CELL_COLORS = {
  h2c: 'bg-red-200 text-red-900',
  h3c: 'bg-red-300 text-red-900',
  h4c: 'bg-red-400 text-white',
  h5c: 'bg-red-500 text-white',
}
export function heatCellClass(heat) {
  return HEAT_CELL_COLORS[heat] || ''
}

/**
 * Legend 4 mức heat (mockup A3 .legend) — nhãn VI + class swatch khớp HEAT_CELL_COLORS.
 * SSoT (chống drift): page render thẳng mảng này, KHÔNG bịa nhãn/màu rời rạc.
 * Thứ tự tăng dần độ đậm = Thấp → TB → Cao → Rất cao (mockup).
 */
export const HEAT_LEGEND = [
  { key: 'h2c', label: 'Thấp', swatch: 'bg-red-200' },
  { key: 'h3c', label: 'TB', swatch: 'bg-red-300' },
  { key: 'h4c', label: 'Cao', swatch: 'bg-red-400' },
  { key: 'h5c', label: 'Rất cao', swatch: 'bg-red-500' },
]

/**
 * Format giá trị raw VND → đơn vị TRIỆU (cột mockup A3 "Tổng (tr)" — vd 2.000.000.000 → '2.000').
 * Làm tròn về số triệu nguyên, phân tách hàng nghìn kiểu VI (dấu '.'). PURE — chỉ trình bày.
 *   null / undefined / '' / 0 / NaN → '—' (ô rỗng mockup). FE KHÔNG tự tính doanh thu — chỉ đổi đơn vị
 *   hiển thị từ value BE trả (BE giữ raw VND để client quyết định format). KHÔNG aggregate.
 */
export function formatTrieu(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (!Number.isFinite(n) || n === 0) return '—'
  const trieu = Math.round(n / 1_000_000)
  if (trieu === 0) return '—'
  return trieu.toLocaleString('vi-VN', { maximumFractionDigits: 0 })
}

// ── M07-1 Portal BV "📰 Thông báo gần đây" (mockup G1) — mốc thời gian relative VI ──

/**
 * M07-1 — format mốc thời gian relative tiếng Việt cho 1 dòng timeline thông báo (mockup G1 .e):
 *   - cùng ngày (hôm nay)  → 'hôm nay HH:MM'   (giờ:phút zero-pad).
 *   - đúng hôm trước       → 'hôm qua'.
 *   - xa hơn (≥2 ngày)     → 'dd/mm'           (ngày/tháng zero-pad, KHÔNG năm — gọn timeline).
 *   - null/undefined/'' / parse-fail → '—'     (KHÔNG NaN — phần thiếu nguồn render gạch ngang).
 * So sánh theo NGÀY LỊCH local (không theo 24h chênh lệch) — 23:59 hôm nay vs 00:01 hôm nay cùng ngày.
 * Nhận chuỗi datetime Frappe ('yyyy-MM-dd HH:MM:SS' / ISO) hoặc Date. Pure (không Vue/frappe-ui) —
 * unit-test trực tiếp; component chỉ render chuỗi trả về. FE KHÔNG suy diễn nghiệp vụ — chỉ trình bày.
 *
 * @param {string|Date|null|undefined} ts - ts từ BE (posting_datetime / contract.modified).
 * @param {Date} [now] - mốc "bây giờ" (tiêm vào để test ổn định; mặc định new Date()).
 * @returns {string} nhãn relative VI hoặc '—'.
 */
export function formatNotifTime(ts, now = new Date()) {
  if (ts === null || ts === undefined || ts === '') return '—'
  const d =
    ts instanceof Date
      ? ts
      : new Date(typeof ts === 'string' ? ts.replace(' ', 'T') : ts)
  if (Number.isNaN(d.getTime())) return '—'
  const p = (x) => String(x).padStart(2, '0')
  // Số ngày lịch chênh lệch (theo ngày local, bỏ phần giờ — tránh lệch do giờ trong ngày).
  const dayOf = (x) =>
    new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const diffDays = Math.round((dayOf(now) - dayOf(d)) / 86_400_000)
  if (diffDays === 0) return `hôm nay ${p(d.getHours())}:${p(d.getMinutes())}`
  if (diffDays === 1) return 'hôm qua'
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}`
}

// ── M07-2 Portal BV "📋 Danh mục vật tư trúng thầu" (mockup G1 .pill) — chip quota ──

/**
 * M07-2 — class chip quota trên danh mục VT trúng thầu theo quota_chip BE
 * (antmed_crm.api.antmed.customer.tender_catalog). KEY khớp EXACT quota_chip BE trả
 * (BE đã phân tầng THẬT theo remaining_pct — FE KHÔNG tính lại ngưỡng):
 *   'ok'     (>10% còn)        → pill ok (xanh — 'Còn quota')
 *   'warn'   (>0% và ≤10% còn) → pill warn (cam — 'Còn X%')
 *   'danger' (≤0% = hết quota) → pill danger (đỏ — 'Hết quota')
 * Tái dùng pillClass(PILL_THEME) — chip lạ/rỗng → neutral (an toàn, không vỡ render).
 * Chip LUÔN kèm CHỮ (tenderQuotaChipLabel) — không phân biệt chỉ bằng màu (WCAG AA).
 * Pure (không import frappe-ui) — unit-test trực tiếp; component chỉ bind class trả về.
 *
 * @param {('ok'|'warn'|'danger'|string|null|undefined)} quotaChip
 * @returns {string} class Tailwind pill (PILL_THEME.ok|warn|danger|neutral).
 */
export const TENDER_QUOTA_CHIP_THEME = {
  ok: 'ok',
  warn: 'warn',
  danger: 'danger',
}
export function tenderQuotaChipClass(quotaChip) {
  return pillClass(TENDER_QUOTA_CHIP_THEME[quotaChip] || 'neutral')
}

/**
 * M07-2 — nhãn VI cho chip quota (kèm chữ — WCAG, không chỉ màu). KEY khớp EXACT quota_chip BE:
 *   'ok'     → 'Còn quota'.
 *   'warn'   → 'Còn X%'   (X = remaining_pct truyền vào, format VI gọn — số còn lại).
 *   'danger' → 'Hết quota'.
 * Chip lạ/rỗng → 'Còn quota' (fallback an toàn, vẫn chữ VI). FE KHÔNG suy diễn ngưỡng (BE quyết).
 * remaining_pct dùng cho nhãn 'warn'; null/NaN ở nhánh warn → '0' (không NaN). Pure — unit-test trực tiếp.
 *
 * @param {('ok'|'warn'|'danger'|string|null|undefined)} quotaChip
 * @param {number|string|null|undefined} [remainingPct] - % còn lại (chỉ dùng cho nhãn 'warn').
 * @returns {string} nhãn tiếng Việt.
 */
export function tenderQuotaChipLabel(quotaChip, remainingPct) {
  if (quotaChip === 'danger') return 'Hết quota'
  if (quotaChip === 'warn') {
    const n = Number(remainingPct)
    const pct = Number.isFinite(n)
      ? n.toLocaleString('vi-VN', { maximumFractionDigits: 1 })
      : '0'
    return `Còn ${pct}%`
  }
  return 'Còn quota'
}

/**
 * M07-1 — 3 quick-action card TĨNH header Portal BV (mockup G1 .cardrow.cols-3). SSoT nhãn VI:
 * icon + tiêu đề + dòng phụ khớp 100% mockup. `to` = đích điều hướng placeholder (vòng này nav-only,
 * CHƯA có form → trỏ /antmed/portal; bật route thật ở vòng M07 sau). `primary` = ô brand (Gọi vật tư).
 * Đổi card = sửa DUY NHẤT mảng này (page render v-for từ đây — KHÔNG hardcode JSX rời rạc).
 */
export const PORTAL_QUICK_ACTIONS = [
  {
    key: 'call-supply',
    icon: '🩺',
    title: 'Gọi vật tư cho ca mổ',
    sub: 'Trong danh mục trúng thầu',
    to: '/antmed/portal',
    primary: true,
  },
  {
    key: 'loan-instrument',
    icon: '🧰',
    title: 'Mượn bộ dụng cụ',
    sub: 'Đặt trước ca mổ',
    to: '/antmed/portal',
    primary: false,
  },
  {
    key: 'lookup-docs',
    icon: '📄',
    title: 'Tra cứu chứng từ',
    sub: 'Hóa đơn, CO/CQ, phiếu giao',
    to: '/antmed/portal/history',
    primary: false,
  },
]

// ── M06-1: helper chip màn "Hàng chờ phát hành chứng từ" (mockup E1) ──
// PURE (không import Vue/frappe-ui) → unit-test trực tiếp. Mirror BE _parse_chips/_chip_text
// để FE render CHÍNH XÁC theo nội dung missing_chips (KHÔNG tự suy logic nghiệp vụ — chỉ render).

/**
 * Parse missing_chips (chuỗi JSON list từ BE) → mảng, null-guard FE-side (mirror BE _parse_chips).
 * None/undefined/'' / JSON hỏng → [] (KHÔNG throw). Đã là mảng → trả nguyên. Giá trị không-mảng
 * (dict/số) → [] để chip không lệch. Bám robustness BE: chip hỏng KHÔNG vỡ render.
 *
 * @param {string|Array|null|undefined} raw
 * @returns {Array}
 */
export function parseMissingChips(raw) {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  if (typeof raw !== 'string') return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

/**
 * Cờ thiếu CO / CQ từ missing_chips — dò token 'CO'/'CQ' trong chuỗi chip (chip dạng 'CO lot L-9930').
 * Mirror BE: "CO" in text / "CQ" in text. Dùng cho chip 'Thiếu CO' / 'Thiếu CQ' trên từng dòng.
 *
 * @param {string|Array|null|undefined} raw - missing_chips (raw hoặc đã parse).
 * @returns {{ co: boolean, cq: boolean }}
 */
export function releaseChipFlags(raw) {
  const chips = parseMissingChips(raw)
  const text = chips.map((c) => String(c)).join(' ')
  return { co: text.includes('CO'), cq: text.includes('CQ') }
}

/**
 * Chip TRẠNG THÁI dòng hàng chờ (mockup E1, 2 nhóm) — KÈM CHỮ (WCAG AA, không chỉ màu):
 *   - status='Chờ phát hành' AND missing_chips RỖNG (đủ CO+CQ) → 'Sẵn sàng phát hành', theme 'ok' (green).
 *   - còn lại (Thiếu chứng từ / Chờ phát hành nhưng missing≠[]) → 'Mở', theme 'warn' (amber).
 *   - status 'Đã phát hành'/khác (đã rời hàng chờ) → label = chính status (neutral) để không lệch.
 * status KEY khớp EXACT options DocType `AntMed Document Release Queue.status` (VI có dấu) — KHÔNG đổi key.
 *
 * @param {string} status - workflow/status VI từ BE.
 * @param {string|Array|null|undefined} rawChips - missing_chips.
 * @returns {{ label: string, theme: ('ok'|'warn'|'neutral') }}
 */
export function releaseStatusChip(status, rawChips) {
  const chips = parseMissingChips(rawChips)
  if (status === 'Chờ phát hành' && chips.length === 0) {
    return { label: 'Sẵn sàng phát hành', theme: 'ok' }
  }
  if (status === 'Chờ phát hành' || status === 'Thiếu chứng từ') {
    return { label: 'Mở', theme: 'warn' }
  }
  // Trạng thái khác (đã rời hàng chờ) — hiển thị nguyên status VI, tone trung tính.
  return { label: status || '—', theme: 'neutral' }
}
