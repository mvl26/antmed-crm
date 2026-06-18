import { describe, it, expect } from 'vitest'
import {
  normalize,
  featherFor,
  searchFunctions,
} from '../../src/data/antmedSearchSources'

describe('normalize — bỏ dấu tiếng Việt', () => {
  it('bỏ dấu + lowercase + trim', () => {
    expect(normalize('  Bệnh Viện  ')).toBe('benh vien')
    expect(normalize('Hợp đồng')).toBe('hop dong')
  })
})

describe('featherFor', () => {
  it('map emoji nav → tên feather; lạ → fallback', () => {
    expect(featherFor('🏥')).toBe('home')
    expect(typeof featherFor('🤷')).toBe('string')
  })
})

describe('searchFunctions', () => {
  it('khớp KHÔNG phân biệt dấu', () => {
    const r = searchFunctions('benh vien')
    expect(r.some((x) => x.label === 'Bệnh viện')).toBe(true)
  })
  it('mỗi kết quả có type=function + to + icon string', () => {
    const r = searchFunctions('hop dong')
    expect(r.length).toBeGreaterThan(0)
    for (const it of r) {
      expect(it.type).toBe('function')
      expect(typeof it.to).toBe('string')
      expect(typeof it.icon).toBe('string')
    }
  })
  it('dedup theo `to` (không trùng đích)', () => {
    const tos = searchFunctions('').map((x) => x.to)
    expect(new Set(tos).size).toBe(tos.length)
  })
  it('query rỗng → gợi ý (≤ 8, không rỗng)', () => {
    const r = searchFunctions('')
    expect(r.length).toBeGreaterThan(0)
    expect(r.length).toBeLessThanOrEqual(8)
  })
  it('không khớp → mảng rỗng', () => {
    expect(searchFunctions('zzqxwv')).toEqual([])
  })
})
