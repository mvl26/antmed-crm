import { readFileSync } from 'fs'
import path from 'path'

// Slice port FCRM→AntMed: Công việc (CRM Task) — màn /antmed/tasks dùng doctype CRM Task.
// Idiom: content-assert nguồn (router/nav/page/data) — KHÔNG @vue/test-utils.

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedTasks.vue'), 'utf8')

describe('Công việc — resource getTasks (GET, đúng endpoint CRM Task)', () => {
  it('data/antmed.js có getTasks → tasks.list_tasks, method GET', () => {
    expect(dataSrc).toMatch(/export function getTasks/)
    const idx = dataSrc.indexOf('export function getTasks')
    const block = dataSrc.slice(idx, idx + 600)
    expect(block).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.tasks\.list_tasks['"]/,
    )
    expect(block).toMatch(/method:\s*['"]GET['"]/)
  })
  it('getTasks CHỈ gửi param đã định nghĩa (KHÔNG {status: undefined} → BE lọc "undefined" = 0 dòng)', () => {
    const idx = dataSrc.indexOf('export function getTasks')
    const block = dataSrc.slice(idx, idx + 500)
    expect(block).toMatch(/if \(status\)/)
    expect(block).not.toMatch(/params:\s*\{\s*status,/)
  })
})

describe('Công việc — route + nav (/antmed/tasks)', () => {
  it('router.js đăng ký AntmedTasks → /antmed/tasks (lazy)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/tasks['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedTasks['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedTasks\.vue['"]\)/)
  })
  it('antmedNav.js có entry Công việc → /antmed/tasks enabled', () => {
    const idx = navSrc.indexOf("key: 'tasks'")
    expect(idx).toBeGreaterThan(-1)
    const block = navSrc.slice(idx, idx + 160)
    expect(block).toMatch(/to:\s*['"]\/antmed\/tasks['"]/)
    expect(block).toMatch(/enabled:\s*true/)
  })
})

describe('Công việc — page đọc data + tri-branch + i18n đúng', () => {
  it('đọc board.data.data + total_count/open_count (RAW dict, KHÔNG .data.data lồng)', () => {
    expect(pageSrc).toMatch(/getTasks/)
    expect(pageSrc).toMatch(/board\.data\?\.data/)
    expect(pageSrc).toMatch(/total_count/)
    expect(pageSrc).toMatch(/open_count/)
  })
  it('tri-branch loading/error/empty + KHÔNG dính bug __ placeholder thiếu replace[]', () => {
    expect(pageSrc).toMatch(/board\.loading/)
    expect(pageSrc).toMatch(/board\.error/)
    expect(pageSrc).toMatch(/hasTasks/)
    expect(pageSrc).not.toMatch(/__\(\s*['"][^'"]*\{\d+\}[^'"]*['"]\s*\)/)
  })
  it('render field công việc (title, status, priority, assigned_to_name, due_date)', () => {
    for (const f of [
      'title',
      'status',
      'priority',
      'assigned_to_name',
      'due_date',
    ]) {
      expect(pageSrc).toContain(f)
    }
  })
})
