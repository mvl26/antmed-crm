/**
 * AntMed CRM — dữ liệu mẫu TĨNH cho prototype 24 màn (Q1 SPEC: bám mockup 100%).
 *
 * Nguồn số liệu: docs/antmed_crm/docs/AntMed_CRM_Full_Mockups.html (24 màn / 8 vai trò).
 * Đây là PROTOTYPE demo — KHÔNG wire backend, KHÔNG business-rule. Mọi con số chép
 * đúng từ mockup (ngoại lệ quy ước "không bịa số" đã được người dùng cho phép — Q1).
 *
 * Tổ chức: 1 named-export / màn (hoặc cụm màn cùng vai trò). 20 export khớp plan T2:
 *   A1 ceoDashboard · A2 contracts · A3 revenue · B1 dispatch · B2 team · B3 approvals ·
 *   C1-C5 repToday · C4 doctor · D1 warehouseExport · D2 consignment · D3 lotTrace ·
 *   E1 docsPending · E2 coCq · E3 reconciliation · F1 receivables · F2 commission ·
 *   G1-G2 portal · H1 users · H2 audit · I1 instruments.
 *
 * Quy ước tone pill khớp UI kit T1 (utils/antmedUi.PILL_THEME): ok/warn/danger/info/neutral.
 * Status PHẢI kèm chữ (label) — không phân biệt chỉ bằng màu (WCAG AA, §4 SPEC).
 * heat lvl 0..5 (0 = ô trống, 1..5 = h1c..h5c) khớp utils/antmedUi.heatClass.
 * lifecycle.current = chỉ số 0-based trong LIFECYCLE_STAGES.
 */

/** 7 trạng thái vòng đời bộ dụng cụ (AmLifecycle) — khớp mockup I1/C3. */
export const LIFECYCLE_STAGES = [
  'SS',
  'Đặt',
  'Giao',
  'SD',
  'Trả',
  'Xử lý',
  'SS lại',
]

// ── A1 · CEO Dashboard điều hành ────────────────────────────────────────────
export const ceoDashboard = {
  period: 'Tháng 05/2026',
  scope: 'Toàn quốc',
  kpis: [
    {
      label: 'Doanh thu tháng',
      value: '12,8 tỷ ₫',
      sub: '▲ 14% vs T4',
      tone: 'ok',
    },
    { label: 'Quota đã dùng', value: '78%', sub: '9 HĐ > 90%', ring: 78 },
    {
      label: 'SLA giao PT',
      value: '94,2%',
      sub: '▲ 2,1% đúng giờ',
      tone: 'ok',
    },
    {
      label: 'Bộ DC lưu hành',
      value: '47',
      sub: '/3 quá hạn · ▲ 1 thất lạc',
      tone: 'danger',
    },
  ],
  topHospitals: [
    { name: 'Bạch Mai', revenue: '2,1', quotaPct: 88, tone: 'default' },
    { name: 'Việt Đức', revenue: '1,7', quotaPct: 72, tone: 'warn' },
    { name: 'K', revenue: '1,3', quotaPct: 60, tone: 'default' },
    { name: 'Chợ Rẫy', revenue: '1,1', quotaPct: 95, tone: 'danger' },
    { name: '108', revenue: '0,9', quotaPct: 42, tone: 'default' },
  ],
  funnel: [
    { stage: 'Lead', count: 38 },
    { stage: 'Khảo sát', count: 24 },
    { stage: 'Báo giá', count: 18 },
    { stage: 'Dự thầu', count: 11 },
    { stage: 'Trúng', count: 6 },
  ],
  alerts: [
    { tone: 'danger', tag: 'HẾT HẠN', text: 'HĐ Chợ Rẫy còn 12 ngày' },
    { tone: 'danger', tag: 'NỢ', text: 'Việt Đức 1,2 tỷ > 90 ngày' },
    { tone: 'warn', tag: 'QUÁ HẠN TRẢ', text: 'Bộ BS-014 trễ 4 ngày' },
    { tone: 'warn', tag: 'CẬN DATE', text: 'Lot L-9921 còn 45 ngày' },
  ],
}

// ── A2 · Sức khỏe hợp đồng ──────────────────────────────────────────────────
export const contracts = {
  rows: [
    {
      contractNo: 'HD-2025-018',
      hospital: 'BV Bạch Mai',
      signedAt: '15/03/2025',
      expireAt: '14/03/2026',
      value: '3,8',
      quotaPct: 88,
      quotaTone: 'default',
      sku: 142,
      status: 'Đang hiệu lực',
      statusTone: 'ok',
      action: 'Chi tiết',
    },
    {
      contractNo: 'HD-2025-022',
      hospital: 'BV Việt Đức',
      signedAt: '02/04/2025',
      expireAt: '01/04/2026',
      value: '2,9',
      quotaPct: 72,
      quotaTone: 'warn',
      sku: 98,
      status: 'Đang hiệu lực',
      statusTone: 'ok',
      action: 'Chi tiết',
    },
    {
      contractNo: 'HD-2024-091',
      hospital: 'BV Chợ Rẫy',
      signedAt: '13/06/2025',
      expireAt: '12/06/2026',
      value: '4,2',
      quotaPct: 95,
      quotaTone: 'danger',
      sku: 205,
      status: 'Sắp hết hạn 12 ngày',
      statusTone: 'danger',
      action: 'Gia hạn',
    },
    {
      contractNo: 'HD-2025-035',
      hospital: 'BV K',
      signedAt: '20/05/2025',
      expireAt: '19/05/2026',
      value: '1,9',
      quotaPct: 60,
      quotaTone: 'default',
      sku: 76,
      status: 'Đang hiệu lực',
      statusTone: 'ok',
      action: 'Chi tiết',
    },
    {
      contractNo: 'HD-2024-128',
      hospital: 'BV E',
      signedAt: '10/01/2025',
      expireAt: '09/01/2026',
      value: '0,9',
      quotaPct: null,
      sku: null,
      status: 'Đã hết hạn',
      statusTone: 'neutral',
      action: 'Tái đấu thầu',
    },
  ],
  topSku: [
    {
      sku: 'VT-0231 · Chỉ Vicryl 2-0',
      quota: '5.000',
      issued: '4.418',
      pct: 88,
    },
    { sku: 'VT-0188 · Dao mổ #11', quota: '3.000', issued: '2.150', pct: 72 },
    { sku: 'VT-1102 · Lưới Prolene', quota: '800', issued: '520', pct: 65 },
    { sku: 'VT-0410 · Gạc cầm máu', quota: '10.000', issued: '9.910', pct: 99 },
    { sku: 'VT-2201 · Kim phẫu thuật', quota: '1.500', issued: '900', pct: 60 },
  ],
}

