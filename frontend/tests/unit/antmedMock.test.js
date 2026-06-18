import * as mock from '../../src/data/antmedMock'
import { LIFECYCLE_STAGES } from '../../src/data/antmedMock'
import { PILL_THEME } from '../../src/utils/antmedUi'

// T2 — Dữ liệu mẫu tĩnh bám mockup (Q1: "đúng số liệu trong mockup").
// Invariant test: 20 export theo màn tồn tại, mảng không rỗng, field bắt buộc có mặt,
// tone pill nằm trong PILL_THEME (link với UI kit T1). Idiom dự án: pure-logic,
// import ES module + assert shape — KHÔNG @vue/test-utils.

const TONES = Object.keys(PILL_THEME) // ok/warn/danger/info/neutral
const nonEmptyArray = (v) => Array.isArray(v) && v.length > 0
const validTone = (t) =>
  t === undefined ||
  t === null ||
  t === '' ||
  t === 'default' ||
  TONES.includes(t)

const SCREEN_EXPORTS = [
  'ceoDashboard',
  'contracts',
  'revenue',
  'dispatch',
  'team',
  'approvals',
  'repToday',
  'doctor',
  'warehouseExport',
  'consignment',
  'lotTrace',
  'docsPending',
  'coCq',
  'reconciliation',
  'receivables',
  'commission',
  'portal',
  'users',
  'audit',
  'instruments',
]

describe('antmedMock — 20 export theo màn (A1..I1)', () => {
  it.each(SCREEN_EXPORTS)('export %s là object định danh', (key) => {
    expect(mock[key]).toBeDefined()
    expect(typeof mock[key]).toBe('object')
    expect(mock[key]).not.toBeNull()
  })

  it('LIFECYCLE_STAGES = 7 trạng thái mockup (SS·Đặt·Giao·SD·Trả·Xử lý·SS lại)', () => {
    expect(LIFECYCLE_STAGES).toEqual([
      'SS',
      'Đặt',
      'Giao',
      'SD',
      'Trả',
      'Xử lý',
      'SS lại',
    ])
  })
})

describe('A1 · CEO Dashboard điều hành', () => {
  const d = mock.ceoDashboard
  it('4 KPI mỗi cái có label+value', () => {
    expect(d.kpis).toHaveLength(4)
    d.kpis.forEach((k) => {
      expect(k.label).toBeTruthy()
      expect(k.value).toBeTruthy()
    })
  })
  it('Top 10 BV: name + quotaPct số + tone hợp lệ', () => {
    expect(nonEmptyArray(d.topHospitals)).toBe(true)
    d.topHospitals.forEach((h) => {
      expect(h.name).toBeTruthy()
      expect(typeof h.quotaPct).toBe('number')
      expect(validTone(h.tone)).toBe(true)
    })
  })
  it('Funnel pipeline: stage + count số', () => {
    expect(nonEmptyArray(d.funnel)).toBe(true)
    d.funnel.forEach((f) => {
      expect(f.stage).toBeTruthy()
      expect(typeof f.count).toBe('number')
    })
  })
  it('Cảnh báo điều hành: tone + text', () => {
    expect(nonEmptyArray(d.alerts)).toBe(true)
    d.alerts.forEach((a) => {
      expect(TONES.includes(a.tone)).toBe(true)
      expect(a.text).toBeTruthy()
    })
  })
})

describe('A2 · Sức khỏe hợp đồng', () => {
  const d = mock.contracts
  it('rows HĐ: contractNo + hospital + status + statusTone hợp lệ', () => {
    expect(nonEmptyArray(d.rows)).toBe(true)
    d.rows.forEach((r) => {
      expect(r.contractNo).toBeTruthy()
      expect(r.hospital).toBeTruthy()
      expect(r.status).toBeTruthy()
      expect(TONES.includes(r.statusTone)).toBe(true)
    })
  })
  it('top SKU: sku + pct số', () => {
    expect(nonEmptyArray(d.topSku)).toBe(true)
    d.topSku.forEach((s) => {
      expect(s.sku).toBeTruthy()
      expect(typeof s.pct).toBe('number')
    })
  })
})

