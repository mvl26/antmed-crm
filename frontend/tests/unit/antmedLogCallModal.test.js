import { readFileSync } from 'fs'
import path from 'path'
import { describe, it, expect } from 'vitest'

const src = readFileSync(
  path.resolve(__dirname, '../../src/components/Antmed/LogCallModal.vue'),
  'utf8',
)

describe('LogCallModal.vue', () => {
  it('dùng logCall factory', () => {
    expect(src).toContain('logCall')
    expect(src).toContain("from '@/data/antmed'")
  })
  it('4 kết quả cuộc gọi', () => {
    for (const o of ['Nghe máy', 'Không nghe', 'Máy bận', 'Hộp thư']) {
      expect(src).toContain(o)
    }
  })
  it('dialog a11y + emit logged/update:open', () => {
    expect(src).toContain('role="dialog"')
    expect(src).toContain("emit('logged')")
    expect(src).toContain("emit('update:open'")
  })
  it('chặn submit khi thiếu outcome', () => {
    expect(src).toContain('Vui lòng chọn kết quả')
  })
})
