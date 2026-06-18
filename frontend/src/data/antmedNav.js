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
  {
    key: 'dashboard',
    label: 'Dashboard',
    icon: '📊',
    to: '/antmed',
    enabled: true,
  },
  {
    key: 'hospitals',
    label: 'Bệnh viện',
    icon: '🏥',
    to: '/antmed/hospitals',
    enabled: true,
  },
  {
    key: 'contracts',
    label: 'Hợp đồng',
    icon: '📋',
    to: '/antmed/contracts',
    enabled: true,
  },
  {
    // M02-2 (mockup A2) — màn "Sức khỏe Hợp đồng": quota + hạn HĐ. Route real-data đã build.
    key: 'contract-health',
    label: 'Sức khỏe Hợp đồng',
    icon: '🩺',
    to: '/antmed/contract-health',
    enabled: true,
  },
  {
    key: 'inventory',
    label: 'Tồn kho',
    icon: '📦',
    to: '/antmed/inventory',
    enabled: false,
  },
  {
    // M04 Slice S1: route /antmed/deliveries đã build (list real-data) → bật nav.
    key: 'deliveries',
    label: 'Giao phòng mổ',
    icon: '🚚',
    to: '/antmed/deliveries',
    enabled: true,
  },
  {
    key: 'instruments',
    label: 'Bộ dụng cụ',
    icon: '🧰',
    to: '/antmed/instruments',
    enabled: true,
  },
  {
    key: 'documents',
    label: 'Chứng từ',
    icon: '📄',
    to: '/antmed/documents',
    enabled: false,
  },
  { key: 'kpi', label: 'KPI', icon: '👥', to: '/antmed/kpi', enabled: false },
  {
    key: 'reports',
    label: 'Báo cáo',
    icon: '📈',
    to: '/antmed/reports',
    enabled: false,
  },
]

/**
 * Sidebar TOÀN DIỆN (grouped) — nguồn duy nhất cho điều hướng mặc định AntMed.
 * Gom MỌI màn real-data /antmed/* đã build theo nhóm chức năng → từ /antmed user
 * truy cập được đầy đủ tính năng (KHÔNG ẩn sau role switcher, KHÔNG trỏ stub /ceo,/portal).
 * Thêm màn mới = thêm item vào section tương ứng (kèm route thật trong router.js).
 */
export const ANTMED_SECTIONS = [
  {
    title: 'Điều hành',
    items: [
      {
        key: 'dashboard',
        label: 'Dashboard',
        icon: '📊',
        to: '/antmed',
        enabled: true,
      },
      {
        key: 'revenue',
        label: 'Báo cáo Doanh thu',
        icon: '💰',
        to: '/antmed/revenue',
        enabled: true,
      },
      {
        key: 'alerts',
        label: 'Cảnh báo điều hành',
        icon: '⚠',
        to: '/antmed/alerts',
        enabled: true,
      },
    ],
  },
  {
    title: 'Khách hàng & Hợp đồng',
    items: [
      {
        key: 'hospitals',
        label: 'Bệnh viện',
        icon: '🏥',
        to: '/antmed/hospitals',
        enabled: true,
      },
      {
        key: 'contracts',
        label: 'Hợp đồng',
        icon: '📋',
        to: '/antmed/contracts',
        enabled: true,
      },
    ],
  },
  {
    title: 'Kinh doanh',
    items: [
      {
        key: 'leads',
        label: 'Quản lý Lead',
        icon: '🧲',
        to: '/antmed/leads',
        enabled: true,
      },
      {
        // M08 (GỘP): pipeline cơ hội = CRM Deal (kéo-thả). Gói thầu = field am_* trên Deal.
        key: 'deal-pipeline',
        label: 'Pipeline cơ hội (Deal)',
        icon: '📈',
        to: '/antmed/deals',
        enabled: true,
      },
      {
        key: 'dispatch',
        label: 'Bảng điều phối',
        icon: '🚦',
        to: '/antmed/sales/dispatch',
        enabled: true,
      },
      {
        // M04 S1: list phiếu Giao phòng mổ (real-data delivery.list_deliveries).
        key: 'deliveries',
        label: 'Giao phòng mổ',
        icon: '🚚',
        to: '/antmed/deliveries',
        enabled: true,
      },
      {
        key: 'team',
        label: 'Quản lý đội ngũ',
        icon: '👥',
        to: '/antmed/sales/team',
        enabled: true,
      },
      {
        key: 'tasks',
        label: 'Công việc',
        icon: '✅',
        to: '/antmed/tasks',
        enabled: true,
      },
    ],
  },
  {
    title: 'Kho vận',
    items: [
      {
        key: 'stock-entries',
        label: 'Phiếu xuất kho',
        icon: '📤',
        to: '/antmed/warehouse/stock-entries',
        enabled: true,
      },
      {
        key: 'consignment',
        label: 'Kho ký gửi BV',
        icon: '🏥',
        to: '/antmed/warehouse/consignment',
        enabled: true,
      },
      {
        key: 'lot-trace',
        label: 'Truy vết lot',
        icon: '🔍',
        to: '/antmed/warehouse/lot-trace',
        enabled: true,
      },
      {
        key: 'expiry-alerts',
        label: 'Cảnh báo HSD',
        icon: '⏰',
        to: '/antmed/warehouse/expiry-alerts',
        enabled: true,
      },
      {
        key: 'instruments',
        label: 'Bộ dụng cụ',
        icon: '🧰',
        to: '/antmed/instruments',
        enabled: true,
      },
    ],
  },
  {
    title: 'Tài chính',
    items: [
      {
        key: 'commission',
        label: 'Hoa hồng NV',
        icon: '💼',
        to: '/antmed/finance/commission',
        enabled: true,
      },
    ],
  },
  {
    title: 'Portal Bệnh viện',
    items: [
      {
        key: 'portal',
        label: 'Trang chủ Portal',
        icon: '🏠',
        to: '/antmed/portal',
        enabled: true,
      },
    ],
  },
  {
    title: 'Quản trị',
    items: [
      {
        key: 'admin-users',
        label: 'User & Role',
        icon: '👥',
        to: '/antmed/admin/users',
        enabled: true,
      },
    ],
  },
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
  if (!item || typeof item.to !== 'string' || typeof path !== 'string')
    return false
  if (item.to === '/antmed') return path === '/antmed' || path === '/antmed/'
  return path === item.to || path.startsWith(item.to + '/')
}

