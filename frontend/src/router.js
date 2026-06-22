import { createRouter, createWebHistory } from 'vue-router'
import { usersStore } from '@/stores/users'
import { sessionStore } from '@/stores/session'
import { isAntmedUser, isAntmedOnlyKeptRoute } from '@/utils/antmed'
import { shouldRedirectNotPermitted } from '@/utils/antmedGuard'

const routes = [
  {
    path: '/',
    name: 'Home',
  },
  // ── Phase 2 — CHỈ DÙNG UI AntMed: ĐÃ GỠ TOÀN BỘ route CRM gốc ───────────────
  // (notifications/dashboard/leads/deals/notes/tasks/contacts/organizations/call-logs/data-import).
  // Page + cụm component CRM gốc đã xoá. Mọi điều hướng tới chúng → guard redirect /antmed
  // (no-match → isAntmedOnlyKeptRoute=false). Doctype CRM (Deal/Lead...) GIỮ làm data layer.
  {
    path: '/antmed',
    name: 'AntmedHome',
    component: () => import('@/pages/AntmedHome.vue'),
  },
  {
    // Trang đăng nhập AntMed (guest-accessible, full-screen — App.vue render guest KHÔNG layout).
    path: '/antmed/login',
    name: 'AntmedLogin',
    component: () => import('@/pages/AntmedLogin.vue'),
  },
  {
    path: '/antmed/hospitals',
    name: 'AntmedHospitalList',
    component: () => import('@/pages/AntmedHospitalList.vue'),
  },
  {
    path: '/antmed/contracts',
    name: 'AntmedContracts',
    component: () => import('@/pages/AntmedContracts.vue'),
  },
  {
    path: '/antmed/contracts/:name',
    name: 'AntmedContractDetail',
    component: () => import('@/pages/AntmedContractDetail.vue'),
    props: true,
  },
  {
    // M04 Slice S1: Giao phòng mổ — list phiếu giao (real-data delivery.list_deliveries).
    path: '/antmed/deliveries',
    name: 'AntmedDeliveries',
    component: () => import('@/pages/AntmedDeliveries.vue'),
  },
  {
    // M04 S1: chi tiết phiếu giao (delivery.get_delivery) — header + items[].
    path: '/antmed/deliveries/:name',
    name: 'AntmedDeliveryDetail',
    component: () => import('@/pages/AntmedDeliveryDetail.vue'),
    props: true,
  },
  {
    // M02-2: màn "Sức khỏe Hợp đồng" (mockup A2) — real-data, render trong AntmedLayout.
    path: '/antmed/contract-health',
    name: 'AntmedContractHealth',
    component: () => import('@/pages/AntmedContractHealth.vue'),
  },
  {
    // M02-3: màn "Cảnh báo điều hành" (mockup A1 widget ⚠, id=ceo) — real-data,
    // render trong AntmedLayout (isAntmedPath '/antmed/*'). meta.role='ceo' ⇒ sidebar CEO.
    path: '/antmed/alerts',
    name: 'AntmedAlerts',
    meta: { role: 'ceo' },
    component: () => import('@/pages/AntmedAlerts.vue'),
  },
  {
    // M02-9: man real-data widget stacked-bar (mockup A3 id=ceo) — render trong AntmedLayout
    // (isAntmedPath '/antmed/*'). meta.role='ceo' => sidebar CEO. Mock A3 giu o /ceo/revenue.
    path: '/antmed/revenue',
    name: 'AntmedRevenuePage',
    meta: { antmedShell: true, role: 'ceo' },
    component: () => import('@/pages/AntmedRevenuePage.vue'),
  },
  {
    // M03-1: màn "Phiếu xuất gần đây" — real-data, render trong AntmedLayout
    // (isAntmedPath '/antmed/*'). meta.role='warehouse' ⇒ sidebar kho (wh-export active).
    path: '/antmed/warehouse/stock-entries',
    name: 'AntmedStockEntries',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedStockEntries.vue'),
  },
  {
    // M03-8: màn "Chi tiết phiếu xuất / Vật tư đã chuẩn bị" (mockup C2 Wizard bước 3) — drill-down
    // từ list "Phiếu xuất gần đây". real-data, render trong AntmedLayout (isAntmedPath '/antmed/*').
    // meta.role='warehouse' ⇒ sidebar kho (wh-export active, cùng nhóm list phiếu xuất).
    path: '/antmed/warehouse/stock-entries/:name',
    name: 'AntmedStockEntryDetail',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedStockEntryDetail.vue'),
  },
  {
    // M03 D3: màn danh sách & lọc lô (item/HSD/recall) + drill 'Truy vết' (?lot=).
    path: '/antmed/warehouse/lots',
    name: 'AntmedLotList',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedLotList.vue'),
  },
  {
    // M03-2: màn "Thông tin lot" (mockup D3 left-card) — real-data, render trong AntmedLayout
    // (isAntmedPath '/antmed/*'). meta.role='warehouse' ⇒ sidebar kho (wh-lot-trace active).
    path: '/antmed/warehouse/lot-trace',
    name: 'AntmedLotTrace',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedLotTrace.vue'),
  },
  {
    // M03-3: màn "Kho ký gửi tại Bệnh viện" (mockup D2) — real-data, render trong AntmedLayout
    // (isAntmedPath '/antmed/*'). meta.role='warehouse' ⇒ sidebar kho (wh-consignment active).
    path: '/antmed/warehouse/consignment',
    name: 'AntmedConsignment',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedConsignment.vue'),
  },
  {
    // M03-4: màn "Cảnh báo HSD" (mockup D1 sidebar ⚠) — real-data, render trong AntmedLayout
    // (isAntmedPath '/antmed/*'). meta.role='warehouse' ⇒ sidebar kho (wh-expiry active).
    path: '/antmed/warehouse/expiry-alerts',
    name: 'AntmedExpiryAlerts',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedExpiryAlerts.vue'),
  },
  {
    // M03-S4: Wizard "Xuất cho NV" (mockup C2) — quét QR + FIFO + chip CO/CQ → lập phiếu xuất.
    // real-data, render trong AntmedLayout. meta.role='warehouse' ⇒ sidebar kho (wh-export active).
    path: '/antmed/warehouse/issue',
    name: 'AntmedStockIssue',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedStockIssue.vue'),
  },
  {
    // M03-S4: "Nhập kho" từ NCC — quét QR + SL/đơn giá → lập phiếu nhập (đơn giản, KHÔNG gate CO/CQ).
    path: '/antmed/warehouse/import',
    name: 'AntmedStockReceipt',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedStockReceipt.vue'),
  },
  {
    // M03-S5: "Kiểm kê" — snapshot tồn × SL thực đếm × chênh lệch live → chốt điều chỉnh sổ tồn.
    path: '/antmed/warehouse/stock-count',
    name: 'AntmedStockCount',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedStockCount.vue'),
  },
  {
    // M05 I1: bảng vòng đời bộ dụng cụ (real-data instrument_loan.board).
    path: '/antmed/instruments',
    name: 'AntmedInstrumentBoard',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedInstrumentSets.vue'),
  },
  {
    // M05 I1 drill: chi tiết 1 bộ + components + lịch sử lượt mượn.
    path: '/antmed/instruments/:name',
    name: 'AntmedInstrumentSetDetail',
    meta: { role: 'warehouse' },
    component: () => import('@/pages/AntmedInstrumentSetDetail.vue'),
    props: true,
  },
  {
    // M05 C3: checklist nhận/trả + hành động vòng đời 1 lượt mượn.
    path: '/antmed/instrument-loans/:name',
    name: 'AntmedInstrumentLoanChecklist',
    meta: { role: 'rep' },
    component: () => import('@/pages/AntmedInstrumentChecklist.vue'),
    props: true,
  },
  {
    // H1: Quản trị User & Role (real-data admin RBAC — admin-gated BE).
    path: '/antmed/admin/users',
    name: 'AntmedAdminUsers',
    meta: { role: 'admin' },
    component: () => import('@/pages/AntmedAdminUsers.vue'),
  },
  {
    // Trang cá nhân — hồ sơ user Frappe đang đăng nhập (profile.me).
    path: '/antmed/profile',
    name: 'AntmedProfile',
    component: () => import('@/pages/AntmedProfile.vue'),
  },
  {
    // M08: Pipeline gói thầu (kanban AntMed Tender 6 giai đoạn) — pipeline.list_tenders/forecast.
    path: '/antmed/tenders',
    name: 'AntmedTenderPipeline',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedPipeline.vue'),
  },
  {
    // M08: Chi tiết 1 gói thầu (pipeline.get_tender) — drill-down từ thẻ pipeline.
    path: '/antmed/tenders/:name',
    name: 'AntmedTenderDetail',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedTenderDetail.vue'),
    props: true,
  },
  {
    // M08: Danh sách Lead (kế thừa CRM Lead, scoped org_hierarchy) — pipeline.list_leads.
    path: '/antmed/leads',
    name: 'AntmedLeads',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedLeads.vue'),
  },
  {
    // M08 (GỘP): Pipeline Cơ hội = CRM Deal (kanban kéo-thả) — pipeline.deal_board.
    path: '/antmed/deals',
    name: 'AntmedDealPipeline',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedDealPipeline.vue'),
  },
  {
    // M08: Chi tiết 1 Cơ hội (CRM Deal) — pipeline.get_deal.
    path: '/antmed/deals/:name',
    name: 'AntmedDealDetail',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedDealDetail.vue'),
    props: true,
  },
  {
    // M10-1: màn Đội ngũ KD (mockup B2, Trưởng phòng KD) — real-data, render trong
    // AntmedLayout (isAntmedPath '/antmed/*'). meta.role='sales' ⇒ sidebar TKD (sales-team active).
    path: '/antmed/sales/team',
    name: 'AntmedTeam',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedTeam.vue'),
  },
  {
    // mockup B1 (Trưởng phòng KD) — Bảng điều phối CA GIAO PHÒNG MỔ: kanban AntMed Delivery
    // theo trạng thái (Mới tiếp nhận/Đã gán NV/Đang giao/Đã bàn giao). meta.role='sales'.
    // (Đổi concept pipeline→delivery cho khớp mockup B1; pipeline cũ dời /antmed/sales/pipeline.)
    path: '/antmed/sales/dispatch',
    name: 'AntmedDispatch',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedDeliveryDispatch.vue'),
  },
  {
    // Pipeline gói thầu (kanban CRM Deal theo giai đoạn) — màn cũ AntmedDispatch.vue, dời route
    // khi /antmed/sales/dispatch chuyển sang Bảng điều phối ca giao phòng mổ (B1). meta.role='sales'.
    path: '/antmed/sales/pipeline',
    name: 'AntmedPipeline',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedDispatch.vue'),
  },
  {
    // Công việc (port CRM Task → dùng cho AntMed): CSKH/hồ sơ thầu/theo dõi HĐ.
    path: '/antmed/tasks',
    name: 'AntmedTasks',
    meta: { role: 'sales' },
    component: () => import('@/pages/AntmedTasks.vue'),
  },
  {
    // M10-3: màn "Hồ sơ nhân viên" (mockup B2 left-card, Trưởng phòng KD) — drill-down 1 dòng từ
    // bảng roster /antmed/sales/team. param owner = deal_owner (email) — KHÔNG hiển thị email thô,
    // chỉ full_name. Render trong AntmedLayout (isAntmedPath '/antmed/*' + meta.antmedShell).
    // meta.role='sales' ⇒ sidebar TKD (sales-team active).
    path: '/antmed/sales/team/:owner',
    name: 'AntmedRepProfile',
    meta: { antmedShell: true, role: 'sales' },
    component: () => import('@/pages/AntmedRepProfile.vue'),
    props: true,
  },
  {
    // M09-1: màn "Hoa hồng Nhân viên" (mockup F2, Kế toán) — real-data 2 card header
    // (Tổng hoa hồng kỳ + Quy tắc kỳ), render trong AntmedLayout (isAntmedPath '/antmed/*' +
    // meta.antmedShell). meta.role='finance' ⇒ sidebar Kế toán (fin-commission active).
    // Stub cũ /finance/commission GIỮ NGUYÊN (name 'AntmedCommission' — no-regression);
    // route real-data dùng name riêng 'AntmedCommissionPage' (vue-router cấm trùng name).
    path: '/antmed/finance/commission',
    name: 'AntmedCommissionPage',
    meta: { antmedShell: true, role: 'finance' },
    component: () => import('@/pages/AntmedCommissionPage.vue'),
  },
  {
    path: '/antmed/hospitals/:name',
    name: 'AntmedHospitalDetail',
    component: () => import('@/pages/AntmedHospitalDetail.vue'),
    props: true,
  },
  {
    path: '/antmed/doctors/:name',
    name: 'AntmedDoctorDetail',
    component: () => import('@/pages/AntmedDoctorDetail.vue'),
    props: true,
  },
  {
    // M07-1: màn "Portal Bệnh viện — Trang chủ" (mockup G1, id=bv) — real-data.
    // 3 quick-action card tĩnh (nav-only) + card "📰 Thông báo gần đây" wire
    // customer.portal_notifications. Render trong AntmedLayout (isAntmedPath '/antmed/*' +
    // meta.antmedShell). meta.role='portal' ⇒ sidebar Portal (topbar trắng — variant portal).
    // name 'AntmedPortalHome' chuyển TỪ stub /portal sang ĐÂY (vue-router cấm trùng name);
    // stub cũ /portal đổi name 'AntmedPortalHomeMock' (no-regression path).
    path: '/antmed/portal',
    name: 'AntmedPortalHome',
    meta: { antmedShell: true, role: 'portal' },
    component: () => import('@/pages/AntmedPortalHome.vue'),
  },

  // ── Phase 2 — CHỈ DÙNG UI AntMed: ĐÃ GỠ TOÀN BỘ route mock prototype cũ ──────
  // (/ceo,/sales/*,/rep/*,/warehouse/*,/docs/*,/finance/*,/portal,/admin/*,/instruments).
  // Màn thật dùng /antmed/*. Page mock (AntmedCeoDashboard/ContractHealth/Revenue) +
  // AntmedScreenStub đã xoá. Điều hướng tới chúng → guard redirect /antmed.

  {
    path: '/welcome',
    name: 'Welcome',
    component: () => import('@/pages/Welcome.vue'),
  },
  {
    path: '/:invalidpath',
    name: 'Invalid Page',
    component: () => import('@/pages/InvalidPage.vue'),
  },
  {
    path: '/not-permitted',
    name: 'Not Permitted',
    component: () => import('@/pages/NotPermitted.vue'),
  },
]