// ── A3 · Báo cáo doanh thu ──────────────────────────────────────────────────
export const revenue = {
  kpis: [
    { label: 'Doanh thu Q2', value: '38,2 tỷ ₫', sub: '▲ 19% YoY', tone: 'ok' },
    {
      label: 'Biên lợi nhuận gộp',
      value: '31,4%',
      sub: '▼ 0,8%',
      tone: 'danger',
    },
    { label: 'Đơn hàng', value: '2.184', sub: 'Avg 17,5 tr/đơn' },
  ],
  heatColumns: ['Bạch Mai', 'Việt Đức', 'K', 'Chợ Rẫy', '108'],
  heatmap: [
    {
      rep: 'Nguyễn Văn An',
      cells: [
        { v: '2.140', lvl: 5 },
        { v: '680', lvl: 3 },
        { v: '1.250', lvl: 4 },
        { v: '—', lvl: 0 },
        { v: '—', lvl: 0 },
      ],
      total: '4.070',
    },
    {
      rep: 'Trần Bình',
      cells: [
        { v: '—', lvl: 0 },
        { v: '1.020', lvl: 4 },
        { v: '—', lvl: 0 },
        { v: '1.180', lvl: 5 },
        { v: '320', lvl: 2 },
      ],
      total: '2.520',
    },
    {
      rep: 'Lê Lan',
      cells: [
        { v: '410', lvl: 2 },
        { v: '—', lvl: 0 },
        { v: '820', lvl: 3 },
        { v: '730', lvl: 3 },
        { v: '980', lvl: 4 },
      ],
      total: '2.940',
    },
    {
      rep: 'Phạm Hà',
      cells: [
        { v: '650', lvl: 3 },
        { v: '390', lvl: 2 },
        { v: '—', lvl: 0 },
        { v: '—', lvl: 0 },
        { v: '1.420', lvl: 5 },
      ],
      total: '2.460',
    },
  ],
  legend: [
    { label: 'Thấp', color: '#FEE2E2' },
    { label: 'TB', color: '#FCA5A5' },
    { label: 'Cao', color: '#F87171' },
    { label: 'Rất cao', color: '#EF4444' },
  ],
}

// ── B1 · Kanban điều phối ca giao ───────────────────────────────────────────
export const dispatch = {
  date: 'Hôm nay 01/06',
  columns: [
    {
      key: 'new',
      title: 'Mới tiếp nhận',
      count: 3,
      cards: [
        {
          hospital: 'BV Việt Đức',
          time: '15:00',
          detail: 'BS. Phương · 4 SKU · còn 0h48 ⚠',
          accent: 'urgent',
          action: 'Gán NV →',
        },
        {
          hospital: 'BV Bạch Mai',
          time: '16:30',
          detail: 'BS. Hùng · 6 SKU',
          accent: 'warn',
          tag: { tone: 'warn', label: 'Ngoài DM' },
        },
        {
          hospital: 'BV 108',
          time: '17:00',
          detail: 'BS. Tâm · 3 SKU',
          accent: '',
        },
      ],
    },
    {
      key: 'assigned',
      title: 'Đã gán NV',
      count: 4,
      cards: [
        {
          hospital: 'BV K',
          time: '14:30',
          detail: 'NV An · đang lấy hàng',
          accent: '',
        },
        {
          hospital: 'BV Chợ Rẫy',
          time: '15:30',
          detail: 'NV Bình · sẵn sàng',
          accent: '',
        },
        {
          hospital: 'BV Nhi TW',
          time: '16:00',
          detail: 'NV Lan · ETA 15:30',
          accent: '',
        },
        {
          hospital: 'BV E',
          time: '18:00',
          detail: 'NV Hà · acked',
          accent: '',
        },
      ],
    },
    {
      key: 'delivering',
      title: 'Đang giao',
      count: 2,
      cards: [
        {
          hospital: 'BV K',
          time: '14:30',
          detail: '📍 NV An — cổng BV 14:08',
          accent: 'warn',
        },
        {
          hospital: 'BV Chợ Rẫy',
          time: '15:30',
          detail: '📍 NV Bình — phòng mổ 15:05',
          accent: '',
        },
      ],
    },
    {
      key: 'done',
      title: 'Đã bàn giao',
      count: 5,
      cards: [
        {
          hospital: 'BV E',
          time: '✓ 13:10',
          detail: 'NV An · CT ✓',
          accent: 'ok',
        },
        {
          hospital: 'BV Việt Đức',
          time: '✓ 12:40',
          detail: 'NV Bình · CO chờ gắn',
          accent: 'ok',
        },
        {
          hospital: 'BV K',
          time: '✓ 11:20',
          detail: 'NV Hà · HĐĐT đã phát hành',
          accent: 'ok',
        },
      ],
    },
  ],
  legend: [
    { tone: 'danger', text: 'Khẩn (<1h)' },
    { tone: 'warn', text: 'Cảnh báo / ngoài DM' },
    { tone: 'ok', text: 'Hoàn tất' },
    {
      tone: 'neutral',
      text: 'Kéo-thả thẻ để gán/đổi NV. Click thẻ → drawer chi tiết.',
    },
  ],
}

