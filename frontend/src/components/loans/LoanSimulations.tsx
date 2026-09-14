import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calculator, DollarSign, Percent, Settings2 } from 'lucide-react'
import { formatCurrency } from '@/lib/format'
import {
  FrozenScrollTable,
  FrozenTd,
  FrozenTh,
} from '@/components/ui/frozen-scroll-table'
import { cn } from '@/lib/utils'

interface LoanSimulationsProps {
  accountId: string
  currentEmi: number
  outstandingBalance: number
  currentRate: number
  remainingMonths: number
  currency?: string
  locale?: string
  /** Hint from account name/notes — NRP must not force 0% penalty */
  isNrpOrCommercial?: boolean
}

type PenaltyBasis = 'outstanding' | 'prepayment_amount'

interface KeepDuration {
  new_emi: number
  delta_emi: number
  months: number
  delta_months: number
  total_interest: number
  interest_delta: number
  interest_saved: number
}

interface KeepEmi {
  emi: number
  delta_emi: number
  new_tenure_months: number | null
  delta_months: number | null
  total_interest: number | null
  interest_delta: number | null
  interest_saved: number | null
  negative_amortisation?: boolean
  monthly_interest?: number
  emi_shortfall?: number
}

interface RateChangeResult {
  current_rate: number
  new_rate: number
  rate_change: number
  current_emi: number | null
  outstanding_balance: number
  remaining_months: number
  is_interest_only?: boolean
  keep_duration: KeepDuration | null
  keep_emi: KeepEmi | null
  recommended?: string
  tenure_cut_usually_wins?: boolean
  negative_amortisation_risk?: boolean
  is_rate_cut?: boolean
  is_rate_hike?: boolean
  rate_ladder?: RateLadderRow[]
  note?: string
  // legacy
  new_emi?: number | null
  emi_change?: number | null
  interest_difference?: number | null
  is_favorable?: boolean
}

interface RateLadderRow {
  rate_step: number
  new_rate: number
  delta_months_if_emi_kept: number | null
  delta_emi_if_duration_kept: number | null
  net_extra_interest: number | null
  interest_impact_keep_emi: number | null
  interest_impact_keep_duration: number | null
  negative_amortisation?: boolean
}

interface EarlyPaymentResult {
  current_state: {
    outstanding_balance: number
    current_emi: number
    remaining_months: number
    current_interest_rate: number
  }
  prepayment: { amount: number; date: string; new_principal: number }
  penalty?: {
    rate: number
    basis: string
    amount: number
    defaults?: { penalty_rate: number; penalty_basis: string; reason: string }
  }
  reduce_emi: {
    new_emi: number
    emi_reduction: number
    emi_reduction_percent: number
    tenure_months: number
    interest_saved: number
    total_savings: number
    bank_default_trap?: boolean
  } | null
  reduce_tenure: {
    emi: number
    new_tenure_months: number
    months_saved: number
    new_payoff_date: string | null
    interest_saved: number
    total_savings: number
    usually_wins?: boolean
  } | null
  recommended?: string
  invest_elsewhere?: {
    alt_return_pct: number
    horizon_months: number
    alt_earnings: number
    prepay_net_benefit: number
    prefer_prepay: boolean
    edge?: number
  }
  is_interest_only?: boolean
  note?: string
}

interface PreclosureResult {
  closure_date: string
  outstanding_principal: number
  accrued_interest: number
  prepayment_penalty: number
  prepayment_penalty_rate: number
  prepayment_penalty_basis?: string
  total_payoff_amount: number
  interest_saved: number
  net_savings: number
  paid_to_date: { principal: number; interest: number; total: number }
  remaining_emis: number
  is_interest_only?: boolean
}

function authHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('token')}`,
    'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
  }
}

function AssumptionChip({
  label,
  value,
  onClick,
}: {
  label: string
  value: string
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/60 hover:bg-muted px-2 py-0.5 text-[10px] sm:text-[11px] transition-colors text-foreground"
    >
      <span className="text-foreground/70">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </button>
  )
}

function moneyTone(n: number | null | undefined, invert = false) {
  if (n == null || n === 0) return 'text-foreground'
  const good = invert ? n < 0 : n > 0
  return good
    ? 'text-emerald-700 dark:text-emerald-300'
    : 'text-rose-700 dark:text-rose-300'
}

function fmtDeltaMoney(n: number | null | undefined, currency: string, locale: string) {
  if (n == null) return '—'
  const sign = n > 0 ? '+' : ''
  return `${sign}${formatCurrency(n, currency, locale)}`
}

function fmtDeltaMonths(n: number | null | undefined) {
  if (n == null) return '—'
  if (n === 0) return '0'
  return n > 0 ? `+${n}` : String(n)
}

function Signed({
  value,
  currency,
  locale,
  invert,
}: {
  value: number | null | undefined
  currency: string
  locale: string
  invert?: boolean
}) {
  return (
    <span className={cn('tabular-nums font-medium', moneyTone(value, invert))}>
      {fmtDeltaMoney(value, currency, locale)}
    </span>
  )
}

export function LoanSimulations({
  accountId,
  currentEmi,
  outstandingBalance: _outstandingBalance,
  currentRate,
  remainingMonths: _remainingMonths,
  currency = 'USD',
  locale = 'en-US',
  isNrpOrCommercial = false,
}: LoanSimulationsProps) {
  void _outstandingBalance
  void _remainingMonths

  const [assumptionsOpen, setAssumptionsOpen] = useState(false)
  // G4: 0% OK for floating retail HL; NRP/commercial must NOT be forced to zero
  const [penaltyRate, setPenaltyRate] = useState(isNrpOrCommercial ? '2' : '0')
  const [penaltyBasis, setPenaltyBasis] = useState<PenaltyBasis>('outstanding')
  const [altReturn, setAltReturn] = useState('7')
  const [defaultsLoaded, setDefaultsLoaded] = useState(false)

  const [earlyPaymentAmount, setEarlyPaymentAmount] = useState('')
  const [earlyPaymentDate, setEarlyPaymentDate] = useState(new Date().toISOString().split('T')[0])
  const [earlyPaymentResult, setEarlyPaymentResult] = useState<EarlyPaymentResult | null>(null)
  const [earlyPaymentLoading, setEarlyPaymentLoading] = useState(false)

  const [closureDate, setClosureDate] = useState(new Date().toISOString().split('T')[0])
  const [preclosureResult, setPreclosureResult] = useState<PreclosureResult | null>(null)
  const [preclosureLoading, setPreclosureLoading] = useState(false)

  const [newRate, setNewRate] = useState('')
  const [rateEffectiveDate, setRateEffectiveDate] = useState(new Date().toISOString().split('T')[0])
  const [rateChangeResult, setRateChangeResult] = useState<RateChangeResult | null>(null)
  const [rateChangeLoading, setRateChangeLoading] = useState(false)
  // Bank trap escape: keep EMI is the one-tap default
  const [preferredPath, setPreferredPath] = useState<'keep_emi' | 'keep_duration'>('keep_emi')

  const [error, setError] = useState('')

  const ladderQuery = useQuery({
    queryKey: ['loan-rate-ladder', accountId],
    queryFn: async () => {
      const r = await fetch('/api/v1/loans/simulations/rate-ladder', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ account_id: accountId }),
      })
      if (!r.ok) throw new Error('Ready-reference failed')
      return r.json() as Promise<{
        rate_ladder: RateLadderRow[]
        is_interest_only?: boolean
        current_rate?: number
        penalty_defaults?: {
          penalty_rate: number
          penalty_basis: string
          reason: string
        }
      }>
    },
  })

  useEffect(() => {
    if (defaultsLoaded) return
    const d = ladderQuery.data?.penalty_defaults
    if (d) {
      setPenaltyRate(String(d.penalty_rate))
      setPenaltyBasis((d.penalty_basis as PenaltyBasis) || 'outstanding')
      setDefaultsLoaded(true)
    } else if (isNrpOrCommercial && !defaultsLoaded) {
      setPenaltyRate('2')
      setDefaultsLoaded(true)
    }
  }, [ladderQuery.data, defaultsLoaded, isNrpOrCommercial])

  const penaltyPayload = useMemo(
    () => ({
      penalty_rate: parseFloat(penaltyRate || '0'),
      penalty_basis: penaltyBasis,
    }),
    [penaltyRate, penaltyBasis],
  )

  const ladderRows: RateLadderRow[] =
    rateChangeResult?.rate_ladder?.length
      ? rateChangeResult.rate_ladder
      : ladderQuery.data?.rate_ladder || []

  const simulateEarlyPayment = async () => {
    setError('')
    setEarlyPaymentLoading(true)
    try {
      const response = await fetch('/api/v1/loans/simulations/early-payment', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          account_id: accountId,
          prepayment_amount: parseFloat(earlyPaymentAmount),
          prepayment_date: earlyPaymentDate,
          alt_return_pct: parseFloat(altReturn || '7'),
          ...penaltyPayload,
        }),
      })
      if (!response.ok) throw new Error('Simulation failed')
      setEarlyPaymentResult(await response.json())
    } catch (err) {
      setError('Could not run prepay simulation')
      console.error(err)
    } finally {
      setEarlyPaymentLoading(false)
    }
  }

  const simulatePreclosure = async () => {
    setError('')
    setPreclosureLoading(true)
    try {
      const response = await fetch('/api/v1/loans/simulations/preclosure', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          account_id: accountId,
          closure_date: closureDate,
          ...penaltyPayload,
        }),
      })
      if (!response.ok) throw new Error('Simulation failed')
      setPreclosureResult(await response.json())
    } catch (err) {
      setError('Could not run foreclosure simulation')
      console.error(err)
    } finally {
      setPreclosureLoading(false)
    }
  }

  const simulateRateChange = async (rateOverride?: number) => {
    setError('')
    setRateChangeLoading(true)
    const rateVal = rateOverride ?? parseFloat(newRate)
    try {
      const response = await fetch('/api/v1/loans/simulations/interest-rate-change', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          account_id: accountId,
          new_interest_rate: rateVal,
          effective_from_date: rateEffectiveDate,
          include_ladder: true,
        }),
      })
      if (!response.ok) throw new Error('Simulation failed')
      const data = (await response.json()) as RateChangeResult
      setRateChangeResult(data)
      if (data.recommended === 'keep_emi' || data.tenure_cut_usually_wins) {
        setPreferredPath('keep_emi')
      }
      if (rateOverride != null) setNewRate(String(rateOverride))
    } catch (err) {
      setError('Could not run rate simulation')
      console.error(err)
    } finally {
      setRateChangeLoading(false)
    }
  }

  const basisLabel =
    penaltyBasis === 'outstanding' ? '% of outstanding' : '% of prepay amount'

  return (
    <div className="space-y-5">
      {/* G4 assumption chips */}
      <div className="flex flex-wrap items-center gap-2">
        <AssumptionChip
          label="Penalty"
          value={`${penaltyRate || '0'}% · ${basisLabel}`}
          onClick={() => setAssumptionsOpen(true)}
        />
        <AssumptionChip
          label="Invest elsewhere"
          value={`${altReturn || '7'}%`}
          onClick={() => setAssumptionsOpen(true)}
        />
        <AssumptionChip
          label="Rate path default"
          value="Keep EMI"
          onClick={() => setPreferredPath('keep_emi')}
        />
        <Popover open={assumptionsOpen} onOpenChange={setAssumptionsOpen}>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground">
              <Settings2 className="h-3.5 w-3.5 mr-1" />
              Assumptions
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80 space-y-3" align="start">
            <h3 className="text-sm font-semibold">Assumptions</h3>
            <div className="space-y-2">
              <Label className="text-xs">Prepay penalty %</Label>
              <Input
                type="number"
                step="0.1"
                value={penaltyRate}
                onChange={(e) => setPenaltyRate(e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">
                Floating retail home loans often 0%. Commercial / NRP may still charge — edit here.
              </p>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Penalty basis</Label>
              <select
                className="w-full border border-border rounded-md h-9 px-2 bg-background text-sm"
                value={penaltyBasis}
                onChange={(e) => setPenaltyBasis(e.target.value as PenaltyBasis)}
              >
                <option value="outstanding">% of outstanding</option>
                <option value="prepayment_amount">% of prepay amount</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Invest-elsewhere return %</Label>
              <Input
                type="number"
                step="0.1"
                value={altReturn}
                onChange={(e) => setAltReturn(e.target.value)}
              />
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="rate-change" className="w-full">
        <TabsList className="grid w-full grid-cols-3 h-auto">
          <TabsTrigger value="rate-change" className="text-xs sm:text-sm py-2">
            <Percent className="h-3.5 w-3.5 mr-1.5 shrink-0" />
            Rate change
          </TabsTrigger>
          <TabsTrigger value="early-payment" className="text-xs sm:text-sm py-2">
            <Calculator className="h-3.5 w-3.5 mr-1.5 shrink-0" />
            Prepay
          </TabsTrigger>
          <TabsTrigger value="preclosure" className="text-xs sm:text-sm py-2">
            <DollarSign className="h-3.5 w-3.5 mr-1.5 shrink-0" />
            Foreclose
          </TabsTrigger>
        </TabsList>

        {/* -------- Rate change -------- */}
        <TabsContent value="rate-change" className="space-y-4 mt-4">
          <Card className="border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">If the rate moves</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="newRate">New rate %</Label>
                  <Input
                    id="newRate"
                    type="number"
                    step="0.01"
                    value={newRate}
                    onChange={(e) => setNewRate(e.target.value)}
                    placeholder={`Now ${currentRate}%`}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="rateEffectiveDate">From</Label>
                  <Input
                    id="rateEffectiveDate"
                    type="date"
                    value={rateEffectiveDate}
                    onChange={(e) => setRateEffectiveDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  variant={preferredPath === 'keep_emi' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setPreferredPath('keep_emi')}
                >
                  Keep EMI · cut tenure
                </Button>
                <Button
                  variant={preferredPath === 'keep_duration' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setPreferredPath('keep_duration')}
                >
                  Cut EMI · keep tenure
                </Button>
                <Button
                  onClick={() => simulateRateChange()}
                  disabled={rateChangeLoading || !newRate}
                  className="sm:ml-auto"
                >
                  {rateChangeLoading ? 'Calculating…' : 'Compare both'}
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Banks often auto-cut EMI. Tap <span className="font-medium text-foreground">Keep EMI</span> to lock
                the tenure cut instead.
              </p>

              {rateChangeResult?.is_interest_only && (
                <Alert>
                  <AlertDescription className="text-sm">
                    {rateChangeResult.note ||
                      'This loan has no EMI. Rate change does not invent one.'}
                  </AlertDescription>
                </Alert>
              )}

              {rateChangeResult && !rateChangeResult.is_interest_only && rateChangeResult.keep_emi && (
                <div className="space-y-3">
                  {rateChangeResult.negative_amortisation_risk && (
                    <Alert variant="destructive">
                      <AlertDescription className="text-sm">
                        At {rateChangeResult.new_rate.toFixed(2)}%, EMI may not cover interest — tenure can
                        stretch without end. Raise EMI or prepay principal.
                      </AlertDescription>
                    </Alert>
                  )}

                  <FrozenScrollTable className="text-sm">
                    <thead>
                      <tr>
                        <FrozenTh stickyLabel className="text-xs">
                          Path
                        </FrozenTh>
                        <FrozenTh align="right" className="text-xs">
                          Δ months
                        </FrozenTh>
                        <FrozenTh align="right" className="text-xs">
                          Δ EMI
                        </FrozenTh>
                        <FrozenTh align="right" className="text-xs">
                          Interest impact
                        </FrozenTh>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        className={cn(
                          preferredPath === 'keep_emi' && 'bg-emerald-500/10 dark:bg-emerald-400/10',
                        )}
                      >
                        <FrozenTd stickyLabel className="font-medium">
                          Keep EMI
                          {rateChangeResult.tenure_cut_usually_wins && (
                            <span className="ml-1.5 text-[10px] text-emerald-700 dark:text-emerald-300">
                              usually wins
                            </span>
                          )}
                        </FrozenTd>
                        <FrozenTd align="right" className="tabular-nums">
                          {rateChangeResult.keep_emi.negative_amortisation
                            ? '∞'
                            : fmtDeltaMonths(rateChangeResult.keep_emi.delta_months)}
                        </FrozenTd>
                        <FrozenTd align="right" className="tabular-nums text-muted-foreground">
                          0
                        </FrozenTd>
                        <FrozenTd align="right">
                          <Signed
                            value={rateChangeResult.keep_emi.interest_delta}
                            currency={currency}
                            locale={locale}
                            invert
                          />
                        </FrozenTd>
                      </tr>
                      <tr
                        className={cn(
                          preferredPath === 'keep_duration' && 'bg-sky-500/10 dark:bg-sky-400/10',
                        )}
                      >
                        <FrozenTd stickyLabel className="font-medium">
                          Keep tenure
                        </FrozenTd>
                        <FrozenTd align="right" className="tabular-nums text-muted-foreground">
                          0
                        </FrozenTd>
                        <FrozenTd align="right">
                          <Signed
                            value={rateChangeResult.keep_duration?.delta_emi}
                            currency={currency}
                            locale={locale}
                            invert
                          />
                        </FrozenTd>
                        <FrozenTd align="right">
                          <Signed
                            value={rateChangeResult.keep_duration?.interest_delta}
                            currency={currency}
                            locale={locale}
                            invert
                          />
                        </FrozenTd>
                      </tr>
                    </tbody>
                  </FrozenScrollTable>

                  <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                    <div>
                      Rate{' '}
                      <span className="text-foreground font-medium">
                        {rateChangeResult.current_rate.toFixed(2)}% → {rateChangeResult.new_rate.toFixed(2)}%
                      </span>
                    </div>
                    <div className="text-right">
                      EMI now{' '}
                      <span className="text-foreground font-medium">
                        {formatCurrency(rateChangeResult.current_emi || currentEmi, currency, locale)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* -------- Prepay -------- */}
        <TabsContent value="early-payment" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Lump / part prepay</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="earlyPaymentAmount">Amount</Label>
                  <Input
                    id="earlyPaymentAmount"
                    type="number"
                    value={earlyPaymentAmount}
                    onChange={(e) => setEarlyPaymentAmount(e.target.value)}
                    placeholder="Prepay amount"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="earlyPaymentDate">Date</Label>
                  <Input
                    id="earlyPaymentDate"
                    type="date"
                    value={earlyPaymentDate}
                    onChange={(e) => setEarlyPaymentDate(e.target.value)}
                  />
                </div>
              </div>

              <Button
                onClick={simulateEarlyPayment}
                disabled={earlyPaymentLoading || !earlyPaymentAmount}
              >
                {earlyPaymentLoading ? 'Calculating…' : 'Compare EMI vs tenure'}
              </Button>

              {earlyPaymentResult?.is_interest_only && (
                <Alert>
                  <AlertDescription className="text-sm">
                    {earlyPaymentResult.note ||
                      'Interest-only loan — principal drops; no EMI reinvented.'}
                  </AlertDescription>
                </Alert>
              )}

              {earlyPaymentResult && !earlyPaymentResult.is_interest_only && (
                <div className="space-y-3">
                  <FrozenScrollTable className="text-sm">
                    <thead>
                      <tr>
                        <FrozenTh stickyLabel className="text-xs">
                          After prepay
                        </FrozenTh>
                        <FrozenTh align="right" className="text-xs">
                          Δ months
                        </FrozenTh>
                        <FrozenTh align="right" className="text-xs">
                          Δ EMI
                        </FrozenTh>
                        <FrozenTh align="right" className="text-xs">
                          Interest saved
                        </FrozenTh>
                        <FrozenTh align="right" className="text-xs">
                          Net (after penalty)
                        </FrozenTh>
                      </tr>
                    </thead>
                    <tbody>
                      {earlyPaymentResult.reduce_tenure && (
                        <tr
                          className={cn(
                            earlyPaymentResult.recommended === 'reduce_tenure' &&
                              'bg-emerald-500/10 dark:bg-emerald-400/10',
                          )}
                        >
                          <FrozenTd stickyLabel className="font-medium">
                            Keep EMI
                            {earlyPaymentResult.reduce_tenure.usually_wins && (
                              <span className="ml-1.5 text-[10px] text-emerald-700 dark:text-emerald-300">
                                usually wins
                              </span>
                            )}
                          </FrozenTd>
                          <FrozenTd align="right" className="tabular-nums">
                            {fmtDeltaMonths(-(earlyPaymentResult.reduce_tenure.months_saved || 0))}
                          </FrozenTd>
                          <FrozenTd align="right" className="tabular-nums text-muted-foreground">
                            0
                          </FrozenTd>
                          <FrozenTd align="right">
                            <Signed
                              value={earlyPaymentResult.reduce_tenure.interest_saved}
                              currency={currency}
                              locale={locale}
                            />
                          </FrozenTd>
                          <FrozenTd align="right">
                            <Signed
                              value={earlyPaymentResult.reduce_tenure.total_savings}
                              currency={currency}
                              locale={locale}
                            />
                          </FrozenTd>
                        </tr>
                      )}
                      {earlyPaymentResult.reduce_emi && (
                        <tr
                          className={cn(
                            earlyPaymentResult.recommended === 'reduce_emi' &&
                              'bg-sky-500/10 dark:bg-sky-400/10',
                          )}
                        >
                          <FrozenTd stickyLabel className="font-medium">
                            Reset EMI
                            {earlyPaymentResult.reduce_emi.bank_default_trap && (
                              <span className="ml-1.5 text-[10px] text-amber-700 dark:text-amber-300">
                                bank default
                              </span>
                            )}
                          </FrozenTd>
                          <FrozenTd align="right" className="tabular-nums text-muted-foreground">
                            0
                          </FrozenTd>
                          <FrozenTd align="right">
                            <Signed
                              value={-(earlyPaymentResult.reduce_emi.emi_reduction || 0)}
                              currency={currency}
                              locale={locale}
                              invert
                            />
                          </FrozenTd>
                          <FrozenTd align="right">
                            <Signed
                              value={earlyPaymentResult.reduce_emi.interest_saved}
                              currency={currency}
                              locale={locale}
                            />
                          </FrozenTd>
                          <FrozenTd align="right">
                            <Signed
                              value={earlyPaymentResult.reduce_emi.total_savings}
                              currency={currency}
                              locale={locale}
                            />
                          </FrozenTd>
                        </tr>
                      )}
                    </tbody>
                  </FrozenScrollTable>

                  {earlyPaymentResult.penalty && earlyPaymentResult.penalty.amount > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Penalty{' '}
                      <span className="text-foreground font-medium">
                        {formatCurrency(earlyPaymentResult.penalty.amount, currency, locale)}
                      </span>{' '}
                      ({earlyPaymentResult.penalty.rate}%{' '}
                      {earlyPaymentResult.penalty.basis === 'outstanding'
                        ? 'of outstanding'
                        : 'of prepay'})
                    </p>
                  )}

                  {earlyPaymentResult.invest_elsewhere && (
                    <FrozenScrollTable className="text-sm">
                      <thead>
                        <tr>
                          <FrozenTh stickyLabel className="text-xs">
                            Use of cash
                          </FrozenTh>
                          <FrozenTh align="right" className="text-xs">
                            Benefit
                          </FrozenTh>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          className={cn(
                            earlyPaymentResult.invest_elsewhere.prefer_prepay &&
                              'bg-emerald-500/10 dark:bg-emerald-400/10',
                          )}
                        >
                          <FrozenTd stickyLabel>Prepay loan (net)</FrozenTd>
                          <FrozenTd align="right">
                            <Signed
                              value={earlyPaymentResult.invest_elsewhere.prepay_net_benefit}
                              currency={currency}
                              locale={locale}
                            />
                          </FrozenTd>
                        </tr>
                        <tr
                          className={cn(
                            !earlyPaymentResult.invest_elsewhere.prefer_prepay &&
                              'bg-sky-500/10 dark:bg-sky-400/10',
                          )}
                        >
                          <FrozenTd stickyLabel>
                            Invest elsewhere @ {earlyPaymentResult.invest_elsewhere.alt_return_pct}%
                          </FrozenTd>
                          <FrozenTd align="right">
                            <Signed
                              value={earlyPaymentResult.invest_elsewhere.alt_earnings}
                              currency={currency}
                              locale={locale}
                            />
                          </FrozenTd>
                        </tr>
                      </tbody>
                    </FrozenScrollTable>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* -------- Foreclose -------- */}
        <TabsContent value="preclosure" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Foreclose / full payoff</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5 max-w-xs">
                <Label htmlFor="closureDate">Closure date</Label>
                <Input
                  id="closureDate"
                  type="date"
                  value={closureDate}
                  onChange={(e) => setClosureDate(e.target.value)}
                />
              </div>

              <Button onClick={simulatePreclosure} disabled={preclosureLoading}>
                {preclosureLoading ? 'Calculating…' : 'Show payoff'}
              </Button>

              {preclosureResult && (
                <div className="space-y-3">
                  <FrozenScrollTable className="text-sm">
                    <thead>
                      <tr>
                        <FrozenTh stickyLabel className="text-xs">
                          Line
                        </FrozenTh>
                        <FrozenTh align="right" className="text-xs">
                          Amount
                        </FrozenTh>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <FrozenTd stickyLabel>Outstanding</FrozenTd>
                        <FrozenTd align="right" className="tabular-nums">
                          {formatCurrency(preclosureResult.outstanding_principal, currency, locale)}
                        </FrozenTd>
                      </tr>
                      <tr>
                        <FrozenTd stickyLabel>Accrued interest</FrozenTd>
                        <FrozenTd align="right" className="tabular-nums">
                          {formatCurrency(preclosureResult.accrued_interest, currency, locale)}
                        </FrozenTd>
                      </tr>
                      <tr>
                        <FrozenTd stickyLabel>
                          Penalty ({preclosureResult.prepayment_penalty_rate}%
                          {preclosureResult.prepayment_penalty_basis
                            ? ` · ${preclosureResult.prepayment_penalty_basis === 'outstanding' ? 'of OS' : 'of prepay'}`
                            : ''}
                          )
                        </FrozenTd>
                        <FrozenTd
                          align="right"
                          className={cn(
                            'tabular-nums',
                            preclosureResult.prepayment_penalty > 0
                              ? 'text-rose-700 dark:text-rose-300'
                              : 'text-muted-foreground',
                          )}
                        >
                          {formatCurrency(preclosureResult.prepayment_penalty, currency, locale)}
                        </FrozenTd>
                      </tr>
                      <tr className="bg-muted/50 font-medium">
                        <FrozenTd stickyLabel className="bg-muted/50">
                          Total payoff
                        </FrozenTd>
                        <FrozenTd align="right" className="tabular-nums">
                          {formatCurrency(preclosureResult.total_payoff_amount, currency, locale)}
                        </FrozenTd>
                      </tr>
                      <tr>
                        <FrozenTd stickyLabel>Interest you avoid</FrozenTd>
                        <FrozenTd align="right">
                          <Signed
                            value={preclosureResult.interest_saved}
                            currency={currency}
                            locale={locale}
                          />
                        </FrozenTd>
                      </tr>
                      <tr>
                        <FrozenTd stickyLabel>Net after penalty</FrozenTd>
                        <FrozenTd align="right">
                          <Signed
                            value={preclosureResult.net_savings}
                            currency={currency}
                            locale={locale}
                          />
                        </FrozenTd>
                      </tr>
                    </tbody>
                  </FrozenScrollTable>
                  <p className="text-xs text-muted-foreground">
                    Paid so far {formatCurrency(preclosureResult.paid_to_date.total, currency, locale)} ·{' '}
                    {preclosureResult.remaining_emis} EMIs left
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* -------- Ready-reference (default bottom) -------- */}
      <Card className="border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Rate ready-reference</CardTitle>
          <p className="text-xs text-muted-foreground">
            ±0.25% · ±0.5% · ±1% — Δ months if EMI kept · Δ EMI if tenure kept · net interest impact
          </p>
        </CardHeader>
        <CardContent>
          {ladderQuery.isLoading && (
            <div className="py-6 text-center text-sm text-muted-foreground">Loading steps…</div>
          )}
          {ladderQuery.data?.is_interest_only && (
            <p className="text-sm text-muted-foreground py-4">
              No EMI on this loan — ready-reference steps do not invent one.
            </p>
          )}
          {!ladderQuery.data?.is_interest_only && ladderRows.length > 0 && (
            <FrozenScrollTable maxHeight="20rem" className="text-sm">
              <thead>
                <tr>
                  <FrozenTh stickyLabel className="text-xs">
                    Rate step
                  </FrozenTh>
                  <FrozenTh align="right" className="text-xs">
                    New rate
                  </FrozenTh>
                  <FrozenTh align="right" className="text-xs">
                    Δ months (keep EMI)
                  </FrozenTh>
                  <FrozenTh align="right" className="text-xs">
                    Δ EMI (keep tenure)
                  </FrozenTh>
                  <FrozenTh align="right" className="text-xs">
                    Net interest
                  </FrozenTh>
                </tr>
              </thead>
              <tbody>
                {ladderRows.map((row) => (
                  <tr
                    key={row.rate_step}
                    className="hover:bg-muted/40 cursor-pointer"
                    onClick={() => simulateRateChange(row.new_rate)}
                  >
                    <FrozenTd stickyLabel className="tabular-nums font-medium">
                      {row.rate_step > 0 ? '+' : ''}
                      {row.rate_step.toFixed(2)}%
                    </FrozenTd>
                    <FrozenTd align="right" className="tabular-nums">
                      {row.new_rate.toFixed(2)}%
                    </FrozenTd>
                    <FrozenTd align="right" className="tabular-nums">
                      {row.negative_amortisation ? (
                        <span className="text-rose-700 dark:text-rose-300">∞ risk</span>
                      ) : (
                        fmtDeltaMonths(row.delta_months_if_emi_kept)
                      )}
                    </FrozenTd>
                    <FrozenTd align="right">
                      <Signed
                        value={row.delta_emi_if_duration_kept}
                        currency={currency}
                        locale={locale}
                        invert
                      />
                    </FrozenTd>
                    <FrozenTd align="right">
                      <Signed
                        value={row.net_extra_interest}
                        currency={currency}
                        locale={locale}
                        invert
                      />
                    </FrozenTd>
                  </tr>
                ))}
              </tbody>
            </FrozenScrollTable>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