describe('A3 · Báo cáo doanh thu', () => {
  const d = mock.revenue
  it('3 KPI', () => {
    expect(d.kpis).toHaveLength(3)
    d.kpis.forEach((k) => expect(k.label && k.value).toBeTruthy())
  })
  it('heatmap NV×BV: rep + cells (lvl 0..5) + total; cột khớp số cells', () => {
    expect(nonEmptyArray(d.heatColumns)).toBe(true)
    expect(nonEmptyArray(d.heatmap)).toBe(true)
    d.heatmap.forEach((row) => {
      expect(row.rep).toBeTruthy()
      expect(row.total).toBeTruthy()
      expect(row.cells).toHaveLength(d.heatColumns.length)
      row.cells.forEach((c) => {
        expect(typeof c.lvl).toBe('number')
        expect(c.lvl).toBeGreaterThanOrEqual(0)
        expect(c.lvl).toBeLessThanOrEqual(5)
      })
    })
  })
})

describe('B1 · Kanban điều phối', () => {
  const d = mock.dispatch
  it('đúng 4 cột, mỗi cột title + count + cards', () => {
    expect(d.columns).toHaveLength(4)
    d.columns.forEach((col) => {
      expect(col.title).toBeTruthy()
      expect(typeof col.count).toBe('number')
      expect(nonEmptyArray(col.cards)).toBe(true)
      col.cards.forEach((c) => expect(c.hospital).toBeTruthy())
    })
  })
  it('legend không rỗng', () => {
    expect(nonEmptyArray(d.legend)).toBe(true)
  })
})

describe('B2 · Quản lý đội ngũ', () => {
  const d = mock.team
  it('members: name + slaPct + dsPct số', () => {
    expect(nonEmptyArray(d.members)).toBe(true)
    d.members.forEach((m) => {
      expect(m.name).toBeTruthy()
      expect(m.slaPct).toBeTruthy()
      expect(typeof m.dsPct).toBe('number')
    })
  })
  it('profile + checkins timeline + bộ DC đang quản lý', () => {
    expect(d.profile.name).toBeTruthy()
    expect(nonEmptyArray(d.profile.checkins)).toBe(true)
    expect(nonEmptyArray(d.setsManaged)).toBe(true)
  })
})

describe('B3 · Hộp duyệt yêu cầu', () => {
  const d = mock.approvals
  it('inbox + summary + detail có alert', () => {
    expect(nonEmptyArray(d.inbox)).toBe(true)
    d.inbox.forEach((i) => expect(i.type && i.who && i.desc).toBeTruthy())
    expect(nonEmptyArray(d.summary)).toBe(true)
    expect(d.detail.code).toBeTruthy()
    expect(TONES.includes(d.detail.alert.tone)).toBe(true)
  })
})

describe('C1/C2/C3/C5 · NV mobile (repToday)', () => {
  const d = mock.repToday
  it('stats + cases hôm nay', () => {
    expect(nonEmptyArray(d.stats)).toBe(true)
    expect(nonEmptyArray(d.cases)).toBe(true)
    d.cases.forEach((c) => expect(c.time && c.hospital).toBeTruthy())
  })
  it('wizard 4 bước (done/current/todo) + items VT', () => {
    expect(d.wizard.steps).toHaveLength(4)
    d.wizard.steps.forEach((s) =>
      expect(['done', 'current', 'todo']).toContain(s.state),
    )
    expect(nonEmptyArray(d.wizard.items)).toBe(true)
  })
  it('checklist 42 món (checked<=total) + lifecycle 7 trạng thái', () => {
    expect(d.checklist.total).toBe(42)
    expect(d.checklist.checked).toBeLessThanOrEqual(d.checklist.total)
    expect(nonEmptyArray(d.checklist.items)).toBe(true)
    expect(d.checklist.lifecycle.stages).toEqual(LIFECYCLE_STAGES)
  })
  it('offline: pendingCount khớp độ dài queue', () => {
    expect(nonEmptyArray(d.offline.queue)).toBe(true)
    expect(d.offline.pendingCount).toBe(d.offline.queue.length)
  })
})