// ── B2 · Quản lý đội ngũ ────────────────────────────────────────────────────
export const team = {
  members: [
    {
      name: 'Nguyễn Văn An',
      route: 'Bạch Mai · K',
      personalStock: '47 SKU / 320tr',
      setsHeld: 3,
      dsPct: 68,
      dsTone: 'default',
      slaPct: '96%',
      returnPct: '92%',
      nps: '4.6/5',
      warning: null,
    },
    {
      name: 'Trần Bình',
      route: 'Việt Đức · Chợ Rẫy',
      personalStock: '32 SKU / 210tr',
      setsHeld: 2,
      dsPct: 54,
      dsTone: 'warn',
      slaPct: '91%',
      returnPct: '88%',
      nps: '4.3/5',
      warning: { tone: 'warn', label: 'Bộ BS-014 trễ' },
    },
    {
      name: 'Lê Lan',
      route: '108 · Nhi TW',
      personalStock: '28 SKU / 180tr',
      setsHeld: 1,
      dsPct: 78,
      dsTone: 'default',
      slaPct: '98%',
      returnPct: '100%',
      nps: '4.8/5',
      warning: null,
    },
    {
      name: 'Phạm Hà',
      route: 'E · 108',
      personalStock: '21 SKU / 140tr',
      setsHeld: 4,
      dsPct: 42,
      dsTone: 'danger',
      slaPct: '89%',
      returnPct: '83%',
      nps: '4.1/5',
      warning: { tone: 'danger', label: 'DS thấp' },
    },
  ],
  profile: {
    name: 'Nguyễn Văn An',
    dept: 'KD Miền Bắc',
    level: 'Senior',
    joined: '03/2022',
    contracts: 'HD-2025-018 (Bạch Mai), HD-2025-035 (K)',
    kpiCommit: '4,2 tỷ',
    kpiAchieved: '2,86 tỷ (68%)',
    commission: '18,7 triệu',
    checkins: [
      { time: '08:12', text: 'Kho TT (lấy hàng cho 3 ca)', dur: '—' },
      {
        time: '10:30',
        text: 'BV Bạch Mai · ghé thăm BS. Linh',
        dur: '15 phút',
      },
      { time: '11:50', text: 'BV K · giao ca 12:00 ✓', dur: '' },
      { time: '14:08', text: 'BV K · đang giao ca 14:30', dur: '' },
    ],
  },
  setsManaged: [
    {
      code: 'BS-007',
      type: 'Sọ não',
      status: 'Đang giao BV Bạch Mai',
      tone: 'info',
      due: '03/06',
    },
    {
      code: 'BS-019',
      type: 'Tiêu hóa',
      status: 'Tại kho TT — SS',
      tone: 'ok',
      due: '—',
    },
    {
      code: 'BS-031',
      type: 'Nội soi',
      status: 'Tiệt khuẩn — chờ lấy',
      tone: 'warn',
      due: '02/06',
    },
  ],
}

// ── B3 · Hộp duyệt yêu cầu ──────────────────────────────────────────────────
export const approvals = {
  pendingCount: 8,
  summary: [
    { tone: 'danger', label: 'Khẩn 2' },
    { tone: 'warn', label: 'Ngoài DM 3' },
    { tone: 'info', label: 'Sponsor 2' },
    { tone: 'neutral', label: 'Trả trễ 1' },
  ],
  inbox: [
    {
      flag: '🔴',
      type: 'Ngoài DM',
      who: 'An / Bạch Mai',
      desc: 'Lưới Prolene 15×15 ngoài thầu',
      at: '10 phút trước',
      highlight: true,
    },
    {
      flag: '🟡',
      type: 'Khẩn',
      who: 'Bình / Việt Đức',
      desc: 'Bổ sung 2 SKU cho ca 15:00',
      at: '22 phút',
    },
    {
      flag: '',
      type: 'Sponsor',
      who: 'Lan / 108',
      desc: 'Tài trợ hội nghị tim mạch 15 tr',
      at: '1 giờ',
    },
    {
      flag: '',
      type: 'Quà tặng',
      who: 'Hà / E',
      desc: 'Quà 3,2 tr cho BS. Tâm sinh nhật',
      at: '3 giờ',
    },
    {
      flag: '',
      type: 'Trả trễ',
      who: 'Bình / K',
      desc: 'Bộ BS-014 quá hạn 4 ngày',
      at: 'hôm qua',
    },
  ],
  detail: {
    code: 'YC-2026-0612',
    rep: 'Nguyễn Văn An',
    hospital: 'Bạch Mai · BS. Hùng · Khoa Ngoại TK',
    caseTime: '16:30 · 01/06/2026',
    item: 'VT-1102 Lưới Prolene 15×15 · SL 1',
    reason: 'Bác sỹ yêu cầu tại chỗ, ngoài DM trúng thầu HĐ-2025-018',
    refPrice: '4,8 triệu/cái',
    note: '"BS. Hùng đã xác nhận, BV cam kết thanh toán riêng."',
    alert: {
      tone: 'danger',
      text: '⚠ Vượt ngưỡng cho phép NV (3tr). Cần TKD ký + báo Pháp lý.',
    },
    actions: ['✓ Duyệt', 'Yêu cầu BS xác nhận', '✗ Từ chối'],
  },
}

