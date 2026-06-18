import { readFileSync } from 'fs'
import path from 'path'
import { describe, it, expect } from 'vitest'

const root = path.resolve(__dirname, '../../src')
const compSrc = readFileSync(
  path.join(root, 'components/Antmed/AntmedQuickSearch.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(root, 'data/antmed.js'), 'utf8')

describe('antmed.js — factory useGlobalSearch', () => {
  it('có factory trỏ method path đúng + method GET', () => {
    expect(dataSrc).toMatch(/export function useGlobalSearch/)
    expect(dataSrc).toContain('antmed_crm.api.antmed.search.global_search')
    expect(dataSrc).toMatch(/useGlobalSearch[\s\S]{0,200}method: 'GET'/)
  })
})

describe('AntmedQuickSearch.vue — command palette', () => {
  it('dùng searchFunctions + useGlobalSearch', () => {
    expect(compSrc).toContain('searchFunctions')
    expect(compSrc).toContain('useGlobalSearch')
  })
  it('overlay Teleport + role dialog/listbox (a11y)', () => {
    expect(compSrc).toContain('<Teleport')
    expect(compSrc).toContain('role="dialog"')
    expect(compSrc).toContain('role="listbox"')
  })
  it('xử lý phím Escape / ArrowDown / Enter', () => {
    expect(compSrc).toContain('Escape')
    expect(compSrc).toContain('ArrowDown')
    expect(compSrc).toContain('Enter')
  })
  it('điều hướng router.push + đóng (emit update:open)', () => {
    expect(compSrc).toContain('router.push')
    expect(compSrc).toContain("emit('update:open'")
  })
  it('có nhóm Bộ dụng cụ + Giao phòng mổ (instrument_sets/deliveries)', () => {
    expect(compSrc).toContain('instrument_sets')
    expect(compSrc).toContain('deliveries')
    expect(compSrc).toContain('/antmed/instruments/')
    expect(compSrc).toContain('/antmed/deliveries/')
  })
})
