import { readFileSync } from 'fs'
import path from 'path'
import { describe, it, expect } from 'vitest'

const src = readFileSync(
  path.resolve(__dirname, '../../src/data/antmed.js'),
  'utf8',
)

const FACTORIES = [
  ['listCareNotes', 'list_care_notes', 'GET'],
  ['saveCareNote', 'save_care_note', 'POST'],
  ['listVisits', 'list_visits', 'GET'],
  ['getVisit', 'get_visit', 'GET'],
  ['listGifts', 'list_gifts', 'GET'],
  ['createGift', 'create_gift', 'POST'],
  ['checkInDoctor', 'check_in', 'POST'],
  ['logCall', 'log_call', 'POST'],
  ['listCallLogs', 'list_call_logs', 'GET'],
]

describe('antmed.js — doctor_care + call factories', () => {
  for (const [fn, endpoint, method] of FACTORIES) {
    it(`${fn} → ${endpoint} (${method})`, () => {
      expect(src).toContain(`export function ${fn}`)
      expect(src).toContain(`antmed_crm.api.antmed.doctor_care.${endpoint}`)
    })
  }
  it('không dùng prefix crm.api.* (legacy) cho doctor_care', () => {
    // 'crm.api.antmed.doctor_care' KHÔNG được đứng sau 'antmed_' (prefix legacy sai)
    expect(src).not.toMatch(/[^_]crm\.api\.antmed\.doctor_care/)
  })
})