// ── C1/C2/C3/C5 · NV Kinh doanh (mobile) ────────────────────────────────────
export const repToday = {
  rep: {
    name: 'Nguyễn Văn An',
    route: 'Bạch Mai · K',
    initials: 'NA',
    notifications: 3,
  },
  stats: [
    { label: 'Kho', value: '47' },
    { label: 'Bộ', value: '3' },
    { label: 'DS', value: '68%' },
  ],
  cases: [
    {
      time: '14:30',
      hospital: 'BV K',
      badge: { tone: 'warn', label: 'còn 1h22' },
      detail: 'BS. Hùng · Ngoại TK · 5 SKU',
      accent: 'accent',
      action: '▶ Bắt đầu giao',
    },
    {
      time: '16:00',
      hospital: 'Bạch Mai',
      badge: { tone: 'ok', label: '2h52' },
      detail: 'Mượn bộ Sọ não BS-007',
      accent: 'ok',
      action: '📋 Checklist',
    },
    {
      time: '18:30',
      hospital: 'BV K',
      badge: null,
      detail: 'Trả bộ BS-014 + xử lý',
      accent: 'danger',
      action: '⚠ Quá hạn 4 ngày',
    },
  ],
  // C2 · Wizard giao 4 bước
  wizard: {
    hospital: 'BV K',
    doctor: 'BS. Hùng',
    steps: [
      { no: 1, label: 'Xác nhận yêu cầu', state: 'done' },
      { no: 2, label: 'Quét lấy hàng', state: 'done' },
      { no: 3, label: 'Bàn giao & Ký số', state: 'current' },
      { no: 4, label: 'Sinh chứng từ', state: 'todo' },
    ],
    items: [
      {
        sku: 'VT-0231',
        name: 'Chỉ Vicryl 2-0',
        lot: 'L-9912',
        exp: '10/2027',
        qty: 5,
      },
      {
        sku: 'VT-0188',
        name: 'Dao mổ #11',
        lot: 'L-9921',
        exp: '03/2027',
        qty: 3,
      },
      {
        sku: 'VT-1102',
        name: 'Lưới Prolene 15×15',
        lot: 'L-9930',
        exp: '05/2028',
        qty: 1,
      },
      {
        sku: 'VT-0410',
        name: 'Gạc cầm máu',
        lot: 'L-9805',
        exp: '07/2026',
        qty: 10,
      },
    ],
    gps: '📍 GPS check-in BV K lúc 14:08 · phòng mổ tầng 4',
    receiver: 'ĐD. Nguyễn Thị Mai',
    receiverRole: 'Điều dưỡng trưởng PM 3',
  },
  // C3 · Checklist bộ dụng cụ
  checklist: {
    setCode: 'BS-007',
    setName: 'Sọ não',
    hospital: 'BV Bạch Mai',
    patient: 'Ca mổ 16:00 · BS. Linh · Phòng mổ 2',
    total: 42,
    checked: 36,
    items: [
      { name: 'Khoan điện cầm tay', checked: true },
      { name: 'Lưỡi cưa #2', checked: true },
      { name: 'Lưỡi cưa #3', checked: true },
      {
        name: 'Bộ kìm gắp (3 món)',
        checked: false,
        tag: { tone: 'warn', label: 'cần ảnh' },
      },
      {
        name: 'Banh xương #5',
        checked: false,
        tag: { tone: 'warn', label: 'cần ảnh' },
      },
      { name: 'Ống hút phẫu thuật', checked: true },
      { name: 'Đầu khoan #2.5mm', checked: true },
    ],
    lifecycle: { stages: LIFECYCLE_STAGES, current: 2 },
  },
  // C5 · Offline mode
  offline: {
    location: 'Bạch Mai · Tầng 3 phòng mổ',
    banner: '⚠ Chế độ ngoại tuyến · 5 thao tác chờ đồng bộ',
    pendingCount: 5,
    queue: [
      {
        icon: '📋',
        title: 'Phiếu giao DO-Local-0042',
        sub: 'BV Bạch Mai · 5 SKU · ký 11:48',
      },
      {
        icon: '🧰',
        title: 'Checklist nhận bộ BS-007',
        sub: '42/42 món · 6 ảnh · ký 11:52',
      },
      { icon: '📝', title: 'Ghi chú ghé thăm BS. Linh', sub: '12:05 · 1 ảnh' },
      { icon: '📍', title: 'Check-in GPS BV Bạch Mai', sub: '11:45' },
      { icon: '📷', title: '5 ảnh chứng từ', sub: '12,4 MB' },
    ],
  },
}

// ── C4 · CRM Bác sỹ (mobile) ────────────────────────────────────────────────
export const doctor = {
  name: 'BS. Trần Mạnh Hùng',
  hospital: 'BV K · Khoa Ngoại Thần kinh',
  title: 'Trưởng khoa',
  meta: 'SN: 12/08 · 14 năm KN',
  initials: 'TH',
  tabs: ['Ghi chú', 'Lịch sử', 'VT ưa dùng', 'Quà'],
  notes: [
    {
      date: '25/05/2026 · ghé thăm',
      text: 'Chốt thêm 200 lưới Prolene cho Q3. BS quan tâm sản phẩm khâu nối tự tiêu mới.',
      meta: '📍 BV K · ⏱ 22 phút',
    },
    {
      date: '18/05/2026 · cuộc gọi',
      text: 'Phản hồi lô L-9710 tốt, không vấn đề.',
      meta: '',
    },
  ],
}

// ── D1 · Xuất kho cho NV (quét QR) ──────────────────────────────────────────
export const warehouseExport = {
  rep: 'Nguyễn Văn An — Tuyến Bạch Mai/K',
  purpose: 'Giao ca mổ — 3 phiếu yêu cầu hôm nay',
  scannedCount: 4,
  items: [
    {
      sku: 'VT-0231',
      name: 'Chỉ Vicryl 2-0',
      lot: 'L-9912',
      exp: '10/2027',
      qty: 5,
      value: '1.250.000',
      coCq: { tone: 'ok', label: 'Đính kèm' },
    },
    {
      sku: 'VT-0188',
      name: 'Dao mổ #11',
      lot: 'L-9921',
      exp: '03/2027',
      qty: 3,
      value: '360.000',
      coCq: { tone: 'ok', label: 'Đính kèm' },
    },
    {
      sku: 'VT-1102',
      name: 'Lưới Prolene 15×15',
      lot: 'L-9930',
      exp: '05/2028',
      qty: 1,
      value: '4.800.000',
      coCq: { tone: 'danger', label: 'THIẾU CQ' },
    },
    {
      sku: 'VT-0410',
      name: 'Gạc cầm máu',
      lot: 'L-9805',
      exp: '07/2026',
      qty: 10,
      value: '900.000',
      coCq: { tone: 'warn', label: 'CO 2/3 lot' },
    },
  ],
  alert: {
    tone: 'danger',
    text: '⚠ VT-1102 thiếu CQ — không thể xuất. Gọi Pháp lý đính file trước.',
  },
  recentSlips: [
    { slip: 'PX-2026-0814', rep: 'Bình', value: '3,2 tr', at: '09:20' },
    { slip: 'PX-2026-0813', rep: 'Lan', value: '1,8 tr', at: '08:55' },
    { slip: 'PX-2026-0812', rep: 'An', value: '2,4 tr', at: '08:14' },
  ],
}

