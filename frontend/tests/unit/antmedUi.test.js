import { existsSync, readFileSync } from 'fs'
import path from 'path'
import {
  PILL_THEME,
  pillClass,
  barFillClass,
  heatClass,
  stageClass,
  alertClass,
  kanbanAccentClass,
  quotaRingTheme,
  ringColorVar,
  RING_COLOR_VAR,
  quotaRingStyle,
} from '../../src/utils/antmedUi'

// T1 — UI kit prototype. Test tầng thuần (antmedUi.js) + content-assert mỗi component tồn tại.
// Theo idiom dự án (antmedShell.test.js): KHÔNG @vue/test-utils.

describe('antmedUi — pill theme', () => {
  it('PILL_THEME phủ đủ 5 trạng thái mockup', () => {
    expect(Object.keys(PILL_THEME).sort()).toEqual(
      ['danger', 'info', 'neutral', 'ok', 'warn'].sort(),
    )
  })
  it('pillClass map đúng + fallback neutral cho theme lạ', () => {
    expect(pillClass('ok')).toBe(PILL_THEME.ok)
    expect(pillClass('danger')).toBe(PILL_THEME.danger)
    expect(pillClass('khong-ton-tai')).toBe(PILL_THEME.neutral)
  })
})

describe('antmedUi — bar / heat / stage / alert / kanban', () => {
  it('barFillClass default/warn/danger', () => {
    expect(barFillClass('warn')).toMatch(/amber/)
    expect(barFillClass('danger')).toMatch(/red/)
    expect(barFillClass('xxx')).toMatch(/teal/) // fallback default
  })
  it('heatClass 1..5 có class, ngoài range = rỗng', () => {
    for (let l = 1; l <= 5; l++) expect(heatClass(l)).toBeTruthy()
    expect(heatClass(0)).toBe('')
    expect(heatClass(9)).toBe('')
  })
  it('stageClass: done xanh lá, current teal, còn lại xám', () => {
    expect(stageClass('done')).toMatch(/green/)
    expect(stageClass('current')).toMatch(/teal/)
    expect(stageClass('cur')).toMatch(/teal/)
    expect(stageClass('todo')).toMatch(/ink-gray/)
  })
  it('alertClass info/warn/danger + fallback warn', () => {
    expect(alertClass('info')).toMatch(/blue/)
    expect(alertClass('danger')).toMatch(/red/)
    expect(alertClass('zzz')).toBe(alertClass('warn'))
  })
  it('kanbanAccentClass urgent/warn/ok + rỗng khi không có', () => {
    expect(kanbanAccentClass('urgent')).toMatch(/red/)
    expect(kanbanAccentClass('ok')).toMatch(/green/)
    expect(kanbanAccentClass('')).toBe('')
  })
})

describe('antmedUi — M11 quota ring (CEO A1)', () => {
  it('quotaRingTheme: đỏ ≥95 / cam ≥72 / xanh (default), biên inclusive', () => {
    expect(quotaRingTheme(95)).toBe('danger')
    expect(quotaRingTheme(96)).toBe('danger')
    expect(quotaRingTheme(94.99)).toBe('warn')
    expect(quotaRingTheme(72)).toBe('warn')
    expect(quotaRingTheme(71.99)).toBe('default')
    expect(quotaRingTheme(0)).toBe('default')
  })

  it('ringColorVar dùng CSS var token (KHÔNG hex thô) + fallback teal', () => {
    expect(ringColorVar('danger')).toBe('var(--red-600)')
    expect(ringColorVar('warn')).toBe('var(--orange-500)')
    expect(ringColorVar('default')).toBe('var(--teal-600)')
    expect(ringColorVar('khong-ton-tai')).toBe(RING_COLOR_VAR.default)
    // KHÔNG có mã màu hex thô trong map (chỉ var token).
    for (const v of Object.values(RING_COLOR_VAR)) {
      expect(v).toMatch(/^var\(--/)
      expect(v).not.toMatch(/#[0-9a-fA-F]{3,6}/)
    }
  })

  it('quotaRingStyle: conic-gradient theo % (clamp) + màu theo ngưỡng', () => {
    // 50% → góc 180deg, màu xanh (default).
    const s50 = quotaRingStyle(50)
    expect(s50.background).toContain('var(--teal-600)')
    expect(s50.background).toContain('180deg')
    // 100% → đỏ (≥95), góc 360deg.
    expect(quotaRingStyle(100).background).toContain('var(--red-600)')
    expect(quotaRingStyle(100).background).toContain('360deg')
    // 80% → cam (≥72).
    expect(quotaRingStyle(80).background).toContain('var(--orange-500)')
  })

  it('quotaRingStyle: clamp >100 → 360deg, <0 → 0deg, null/NaN → 0deg xanh', () => {
    expect(quotaRingStyle(150).background).toContain('360deg')
    expect(quotaRingStyle(-5).background).toContain('0deg')
    expect(quotaRingStyle(null).background).toContain('var(--teal-600)')
    expect(quotaRingStyle(undefined).background).toContain('0deg')
    // KHÔNG NaN lọt vào string.
    expect(quotaRingStyle('xx').background).not.toMatch(/NaN/)
  })
})

describe('UI kit — components/Antmed/ui/* tồn tại & hợp lệ', () => {
  const uiDir = path.resolve(__dirname, '../../src/components/Antmed/ui')
  const KIT = [
    'AmPill',
    'AmCard',
    'AmKpiCard',
    'AmBar',
    'AmLifecycle',
    'AmSteps',
    'AmTimeline',
    'AmFunnel',
    'AmHeatCell',
    'AmKanbanColumn',
    'AmKanbanCard',
    'AmPhoneFrame',
    'AmTablet',
    'AmRoleBand',
    'AmScanBox',
    'AmAlertBox',
    'AmSignaturePad',
  ]

  it.each(KIT)('%s.vue có <template>', (name) => {
    const file = path.join(uiDir, name + '.vue')
    expect(existsSync(file)).toBe(true)
    expect(readFileSync(file, 'utf8')).toMatch(/<template>/)
  })
})
