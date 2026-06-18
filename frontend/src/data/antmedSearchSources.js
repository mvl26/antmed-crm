/**
 * Nguồn dữ liệu thuần cho command palette quick-search (header AntMed).
 * Tách khỏi component để UNIT-TEST được (vitest) — không phụ thuộc Vue/DOM.
 *
 * searchFunctions(query): match CHỨC NĂNG client-side từ ANTMED_SECTIONS
 * (chỉ item enabled, dedup theo `to`), bỏ dấu tiếng Việt. records (BV/HĐ) đi
 * qua endpoint global_search — KHÔNG nằm ở đây.
 */
import { ANTMED_SECTIONS } from './antmedNav'

// emoji nav (antmedNav) → tên icon feather (frappe-ui FeatherIcon) cho palette.
const EMOJI_FEATHER = {
  '📊': 'bar-chart-2',
  '💰': 'dollar-sign',
  '⚠': 'alert-triangle',
  '🏥': 'home',
  '📋': 'clipboard',
  '📄': 'file-text',
  '🎯': 'target',
  '🚚': 'truck',
  '👥': 'users',
  '📤': 'upload',
  '🔍': 'search',
  '⏰': 'clock',
  '🧰': 'box',
  '🏠': 'home',
  '💼': 'briefcase',
  '🩺': 'activity',
  '🧲': 'zap',
  '✅': 'check-square',
}

export function featherFor(emoji) {
  return EMOJI_FEATHER[emoji] || 'chevron-right'
}

/** Bỏ dấu tiếng Việt + lowercase + trim → so khớp không phân biệt dấu. */
export function normalize(s) {
  return (s || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .trim()
}

const MAX_FUNCTIONS = 8

// Item nav enabled, dedup theo `to` (single source = ANTMED_SECTIONS).
function navItems() {
  const seen = new Set()
  const out = []
  for (const sec of ANTMED_SECTIONS) {
    for (const it of sec.items || []) {
      if (!it.enabled || seen.has(it.to)) continue
      seen.add(it.to)
      out.push(it)
    }
  }
  return out
}

/**
 * Match chức năng cho palette.
 * @param {string} query
 * @returns {Array<{type:'function', key:string, label:string, icon:string, to:string}>}
 */
export function searchFunctions(query) {
  const q = normalize(query)
  const items = navItems()
  const matched = q
    ? items.filter((it) => normalize(it.label).includes(q))
    : items.slice(0, MAX_FUNCTIONS)
  return matched.slice(0, MAX_FUNCTIONS).map((it) => ({
    type: 'function',
    key: it.key,
    label: it.label,
    icon: featherFor(it.icon),
    to: it.to,
  }))
}