// ── D2 · Kho ký gửi BV ──────────────────────────────────────────────────────
export const consignment = {
  hospital: 'BV Bạch Mai',
  kpis: [
    { label: 'Bệnh viện có ký gửi', value: '14' },
    { label: 'Tồn ký gửi', value: '2,1 tỷ ₫', sub: '487 SKU · 1.240 lot' },
    { label: 'Cận date (≤90 ngày)', value: '18 lot', tone: 'danger' },
  ],
  rows: [
    {
      sku: 'VT-0231',
      name: 'Chỉ Vicryl 2-0',
      lot: 'L-9912',
      exp: '10/2027',
      sysQty: 120,
      realQty: 118,
      diff: '−2',
      diffTone: 'danger',
      lastCheck: '28/05',
      status: 'Lệch nhẹ',
      statusTone: 'warn',
    },
    {
      sku: 'VT-0188',
      name: 'Dao mổ #11',
      lot: 'L-9921',
      exp: '03/2027',
      sysQty: 50,
      realQty: 50,
      diff: '0',
      diffTone: '',
      lastCheck: '28/05',
      status: 'Khớp',
      statusTone: 'ok',
    },
    {
      sku: 'VT-0410',
      name: 'Gạc cầm máu',
      lot: 'L-9805',
      exp: '07/2026 (cận 38 ngày)',
      sysQty: 200,
      realQty: 200,
      diff: '0',
      diffTone: '',
      lastCheck: '28/05',
      status: 'Cận date',
      statusTone: 'danger',
      rowHighlight: true,
    },
    {
      sku: 'VT-2201',
      name: 'Kim PT',
      lot: 'L-9971',
      exp: '12/2028',
      sysQty: 80,
      realQty: null,
      diff: '—',
      diffTone: '',
      lastCheck: '—',
      status: 'Chưa kiểm',
      statusTone: 'neutral',
    },
  ],
}

// ── D3 · Truy vết lot ───────────────────────────────────────────────────────
export const lotTrace = {
  lotCode: 'L-22834',
  info: [
    { field: 'SKU', value: 'VT-0231 · Chỉ phẫu thuật Vicryl 2-0' },
    { field: 'NCC', value: 'Johnson & Johnson VN' },
    { field: 'NSX', value: '03/2025' },
    { field: 'HSD', value: '10/2027' },
    { field: 'SL nhập', value: '1.000' },
    { field: 'SL đã xuất', value: '847' },
    { field: 'SL còn', value: '153 (kho TT 80 + ký gửi BV 73)' },
    { field: 'CO', value: 'CO_JJ_L22834.pdf', file: true },
    { field: 'CQ', value: 'CQ_JJ_L22834.pdf', file: true },
  ],
  tree: `Lot L-22834 (Vicryl 2-0)
 ├─ 12/03/2026 · Nhập từ J&J VN · 1.000 cái
 │
 ├─ 02/05/2026 · Xuất cho NV An · 200
 │  ├─ 03/05 · BV Việt Đức · BS. Hùng · ca 14:30
 │  │   └─ Hóa đơn HD-2026-00871 · 30 cái
 │  ├─ 05/05 · BV Bạch Mai · BS. Linh
 │  │   └─ HD-2026-00903 · 40 cái
 │  └─ kho NV An còn 90
 │
 ├─ 10/05 · Xuất cho NV Bình · 150
 │  └─ BV Chợ Rẫy · ký gửi 150
 │
 └─ Tồn kho tổng: 80`,
}

// ── E1 · Hàng chờ phát hành chứng từ ────────────────────────────────────────
export const docsPending = {
  summary: [
    { tone: 'danger', label: 'Thiếu CO 3' },
    { tone: 'warn', label: 'Thiếu CQ 5' },
    { tone: 'info', label: 'Sẵn sàng phát hành 12' },
  ],
  rows: [
    {
      do: 'DO-2026-0871',
      hospital: 'Việt Đức',
      rep: 'Bình',
      missing: { tone: 'danger', label: 'CO lot L-9930' },
      date: '01/06 12:40',
      ready: false,
    },
    {
      do: 'DO-2026-0870',
      hospital: 'Bạch Mai',
      rep: 'An',
      missing: { tone: 'warn', label: 'CQ lot L-9912' },
      date: '01/06 11:50',
      ready: false,
    },
    {
      do: 'DO-2026-0869',
      hospital: 'K',
      rep: 'Hà',
      missing: { tone: 'ok', label: 'Đủ' },
      date: '01/06 11:20',
      ready: true,
    },
    {
      do: 'DO-2026-0868',
      hospital: '108',
      rep: 'Lan',
      missing: { tone: 'warn', label: 'CO L-9805' },
      date: '01/06 10:15',
      ready: false,
    },
  ],
  detail: {
    do: 'DO-2026-0871',
    hospital: 'Việt Đức',
    rep: 'Trần Bình',
    doctor: 'Phương',
    caseTime: '12:00 01/06',
    summary: '4 SKU · 8,9 tr ₫',
    lots: [
      { lot: 'L-9912', co: true, cq: true },
      { lot: 'L-9930', co: false, cq: true },
    ],
  },
}