let router = createRouter({
  history: createWebHistory('/'),
  routes,
})

router.beforeEach(async (to, from, next) => {
  router.previousRoute = from

  const { isLoggedIn } = sessionStore()
  const { users, isCrmUser } = usersStore()

  if (isLoggedIn && !users.fetched) {
    try {
      await users.promise
    } catch (error) {
      console.error('Error loading users', error)
    }
  }

  // Guest → trang login AntMed (full-screen, KHÔNG layout shell). Giữ đích redirect.
  if (!isLoggedIn) {
    if (to.name === 'AntmedLogin') {
      next()
    } else {
      next({ name: 'AntmedLogin', query: { 'redirect-to': to.fullPath } })
    }
    return
  }

  // ── Phase 2 — CHỈ DÙNG UI AntMed ──────────────────────────────────────────
  // Mọi route ngoài khu /antmed/* (Home, CRM gốc + mock prototype ĐÃ GỠ, URL lạ) → redirect
  // /antmed. Giữ: /antmed/*, login AntMed, trang "Not Permitted".
  if (!isAntmedOnlyKeptRoute(to)) {
    next({ name: 'AntmedHome' })
    return
  }

  // Permission gate (BR data-scoping) cho route /antmed/* — CRM hoặc AntMed user.
  if (
    to.name !== 'Not Permitted' &&
    shouldRedirectNotPermitted(to, { isCrmUser, isAntmedUser })
  ) {
    next({ name: 'Not Permitted' })
    return
  }

  next()
})

export default router
