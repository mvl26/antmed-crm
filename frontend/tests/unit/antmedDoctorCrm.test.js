import { readFileSync } from 'fs'
import path from 'path'
import { describe, it, expect } from 'vitest'

const src = readFileSync(
  path.resolve(__dirname, '../../src/pages/AntmedDoctorDetail.vue'),
  'utf8',
)

describe('AntmedDoctorDetail.vue — CRM Bác sỹ', () => {
  it('3 nút hành động: gọi / Zalo / check-in', () => {
    expect(src).toContain('startCall')
    expect(src).toContain('openZalo')
    expect(src).toContain('checkIn')
  })
  it('4 tab notes/visits/gifts/calls', () => {
    for (const t of ['notes', 'visits', 'gifts', 'calls']) {
      expect(src).toContain(`'${t}'`)
    }
  })
  it('mở dialer tel: + LogCallModal', () => {
    expect(src).toContain("'tel:'")
    expect(src).toContain('LogCallModal')
  })
  it('wire 4 resource list', () => {
    for (const r of [
      'listCareNotes',
      'listVisits',
      'listGifts',
      'listCallLogs',
    ]) {
      expect(src).toContain(r)
    }
  })
  it('form thêm nhanh ghi chú + quà', () => {
    expect(src).toContain('saveCareNote')
    expect(src).toContain('createGift')
    expect(src).toContain('addNote')
    expect(src).toContain('addGift')
  })
})