/**
 * T3 — Shell ROLE-AWARE: 8 vai trò mockup (docs/.../AntMed_CRM_Full_Mockups.html).
 * Mỗi role có sidebar riêng (ROLE_NAV). `variant:'portal'` = topbar trắng (vai trò G);
 * `mobile:true` = NV kinh doanh dùng phone-frame (tabbar) thay sidebar.
 */
export const ANTMED_ROLES = [
  { key: 'ceo', label: 'CEO / Ban GĐ', avatar: 'CEO' },
  { key: 'sales', label: 'Trưởng KD', avatar: 'TK' },
  { key: 'rep', label: 'NV Kinh doanh', avatar: 'NA', mobile: true },
  { key: 'warehouse', label: 'Thủ kho Tổng', avatar: 'TK' },
  { key: 'docs', label: 'Chứng từ / Pháp lý', avatar: 'CT' },
  { key: 'finance', label: 'Kế toán', avatar: 'KT' },
  {
    key: 'portal',
    label: 'Portal Bác sỹ / BV',
    avatar: 'TH',
    variant: 'portal',
  },
  { key: 'admin', label: 'System Admin', avatar: 'AD' },
]

/**
 * Nav theo vai trò — labels/icons bám sidebar mockup. `to` = route role-prefixed
 * (T4 đăng ký). `enabled:false` ⇒ render "Sắp có" (tránh dead-link tới khi T4/T5+
 * dựng route/màn). T4 sẽ bật enabled khi route tồn tại.
 */
