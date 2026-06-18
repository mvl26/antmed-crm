import { readFileSync, readdirSync } from 'fs'
import path from 'path'

// BUGFIX: src/translation.js format() làm message.replace(/{(\d+)}/g, fn) với fn đọc
// replace[number]. Gọi __('...{0}...') 1-tham-số (replace=undefined) → undefined[0] →
// TypeError "Cannot read properties of undefined (reading '0')" → component CRASH → trang trắng.
// (đã quan sát LIVE: /antmed/sales/dispatch <main> rỗng + console TypeError.)
// Dạng ĐÚNG (canonical, dùng khắp app): __('...{0}...', [args]). Guard này chặn tái diễn
// anti-pattern __('...{N}...').replace(...) và __('...{N}...') 1-arg trong mọi page/component AntMed.

const srcDir = path.resolve(__dirname, '../../src')

function walk(dir) {
  const out = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) out.push(...walk(p))
    else if (/Antmed.*\.vue$/.test(e.name)) out.push(p)
  }
  return out
}

// __('....{0}....') KHÔNG kèm tham số replace thứ 2 (kết thúc bằng ')' ngay sau chuỗi).
const BAD = /__\(\s*['"][^'"]*\{\d+\}[^'"]*['"]\s*\)/g

describe('AntMed i18n — KHÔNG __("...{N}...") thiếu mảng replace (chống crash translation)', () => {
  it('không page/component AntMed nào gọi __ placeholder thiếu replace[]', () => {
    const offenders = []
    for (const f of walk(srcDir)) {
      const src = readFileSync(f, 'utf8')
      const hits = src.match(BAD)
      if (hits) offenders.push(`${path.basename(f)}: ${hits.join(' | ')}`)
    }
    expect(offenders).toEqual([])
  })
})