describe('C4 · CRM Bác sỹ', () => {
  const d = mock.doctor
  it('profile + tabs + notes', () => {
    expect(d.name).toBeTruthy()
    expect(nonEmptyArray(d.tabs)).toBe(true)
    expect(nonEmptyArray(d.notes)).toBe(true)
    d.notes.forEach((n) => expect(n.date && n.text).toBeTruthy())
  })
})

describe('D1 · Xuất kho (QR)', () => {
  const d = mock.warehouseExport
  it('items có lot + coCq{tone,label} + recentSlips', () => {
    expect(nonEmptyArray(d.items)).toBe(true)
    d.items.forEach((it) => {
      expect(it.sku && it.lot).toBeTruthy()
      expect(TONES.includes(it.coCq.tone)).toBe(true)
      expect(it.coCq.label).toBeTruthy()
    })
    expect(nonEmptyArray(d.recentSlips)).toBe(true)
  })
})

describe('D2 · Kho ký gửi BV', () => {
  const d = mock.consignment
  it('3 KPI + rows đối chiếu (status + statusTone)', () => {
    expect(d.kpis).toHaveLength(3)
    expect(nonEmptyArray(d.rows)).toBe(true)
    d.rows.forEach((r) => {
      expect(r.sku && r.status).toBeTruthy()
      expect(TONES.includes(r.statusTone)).toBe(true)
    })
  })
})

describe('D3 · Truy vết lot', () => {
  const d = mock.lotTrace
  it('lotCode + info[] + tree string', () => {
    expect(d.lotCode).toBeTruthy()
    expect(nonEmptyArray(d.info)).toBe(true)
    d.info.forEach((f) => expect(f.field && f.value).toBeTruthy())
    expect(typeof d.tree).toBe('string')
    expect(d.tree.length).toBeGreaterThan(0)
  })
})

describe('E1 · Hàng chờ phát hành', () => {
  const d = mock.docsPending
  it('rows (do/hospital/missing) + summary + detail.lots', () => {
    expect(nonEmptyArray(d.rows)).toBe(true)
    d.rows.forEach((r) => {
      expect(r.do && r.hospital).toBeTruthy()
      expect(TONES.includes(r.missing.tone)).toBe(true)
    })
    expect(nonEmptyArray(d.summary)).toBe(true)
    expect(nonEmptyArray(d.detail.lots)).toBe(true)
  })
})

describe('E2 · Kho CO/CQ', () => {
  const d = mock.coCq
  it('suppliers (count số) + files (hash, type)', () => {
    expect(nonEmptyArray(d.suppliers)).toBe(true)
    d.suppliers.forEach((s) => {
      expect(s.name).toBeTruthy()
      expect(typeof s.count).toBe('number')
    })
    expect(nonEmptyArray(d.files)).toBe(true)
    d.files.forEach((f) => expect(f.file && f.lot && f.type).toBeTruthy())
  })
})

describe('E3 · Đối soát ký nhận', () => {
  const d = mock.reconciliation
  it('4 KPI + rows (status + statusTone)', () => {
    expect(d.kpis).toHaveLength(4)
    expect(nonEmptyArray(d.rows)).toBe(true)
    d.rows.forEach((r) => {
      expect(r.do && r.status).toBeTruthy()
      expect(TONES.includes(r.statusTone)).toBe(true)
    })
  })
})