export const ROLE_NAV = {
  ceo: [
    {
      key: 'ceo-dash',
      label: 'Dashboard',
      icon: '📊',
      to: '/antmed',
      enabled: true,
    },
    {
      // M02-2 (mockup A2 id=ceo, sidebar "Hợp đồng" active) — trỏ màn real-data "Sức khỏe Hợp đồng".
      key: 'ceo-contracts',
      label: 'Hợp đồng',
      icon: '📋',
      to: '/antmed/contract-health',
      enabled: true,
    },
    {
      // M02-3 (mockup A1 widget ⚠ "Cảnh báo điều hành") — màn real-data list_quota_alerts.
      key: 'ceo-alerts',
      label: 'Cảnh báo',
      icon: '⚠',
      to: '/antmed/alerts',
      enabled: true,
    },
    {
      // M02-9 (mockup A3 id=ceo) — trỏ màn real-data "Doanh thu theo Nhóm vật tư" (/antmed/revenue).
      key: 'ceo-revenue',
      label: 'Doanh thu',
      icon: '💰',
      to: '/antmed/revenue',
      enabled: true,
    },
    {
      key: 'ceo-inventory',
      label: 'Tồn kho',
      icon: '📦',
      to: '/warehouse/consignment',
      enabled: false,
    },
    {
      key: 'ceo-instruments',
      label: 'Bộ dụng cụ',
      icon: '🧰',
      to: '/instruments',
      enabled: false,
    },
    {
      key: 'ceo-kpi',
      label: 'KPI NS',
      icon: '👥',
      to: '/sales/team',
      enabled: false,
    },
    {
      key: 'ceo-reports',
      label: 'Báo cáo',
      icon: '📈',
      to: '/ceo/revenue',
      enabled: false,
    },
  ],
  sales: [
    {
      // M10-2: trỏ màn real-data "Bảng điều phối" (/antmed/sales/dispatch, mockup B1).
      // Route prototype /sales/dispatch giữ nguyên (no-regression) nhưng KHÔNG còn là đích nav.
      key: 'sales-dispatch',
      label: 'Điều phối',
      icon: '🎯',
      to: '/antmed/sales/dispatch',
      enabled: true,
    },
    {
      key: 'sales-approvals',
      label: 'Duyệt yêu cầu',
      icon: '📥',
      to: '/sales/approvals',
      enabled: false,
    },
    {
      // M10-1: trỏ màn real-data "Quản lý Đội ngũ" (/antmed/sales/team, mockup B2).
      // Route prototype /sales/team giữ nguyên (no-regression) nhưng KHÔNG còn là đích nav.
      key: 'sales-team',
      label: 'Đội ngũ',
      icon: '👥',
      to: '/antmed/sales/team',
      enabled: true,
    },
    {
      key: 'sales-customers',
      label: 'Khách hàng',
      icon: '🏥',
      to: '/antmed/hospitals',
      enabled: true,
    },
    {
      key: 'sales-instruments',
      label: 'Bộ dụng cụ',
      icon: '🧰',
      to: '/instruments',
      enabled: false,
    },
  ],
  rep: [
    {
      key: 'rep-home',
      label: 'Trang chủ',
      icon: '🏠',
      to: '/rep',
      enabled: false,
    },
    {
      key: 'rep-wizard',
      label: 'Giao hàng',
      icon: '🚚',
      to: '/rep/wizard',
      enabled: false,
    },
    {
      key: 'rep-checklist',
      label: 'Bộ dụng cụ',
      icon: '🧰',
      to: '/rep/checklist',
      enabled: false,
    },
    {
      key: 'rep-doctor',
      label: 'CRM Bác sỹ',
      icon: '👨‍⚕️',
      to: '/rep/doctor',
      enabled: false,
    },
    {
      key: 'rep-offline',
      label: 'Offline',
      icon: '📴',
      to: '/rep/offline',
      enabled: false,
    },
  ],
  warehouse: [
    {
      // M03-S4: trỏ màn real-data "Nhập kho" từ NCC (/antmed/warehouse/import).
      key: 'wh-import',
      label: 'Nhập kho',
      icon: '📥',
      to: '/antmed/warehouse/import',
      enabled: true,
    },
    {
      // M03-S4: trỏ Wizard real-data "Xuất cho NV" (/antmed/warehouse/issue — quét QR + CO/CQ + FIFO).
      // Route /antmed/warehouse/stock-entries giữ nguyên (list "Phiếu xuất gần đây") nhưng KHÔNG còn là đích nav.
      key: 'wh-export',
      label: 'Xuất cho NV',
      icon: '📤',
      to: '/antmed/warehouse/issue',
      enabled: true,
    },
    {
      // M03-3: trỏ màn real-data "Kho ký gửi tại Bệnh viện" (/antmed/warehouse/consignment).
      // Route prototype /warehouse/consignment giữ nguyên (no-regression) nhưng KHÔNG còn là đích nav.
      key: 'wh-consignment',
      label: 'Kho ký gửi BV',
      icon: '🏥',
      to: '/antmed/warehouse/consignment',
      enabled: true,
    },
    {
      // M03-S5: màn real-data "Kiểm kê" (snapshot tồn × thực đếm × chênh lệch). Thứ tự mockup:
      // Nhập → Xuất → Ký gửi → Kiểm kê → Truy vết → Cảnh báo HSD.
      key: 'wh-stock-count',
      label: 'Kiểm kê',
      icon: '📊',
      to: '/antmed/warehouse/stock-count',
      enabled: true,
    },
    {
      // M03 D3: màn "Quản lý lot" (list + lọc + drill 'Truy vết').
      key: 'wh-lots',
      label: 'Quản lý lot',
      icon: '📦',
      to: '/antmed/warehouse/lots',
      enabled: true,
    },
    {
      // M03-2: trỏ màn real-data "Thông tin lot" (/antmed/warehouse/lot-trace).
      // Route prototype /warehouse/lot-trace giữ nguyên (no-regression) nhưng KHÔNG còn là đích nav.
      key: 'wh-lot-trace',
      label: 'Truy vết lot',
      icon: '🔍',
      to: '/antmed/warehouse/lot-trace',
      enabled: true,
    },
    {
      // M03-4: màn real-data "Cảnh báo HSD" (mockup D1 sidebar ⚠) — rollup lô cận/quá date toàn kho.
      key: 'wh-expiry',
      label: 'Cảnh báo HSD',
      icon: '⚠',
      to: '/antmed/warehouse/expiry-alerts',
      enabled: true,
    },
    {
      key: 'wh-instruments',
      label: 'Bộ dụng cụ',
      icon: '🧰',
      to: '/instruments',
      enabled: false,
    },
  ],
  docs: [
    {
      key: 'docs-pending',
      label: 'Hàng chờ',
      icon: '📥',
      to: '/docs/pending',
      enabled: false,
    },
    {
      key: 'docs-co-cq',
      label: 'Kho CO/CQ',
      icon: '📂',
      to: '/docs/co-cq',
      enabled: false,
    },
    {
      key: 'docs-einvoice',
      label: 'Hóa đơn điện tử',
      icon: '🧾',
      to: '/docs/pending',
      enabled: false,
    },
    {
      key: 'docs-reconciliation',
      label: 'Đối soát ký nhận',
      icon: '✍',
      to: '/docs/reconciliation',
      enabled: false,
    },
  ],
  finance: [
    {
      key: 'fin-invoices',
      label: 'Hóa đơn',
      icon: '🧾',
      to: '/finance/receivables',
      enabled: false,
    },
    {
      key: 'fin-receivables',
      label: 'Công nợ',
      icon: '💳',
      to: '/finance/receivables',
      enabled: false,
    },
    {
      key: 'fin-commission',
      label: 'Hoa hồng NV',
      icon: '💼',
      to: '/antmed/finance/commission',
      enabled: true,
    },
  ],
  portal: [
    {
      // M07-1: màn real-data "Portal Bệnh viện — Trang chủ" (/antmed/portal, mockup G1).
      key: 'portal-home',
      label: 'Trang chủ Portal',
      icon: '🏠',
      to: '/antmed/portal',
      enabled: true,
    },
    {
      key: 'portal-call',
      label: 'Gọi vật tư',
      icon: '🩺',
      to: '/portal',
      enabled: false,
    },
    {
      key: 'portal-loan',
      label: 'Mượn bộ dụng cụ',
      icon: '🧰',
      to: '/portal',
      enabled: false,
    },
    {
      key: 'portal-history',
      label: 'Lịch sử & chứng từ',
      icon: '📄',
      to: '/portal/history',
      enabled: false,
    },
  ],
  admin: [
    {
      key: 'admin-users',
      label: 'User & Role',
      icon: '👥',
      to: '/antmed/admin/users',
      enabled: true,
    },
    {
      key: 'admin-rules',
      label: 'Quy tắc KD',
      icon: '📜',
      to: '/admin/users',
      enabled: false,
    },
    {
      key: 'admin-audit',
      label: 'Audit log',
      icon: '🔍',
      to: '/admin/audit',
      enabled: false,
    },
    {
      key: 'admin-integrations',
      label: 'Tích hợp',
      icon: '🔌',
      to: '/admin/users',
      enabled: false,
    },
  ],
}

/**
 * Nav cho 1 vai trò. Role lạ/rỗng/undefined → ANTMED_NAV (giữ shell `/antmed/*`
 * real-data cũ, no-regression). Single-source: đổi nav = sửa ROLE_NAV ở đây.
 *
 * @param {string} [role]
 * @returns {Array}
 */
export function navForRole(role) {
  return ROLE_NAV[role] || ANTMED_NAV
}
