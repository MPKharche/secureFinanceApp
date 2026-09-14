import { describe, expect, it } from 'vitest'
import { sortAccountsByDisplayName, clientLoanTitle, formatLoanNextDue } from './account-utils'

describe('sortAccountsByDisplayName', () => {
  it('orders accounts by display name when present and falls back to name', () => {
    const accounts = [
      { id: '1', name: 'Alpha', display_name: 'Vacation' },
      { id: '2', name: 'Zulu', display_name: null },
      { id: '3', name: 'Checking', display_name: 'Bills' },
    ]

    expect(sortAccountsByDisplayName(accounts).map((account) => account.id)).toEqual([
      '3',
      '1',
      '2',
    ])
  })

  it('does not mutate the API account list', () => {
    const accounts = [{ name: 'Zulu' }, { name: 'Alpha' }]

    sortAccountsByDisplayName(accounts)

    expect(accounts.map((account) => account.name)).toEqual(['Zulu', 'Alpha'])
  })
})


describe('clientLoanTitle', () => {
  it('strips KM meta and rate/EMI noise from NRP display name', () => {
    const raw =
      'ICICI NRP · 7.75% · EMI ₹1,21,543 · tenor 130 | KM:disbursal_phases=5;pre_emi/partial→full@May-26;rate_path=9→8.5→8→7.75;proj=cash_hist→current_EMI | Godrej U114 | TBPUN…5113 | OS₹1.07Cr@13-Sep'
    expect(clientLoanTitle(raw)).toBe('ICICI NRP · Godrej U114')
  })

  it('strips no_flatten / DO_NOT_FLATTEN style Pru meta', () => {
    const raw =
      'ICICI Pru A8884526 — NO EMI · half-yr@7.96% prin · O/S ₹1.75L@18-May-26 (₹1.60L+₹14805·paid0) | FORECLOSE>SV | KM:no_emi;half_yr;vol;no_flatten'
    expect(clientLoanTitle(raw)).toBe('ICICI Pru A8884526')
  })

  it('passes through a clean title', () => {
    expect(clientLoanTitle('Home Loan')).toBe('Home Loan')
  })
})

describe('formatLoanNextDue', () => {
  it('formats ISO date', () => {
    expect(formatLoanNextDue('2026-10-05', 'en-IN')).toMatch(/5/)
  })
  it('returns em dash when missing', () => {
    expect(formatLoanNextDue(null)).toBe('—')
  })
})