// ── E2 · Kho CO/CQ (NCC × Lot) ──────────────────────────────────────────────
export const coCq = {
  suppliers: [
    { name: 'Johnson & Johnson VN', count: 214, indent: 0 },
    { name: 'Chỉ phẫu thuật', count: 82, indent: 1 },
    { name: 'Dao mổ', count: 45, indent: 1 },
    { name: 'Medtronic', count: 128, indent: 0 },
    { name: 'B. Braun', count: 96, indent: 0 },
    { name: 'Olympus', count: 53, indent: 0 },
    { name: 'Stryker', count: 71, indent: 0 },
  ],
  files: [
    {
      file: '📄 CO_JJ_L22834.pdf',
      lot: 'L-22834',
      sku: 'VT-0231',
      type: 'CO',
      hash: 'a3f...e21',
      upload: '13/03/2026',
      attached: '147 phiếu',
    },
    {
      file: '📄 CQ_JJ_L22834.pdf',
      lot: 'L-22834',
      sku: 'VT-0231',
      type: 'CQ',
      hash: '9b1...7c0',
      upload: '13/03/2026',
      attached: '147 phiếu',
    },
    {
      file: '📄 CO_JJ_L9930.pdf',
      lot: 'L-9930',
      sku: 'VT-1102',
      type: 'CO',
      hash: '—',
      upload: { tone: 'warn', label: 'Chờ NCC' },
      attached: '0',
    },
  ],
}

// ── E3 · Đối soát ký nhận ───────────────────────────────────────────────────
export const reconciliation = {
  kpis: [
    { label: 'Đã gửi · chờ ký', value: '87' },
    { label: 'Đã ký nhận', value: '643', tone: 'ok' },
    { label: 'BV phản hồi sai sót', value: '5', tone: 'danger' },
    { label: 'Quá hạn ký (>7 ngày)', value: '12', tone: 'warn' },
  ],
  rows: [
    {
      do: 'DO-2026-0850',
      hospital: 'Bạch Mai',
      value: '3,2 tr',
      sentAt: '25/05',
      status: 'Đã ký 27/05',
      statusTone: 'ok',
      sla: '2 ngày',
      action: '—',
    },
    {
      do: 'DO-2026-0832',
      hospital: 'Việt Đức',
      value: '5,1 tr',
      sentAt: '20/05',
      status: 'Chờ ký',
      statusTone: 'warn',
      sla: '12 ngày ⚠',
      action: 'Gửi nhắc',
    },
    {
      do: 'DO-2026-0828',
      hospital: 'Chợ Rẫy',
      value: '2,8 tr',
      sentAt: '18/05',
      status: 'Phản hồi sai sót',
      statusTone: 'danger',
      sla: '—',
      action: 'Xem phản hồi',
    },
    {
      do: 'DO-2026-0815',
      hospital: '108',
      value: '1,4 tr',
      sentAt: '15/05',
      status: 'Đã ký 16/05',
      statusTone: 'ok',
      sla: '1 ngày',
      action: '—',
    },
  ],
}

// ── F1 · Công nợ phải thu theo BV ───────────────────────────────────────────
export const receivables = {
  kpis: [
    { label: 'Tổng phải thu', value: '14,2 tỷ ₫' },
    { label: '≤30 ngày', value: '7,1 tỷ', tone: 'ok' },
    { label: '31–90 ngày', value: '4,8 tỷ', tone: 'warn' },
    { label: '>90 ngày', value: '2,3 tỷ', tone: 'danger' },
  ],
  bucketLabels: ['0–30', '31–60', '61–90', '>90'],
  rows: [
    {
      hospital: 'Việt Đức',
      total: '3,1 tỷ',
      buckets: [
        { v: '820', lvl: 2 },
        { v: '680', lvl: 3 },
        { v: '410', lvl: 4 },
        { v: '1.190', lvl: 5 },
      ],
      avgAge: '74 ngày',
      ageTone: 'danger',
      action: 'Gửi nhắc',
    },
    {
      hospital: 'Chợ Rẫy',
      total: '2,4 tỷ',
      buckets: [
        { v: '1.100', lvl: 3 },
        { v: '600', lvl: 2 },
        { v: '420', lvl: 2 },
        { v: '280', lvl: 3 },
      ],
      avgAge: '42 ngày',
      ageTone: 'warn',
      action: 'Tạo BB',
    },
    {
      hospital: 'Bạch Mai',
      total: '2,1 tỷ',
      buckets: [
        { v: '1.800', lvl: 5 },
        { v: '300', lvl: 2 },
        { v: '—', lvl: 0 },
        { v: '—', lvl: 0 },
      ],
      avgAge: '14 ngày',
      ageTone: 'ok',
      action: '—',
    },
    {
      hospital: 'K',
      total: '1,3 tỷ',
      buckets: [
        { v: '900', lvl: 4 },
        { v: '400', lvl: 2 },
        { v: '—', lvl: 0 },
        { v: '—', lvl: 0 },
      ],
      avgAge: '18 ngày',
      ageTone: 'ok',
      action: '—',
    },
    {
      hospital: '108',
      total: '0,9 tỷ',
      buckets: [
        { v: '500', lvl: 3 },
        { v: '240', lvl: 2 },
        { v: '160', lvl: 2 },
        { v: '—', lvl: 0 },
      ],
      avgAge: '38 ngày',
      ageTone: 'warn',
      action: 'Gửi nhắc',
    },
  ],
}

