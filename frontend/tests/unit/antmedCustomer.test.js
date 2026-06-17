import { readFileSync } from 'fs'
import path from 'path'

// TDD-FE (M01 R2 Customer 360°): 3 route mới (/antmed/hospitals, :name,
// /antmed/doctors/:name) lazy-import; page list gọi list_hospitals; detail gọi
// get_hospital/get_doctor; route CRM gốc còn nguyên; gate grep sạch
// (không axios/tanstack/antmed_crm.api). Kiểm bằng nội dung file (grep nhẹ).

const srcDir = path.resolve(__dirname, '../../src')
const read = (rel) => readFileSync(path.join(srcDir, rel), 'utf8')

const routerSrc = read('router.js')
const dataSrc = read('data/antmed.js')
const listSrc = read('pages/AntmedHospitalList.vue')
const hospitalDetailSrc = read('pages/AntmedHospitalDetail.vue')
const doctorDetailSrc = read('pages/AntmedDoctorDetail.vue')

describe('AntMed FE Customer 360° (M01 R2) — routes', () => {
  it('route /antmed/hospitals tồn tại + name AntmedHospitalList + lazy import', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/hospitals['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedHospitalList['"]/)
    expect(routerSrc).toMatch(
      /component:\s*\(\)\s*=>\s*import\(['"]@\/pages\/AntmedHospitalList\.vue['"]\)/,
    )
  })

  it('route /antmed/hospitals/:name tồn tại + name AntmedHospitalDetail + lazy + props', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/hospitals\/:name['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedHospitalDetail['"]/)
    expect(routerSrc).toMatch(
      /component:\s*\(\)\s*=>\s*import\(['"]@\/pages\/AntmedHospitalDetail\.vue['"]\)/,
    )
  })

  it('route /antmed/doctors/:name tồn tại + name AntmedDoctorDetail + lazy + props', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/doctors\/:name['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedDoctorDetail['"]/)
    expect(routerSrc).toMatch(
      /component:\s*\(\)\s*=>\s*import\(['"]@\/pages\/AntmedDoctorDetail\.vue['"]\)/,
    )
  })

  it('KHÔNG đụng route Frappe CRM gốc (Leads/Deals/Contacts/Organizations còn nguyên)', () => {
    expect(routerSrc).toMatch(/name:\s*['"]Leads['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]Deals['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]Contacts['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]Organizations['"]/)
  })

  it('route /antmed R1 (AntmedHome) vẫn còn', () => {
    expect(routerSrc).toMatch(/name:\s*['"]AntmedHome['"]/)
  })
})

describe('AntMed FE Customer 360° (M01 R2) — resource naming contract', () => {
  it('data/antmed.js expose list_hospitals / get_hospital / list_doctors / get_doctor', () => {
    expect(dataSrc).toMatch(/url:\s*['"]crm\.api\.antmed\.customer\.list_hospitals['"]/)
    expect(dataSrc).toMatch(/url:\s*['"]crm\.api\.antmed\.customer\.get_hospital['"]/)
    expect(dataSrc).toMatch(/url:\s*['"]crm\.api\.antmed\.customer\.list_doctors['"]/)
    expect(dataSrc).toMatch(/url:\s*['"]crm\.api\.antmed\.customer\.get_doctor['"]/)
  })

  it('AntmedHospitalList gọi đúng url list_hospitals (qua resource layer)', () => {
    expect(listSrc).toMatch(/listHospitals/)
    expect(listSrc).toMatch(/from\s*['"]@\/data\/antmed['"]/)
  })

  it('AntmedHospitalDetail gọi get_hospital; AntmedDoctorDetail gọi get_doctor', () => {
    expect(hospitalDetailSrc).toMatch(/getHospital/)
    expect(doctorDetailSrc).toMatch(/getDoctor/)
  })
})

describe('AntMed FE Customer 360° (M01 R2) — grep gate (di sản stack cũ = 0)', () => {
  const allFiles = [dataSrc, listSrc, hospitalDetailSrc, doctorDetailSrc, routerSrc]

  it('KHÔNG axios / @tanstack/vue-query / @/api layer', () => {
    for (const src of allFiles) {
      expect(src).not.toMatch(/axios/)
      expect(src).not.toMatch(/@tanstack\/vue-query/)
      expect(src).not.toMatch(/from ['"]@\/api\//)
    }
  })

  it('KHÔNG dùng namespace sai antmed_crm.api (app này in-place = crm.api.antmed)', () => {
    for (const src of allFiles) {
      expect(src).not.toMatch(/antmed_crm\.api/)
    }
  })

  it('KHÔNG dùng createListResource cho endpoint trả dict bọc {data,total_count}', () => {
    // R2 chốt: list trả dict bọc → createResource (đọc r.data.data), KHÔNG createListResource.
    expect(dataSrc).not.toMatch(/createListResource/)
  })

  it('KHÔNG raw frappe.client.* (lookup phải qua endpoint permission-aware)', () => {
    for (const src of [listSrc, hospitalDetailSrc, doctorDetailSrc]) {
      expect(src).not.toMatch(/frappe\.client\.(get_value|get_list)/)
    }
  })
})
