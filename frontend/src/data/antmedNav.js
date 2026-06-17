/**
 * AntMed SPA — single source danh sách điều hướng cho app shell (sidebar mockup A1).
 *
 * Tham chiếu mockup: docs/docs/AntMed_CRM_Full_Mockups.html (sidebar nav).
 * Mỗi item:
 *   - key:     định danh ổn định (test + active-state).
 *   - label:   nhãn tiếng Việt hiển thị.
 *   - icon:    emoji glyph (khớp mockup; nhẹ, không cần icon-set).
 *   - to:      path SPA (vue-router).
 *   - enabled: true = route đã build (điều hướng được);
 *              false = module chưa build → render "Sắp có", KHÔNG điều hướng (tránh dead-link).
 *
 * Đổi/thêm màn = sửa DUY NHẤT ở đây (sidebar render từ mảng này). Khi build module mới
 * (M02 Hợp đồng, M03 Tồn kho, …) → bật enabled=true + thêm route tương ứng trong router.js.
 */
export const ANTMED_NAV = [
  { key: 'dashboard', label: 'Dashboard', icon: '📊', to: '/antmed', enabled: true },
  { key: 'hospitals', label: 'Bệnh viện', icon: '🏥', to: '/antmed/hospitals', enabled: true },
  { key: 'contracts', label: 'Hợp đồng', icon: '📋', to: '/antmed/contracts', enabled: true },
  { key: 'inventory', label: 'Tồn kho', icon: '📦', to: '/antmed/inventory', enabled: false },
  { key: 'deliveries', label: 'Giao phòng mổ', icon: '🚚', to: '/antmed/deliveries', enabled: false },
  { key: 'instruments', label: 'Bộ dụng cụ', icon: '🧰', to: '/antmed/instruments', enabled: false },
  { key: 'documents', label: 'Chứng từ', icon: '📄', to: '/antmed/documents', enabled: false },
  { key: 'kpi', label: 'KPI', icon: '👥', to: '/antmed/kpi', enabled: false },
  { key: 'reports', label: 'Báo cáo', icon: '📈', to: '/antmed/reports', enabled: false },
]

/**
 * Item có đang active với `path` hiện tại không.
 *
 * Lưu ý edge-case: MỌI path AntMed đều bắt đầu bằng '/antmed', nên Dashboard ('/antmed')
 * chỉ active khi path TRÙNG KHỚP (exact) — không dùng prefix, nếu không Dashboard sẽ
 * luôn active ở mọi trang con. Các item khác active khi path == to hoặc là sub-route (to + '/').
 *
 * @param {{to?: string}} item
 * @param {string} path
 * @returns {boolean}
 */
export function isNavActive(item, path) {
  if (!item || typeof item.to !== 'string' || typeof path !== 'string') return false
  if (item.to === '/antmed') return path === '/antmed' || path === '/antmed/'
  return path === item.to || path.startsWith(item.to + '/')
}