// ── F2 · Hoa hồng NV ────────────────────────────────────────────────────────
export const commission = {
  period: 'T05/2026',
  total: '186,4 triệu ₫',
  totalSub: '14 NV · 4 nhóm vật tư',
  rules:
    'Chỉ PT: 3% · Dao mổ: 2% · Lưới: 4% · Tiêu hao: 1,5% · Bonus đạt KPI ≥100%: +1,5% / Bộ DC trả đủ đúng hạn: +200k/bộ',
  rows: [
    {
      name: 'Nguyễn Văn An',
      revenue: '4,07 tỷ',
      kpiPct: '96%',
      kpiTone: 'ok',
      base: '96,8 tr',
      bonusKpi: '—',
      bonusSet: '2 × 200k = 400k',
      deduction: '—',
      total: '97,2 tr',
    },
    {
      name: 'Trần Bình',
      revenue: '2,52 tỷ',
      kpiPct: '54%',
      kpiTone: 'warn',
      base: '52,4 tr',
      bonusKpi: '—',
      bonusSet: '1 × 200k',
      deduction: '−1,5 tr',
      total: '51,1 tr',
    },
    {
      name: 'Lê Lan',
      revenue: '2,94 tỷ',
      kpiPct: '112%',
      kpiTone: 'ok',
      base: '61,2 tr',
      bonusKpi: '+10,4 tr',
      bonusSet: '1 × 200k',
      deduction: '—',
      total: '71,8 tr',
    },
    {
      name: 'Phạm Hà',
      revenue: '2,46 tỷ',
      kpiPct: '42%',
      kpiTone: 'warn',
      base: '49,6 tr',
      bonusKpi: '—',
      bonusSet: '—',
      deduction: '−2,8 tr',
      total: '46,8 tr',
    },
  ],
}

// ── G1/G2 · Portal Bác sỹ / Bệnh viện ───────────────────────────────────────
export const portal = {
  hospital: 'BV K · BS. Hùng',
  actions: [
    {
      icon: '🩺',
      title: 'Gọi vật tư cho ca mổ',
      sub: 'Trong danh mục trúng thầu',
      primary: true,
    },
    { icon: '🧰', title: 'Mượn bộ dụng cụ', sub: 'Đặt trước ca mổ' },
    {
      icon: '📄',
      title: 'Tra cứu chứng từ',
      sub: 'Hóa đơn, CO/CQ, phiếu giao',
    },
  ],
  callForm: {
    caseHint: '(Gợi ý từ lịch mổ) · 16:30 01/06 · Phòng mổ 4',
    doctor: 'BS. Trần Mạnh Hùng',
    room: 'PM 4 · Tầng 4',
    catalog: [
      {
        sku: 'VT-0231',
        name: 'Chỉ Vicryl 2-0',
        quota: { tone: 'ok', label: 'Còn quota' },
        qty: 5,
      },
      {
        sku: 'VT-0188',
        name: 'Dao mổ #11',
        quota: { tone: 'ok', label: 'Còn quota' },
        qty: 3,
      },
      {
        sku: 'VT-0410',
        name: 'Gạc cầm máu',
        quota: { tone: 'warn', label: 'Còn 1%' },
        qty: 10,
      },
    ],
  },
  notifications: [
    {
      time: '10:30 hôm nay',
      text: 'Yêu cầu YC-2026-0612 đã được NV An nhận · ETA 14:20',
    },
    { time: 'Hôm qua', text: 'Hóa đơn HD-2026-0903 đã phát hành · Tải PDF' },
    { time: '27/05', text: 'Bộ Sọ não BS-007 đã đặt thành công cho ca 01/06' },
    {
      time: '25/05',
      text: 'Quota chỉ Vicryl còn 12% · liên hệ AntMed nếu cần đặt thêm',
    },
  ],
  history: [
    {
      date: '01/06',
      do: 'DO-0869',
      doctor: 'BS. Hùng',
      sku: '4 SKU',
      value: '2,4 tr',
      docs: '📄 PDF · 📃 HĐĐT · 📜 CO/CQ',
      payment: { tone: 'warn', label: 'Chờ TT' },
    },
    {
      date: '28/05',
      do: 'DO-0855',
      doctor: 'BS. Linh',
      sku: '6 SKU',
      value: '5,1 tr',
      docs: '📄 · 📃 · 📜',
      payment: { tone: 'ok', label: 'Đã TT 30/05' },
    },
    {
      date: '25/05',
      do: 'DO-0841',
      doctor: 'BS. Hùng',
      sku: '3 SKU',
      value: '1,8 tr',
      docs: '📄 · 📃 · 📜',
      payment: { tone: 'ok', label: 'Đã TT' },
    },
  ],
}

// ── H1 · User & Role ────────────────────────────────────────────────────────
export const users = {
  rows: [
    {
      name: 'Nguyễn Văn An',
      email: 'an@antmed.vn',
      role: 'NV Kinh doanh',
      roleTone: 'info',
      scope: 'Bạch Mai · K',
      twoFa: { tone: 'ok', label: 'Bật' },
      status: { tone: 'ok', label: 'Active' },
    },
    {
      name: 'Trần Bình',
      email: 'binh@antmed.vn',
      role: 'NV Kinh doanh',
      roleTone: 'info',
      scope: 'Việt Đức · Chợ Rẫy',
      twoFa: { tone: 'ok', label: 'Bật' },
      status: { tone: 'ok', label: 'Active' },
    },
    {
      name: 'Phạm Linh',
      email: 'linh@antmed.vn',
      role: 'Trưởng KD',
      roleTone: 'warn',
      scope: 'Miền Bắc',
      twoFa: { tone: 'ok', label: 'Bật' },
      status: { tone: 'ok', label: 'Active' },
    },
    {
      name: 'Nguyễn Mai',
      email: 'mai@antmed.vn',
      role: 'Thủ kho',
      roleTone: 'neutral',
      scope: 'Kho TT',
      twoFa: { tone: 'danger', label: 'Tắt' },
      status: { tone: 'ok', label: 'Active' },
    },
    {
      name: 'Lê Hà',
      email: 'ha@antmed.vn',
      role: 'Chứng từ',
      roleTone: 'neutral',
      scope: 'Toàn bộ',
      twoFa: { tone: 'ok', label: 'Bật' },
      status: { tone: 'ok', label: 'Active' },
    },
    {
      name: 'BS. Hùng',
      email: 'hung@bvk.vn',
      role: 'Portal BV',
      roleTone: 'info',
      scope: 'BV K only',
      twoFa: { tone: 'ok', label: 'Bật' },
      status: { tone: 'ok', label: 'Active' },
    },
  ],
  permRole: 'NV Kinh doanh',
  permMatrix: [
    {
      module: 'Khách hàng',
      read: '✓ (tuyến)',
      create: '✓',
      update: '✓ (của mình)',
      del: '—',
    },
    {
      module: 'Phiếu giao',
      read: '✓',
      create: '✓',
      update: '✓ (chưa phát hành)',
      del: '—',
    },
    { module: 'Hóa đơn', read: '✓', create: '—', update: '—', del: '—' },
    { module: 'Kho TT', read: '✓ SL', create: '—', update: '—', del: '—' },
    {
      module: 'Kho cá nhân',
      read: '✓',
      create: '✓ (xin xuất)',
      update: '—',
      del: '—',
    },
    {
      module: 'Bộ dụng cụ',
      read: '✓',
      create: '—',
      update: '✓ (trạng thái)',
      del: '—',
    },
    { module: 'Audit log', read: '—', create: '—', update: '—', del: '—' },
  ],
  scopeNote:
    '🛈 Phạm vi DL: NV chỉ thấy bệnh viện thuộc tuyến phụ trách. Mọi thao tác đều ghi audit log.',
}

