import { readFileSync } from 'fs'
import path from 'path'
import { describe, it, expect } from 'vitest'

const layoutSrc = readFileSync(
  path.resolve(__dirname, '../../src/components/Antmed/AntmedLayout.vue'),
  'utf8',
)

describe('AntmedLayout — wire quick-search palette', () => {
  it('import + render AntmedQuickSearch (v-model:open)', () => {
    expect(layoutSrc).toContain('AntmedQuickSearch')
    expect(layoutSrc).toMatch(/<AntmedQuickSearch[\s\S]*v-model:open="searchOpen"/)
  })
  it('ô header là button mở palette (KHÔNG còn <input> chết)', () => {
    expect(layoutSrc).toContain('searchOpen = true')
    // input cũ "placeholder:text-white/60" đã bị thay
    expect(layoutSrc).not.toContain('placeholder:text-white/60')
  })
  it('hotkey ⌘/Ctrl+K mở palette', () => {
    expect(layoutSrc).toMatch(/metaKey \|\| .*ctrlKey/)
    expect(layoutSrc).toContain("addEventListener('keydown'")
  })
})