describe('F1 · Công nợ theo BV', () => {
  const d = mock.receivables
  it('4 KPI aging + bucketLabels + rows aging (buckets lvl 0..5)', () => {
    expect(d.kpis).toHaveLength(4)
    expect(nonEmptyArray(d.bucketLabels)).toBe(true)
    expect(nonEmptyArray(d.rows)).toBe(true)
    d.rows.forEach((r) => {
      expect(r.hospital && r.total).toBeTruthy()
      expect(r.buckets).toHaveLength(d.bucketLabels.length)
      r.buckets.forEach((b) => {
        expect(b.lvl).toBeGreaterThanOrEqual(0)
        expect(b.lvl).toBeLessThanOrEqual(5)
      })
    })
  })
})

describe('F2 · Hoa hồng NV', () => {
  const d = mock.commission
  it('total + rules + rows (kpiTone hợp lệ)', () => {
    expect(d.total).toBeTruthy()
    expect(d.rules).toBeTruthy()
    expect(nonEmptyArray(d.rows)).toBe(true)
    d.rows.forEach((r) => {
      expect(r.name && r.total).toBeTruthy()
      expect(validTone(r.kpiTone)).toBe(true)
    })
  })
})

describe('G1/G2 · Portal BV', () => {
  const d = mock.portal
  it('actions + callForm.catalog + notifications + history', () => {
    expect(nonEmptyArray(d.actions)).toBe(true)
    d.actions.forEach((a) => expect(a.icon && a.title).toBeTruthy())
    expect(nonEmptyArray(d.callForm.catalog)).toBe(true)
    expect(nonEmptyArray(d.notifications)).toBe(true)
    expect(nonEmptyArray(d.history)).toBe(true)
    d.history.forEach((h) => expect(TONES.includes(h.payment.tone)).toBe(true))
  })
})

describe('H1 · User & Role', () => {
  const d = mock.users
  it('rows (role/scope/2FA/status với tone) + permMatrix', () => {
    expect(nonEmptyArray(d.rows)).toBe(true)
    d.rows.forEach((u) => {
      expect(u.name && u.email && u.role).toBeTruthy()
      expect(TONES.includes(u.twoFa.tone)).toBe(true)
      expect(TONES.includes(u.status.tone)).toBe(true)
    })
    expect(nonEmptyArray(d.permMatrix)).toBe(true)
    d.permMatrix.forEach((p) => expect(p.module).toBeTruthy())
  })
})

describe('H2 · Audit log', () => {
  const d = mock.audit
  it('rows (actor/action/object/diff) + actionTone hợp lệ + filters', () => {
    expect(nonEmptyArray(d.rows)).toBe(true)
    d.rows.forEach((r) => {
      expect(r.actor && r.action && r.object).toBeTruthy()
      expect(TONES.includes(r.actionTone)).toBe(true)
    })
    expect(nonEmptyArray(d.objectFilters)).toBe(true)
    expect(nonEmptyArray(d.actionFilters)).toBe(true)
  })
})

describe('I1 · Bộ dụng cụ — vòng đời', () => {
  const d = mock.instruments
  it('4 KPI + sets (current index trong stages) + frequency', () => {
    expect(d.kpis).toHaveLength(4)
    expect(d.stages).toEqual(LIFECYCLE_STAGES)
    expect(nonEmptyArray(d.sets)).toBe(true)
    d.sets.forEach((s) => {
      expect(s.code && s.name).toBeTruthy()
      expect(typeof s.current).toBe('number')
      expect(s.current).toBeGreaterThanOrEqual(0)
      expect(s.current).toBeLessThan(LIFECYCLE_STAGES.length)
    })
    expect(nonEmptyArray(d.frequency)).toBe(true)
    d.frequency.forEach((f) => {
      expect(f.type).toBeTruthy()
      expect(typeof f.count).toBe('number')
      expect(TONES.includes(f.suggestion.tone)).toBe(true)
    })
  })
})