// ── H2 · Audit log ──────────────────────────────────────────────────────────
export const audit = {
  objectFilters: [
    'Mọi đối tượng',
    'Lot',
    'Phiếu giao',
    'Hóa đơn',
    'Bộ DC',
    'User',
  ],
  actionFilters: ['Mọi action', 'Create', 'Update', 'Delete', 'Login'],
  rows: [
    {
      time: '01/06 14:08:22',
      actor: 'an@antmed.vn',
      ip: '113.161.x.x',
      action: 'UPDATE',
      actionTone: 'ok',
      object: 'DO-2026-0871',
      diff: 'status: "draft" → "delivered"',
    },
    {
      time: '01/06 12:40:11',
      actor: 'binh@antmed.vn',
      ip: '113.161.x.x',
      action: 'CREATE',
      actionTone: 'info',
      object: 'DO-2026-0871',
      diff: '+4 line items, total 8.910.000',
    },
    {
      time: '01/06 11:20:50',
      actor: 'ha@antmed.vn',
      ip: '14.241.x.x',
      action: 'ISSUE_EINVOICE',
      actionTone: 'warn',
      object: 'HD-2026-00903',
      diff: 'via Viettel · cert "CN=AntMed..."',
    },
    {
      time: '01/06 10:14:33',
      actor: 'linh@antmed.vn',
      ip: '113.161.x.x',
      action: 'DELETE',
      actionTone: 'danger',
      object: 'DO-2026-0820 (draft)',
      diff: 'removed by Trưởng KD',
      highlight: true,
    },
    {
      time: '01/06 09:50:02',
      actor: 'an@antmed.vn',
      ip: '—',
      action: 'LOGIN',
      actionTone: 'neutral',
      object: 'session',
      diff: '2FA OK · mobile · iOS',
    },
  ],
}

// ── I1 · Bộ dụng cụ — vòng đời 47 bộ ────────────────────────────────────────
export const instruments = {
  kpis: [
    { label: 'Tổng bộ', value: '47' },
    { label: 'Đang lưu hành', value: '22' },
    { label: 'Tại kho — SS', value: '21', tone: 'ok' },
    { label: 'Quá hạn/thất lạc', value: '4', tone: 'danger' },
  ],
  stages: LIFECYCLE_STAGES,
  sets: [
    {
      code: 'BS-007',
      name: 'Sọ não',
      meta: '42 món · BV Bạch Mai · BS. Linh',
      current: 2,
      note: 'NV An đang vận chuyển · ETA 15:45',
    },
    {
      code: 'BS-014',
      name: 'CTCH',
      meta: '38 món · BV K · BS. Hùng',
      current: 4,
      note: '⚠ Trễ 4 ngày · NV Bình',
      noteTone: 'danger',
    },
    {
      code: 'BS-021',
      name: 'Tim mạch',
      meta: '56 món · BV Chợ Rẫy · BS. Long',
      current: 5,
      note: 'Tiệt khuẩn 28/05 · dự kiến lấy 31/05',
    },
    {
      code: 'BS-031',
      name: 'Nội soi',
      meta: '28 món · BV Việt Đức · BS. Phương',
      current: 6,
      note: 'Sẵn sàng cho lần mượn kế',
    },
    {
      code: 'BS-019',
      name: 'Tiêu hóa',
      meta: '34 món · Kho TT',
      current: 0,
      note: 'Lượt mượn gần nhất: 18/05',
    },
    {
      code: 'BS-022',
      name: 'Khoan',
      meta: '12 món · BV Nhi TW · BS. Vy',
      current: 1,
      note: 'Đặt mượn cho ca 03/06 09:00',
    },
  ],
  frequency: [
    {
      type: 'Sọ não',
      count: 3,
      monthly: 18,
      cycle: '2,5',
      conflict: '4 lần',
      suggestion: { tone: 'warn', label: '+1 bộ' },
    },
    {
      type: 'CTCH',
      count: 5,
      monthly: 22,
      cycle: '3,1',
      conflict: '1 lần',
      suggestion: { tone: 'ok', label: 'Đủ' },
    },
    {
      type: 'Tim mạch',
      count: 2,
      monthly: 14,
      cycle: '3,8',
      conflict: '6 lần',
      suggestion: { tone: 'danger', label: '+2 bộ' },
    },
    {
      type: 'Nội soi',
      count: 4,
      monthly: 12,
      cycle: '2,1',
      conflict: '0',
      suggestion: { tone: 'ok', label: 'Đủ' },
    },
  ],
}
