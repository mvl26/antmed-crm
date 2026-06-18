import { readFileSync } from 'fs'
import path from 'path'

// BUGFIX (FE↔BE connection): mọi AntMed endpoint là @frappe.whitelist(methods=["GET"]),
// nhưng frappe-ui resourceFetcher=frappeRequest mặc định POST (frappeRequest.js:27) ⇒
// POST tới endpoint GET-only → HTTP 403 "Not permitted" → KHÔNG có data ở browser.
// (server-side/bench gọi trực tiếp KHÔNG qua HTTP-method-check nên vẫn ra data → dễ tưởng OK.)
// => MỌI createResource gọi antmed_crm.api.antmed.* PHẢI khai báo method:'GET'. Guard test này
// chặn regression (factory thêm resource mới mà quên method:'GET' = lỗi "no data" tái diễn).

const src = readFileSync(
  path.resolve(__dirname, '../../src/data/antmed.js'),
  'utf8',
)

describe('AntMed createResource — bắt buộc khai báo method tường minh', () => {
  // Bug gốc = THIẾU method ⇒ frappe-ui mặc định POST ⇒ 403 trên endpoint GET-only.
  // Invariant: mọi resource antmed_crm.api.antmed.* PHẢI khai method tường minh
  // (đọc='GET'; mutation như initiate_recall='POST') — KHÔNG để rơi về default POST.
  it('không resource antmed_crm.api.antmed.* nào thiếu method (GET|POST)', () => {
    const blocks = src.split('createResource({').slice(1)
    const offenders = []
    for (const b of blocks) {
      const end = b.indexOf('})')
      const block = end === -1 ? b : b.slice(0, end)
      const m = block.match(/url:\s*['"](antmed_crm\.api\.antmed\.[^'"]+)['"]/)
      if (m && !/method:\s*['"](GET|POST)['"]/.test(block)) offenders.push(m[1])
    }
    expect(offenders).toEqual([])
  })
})
