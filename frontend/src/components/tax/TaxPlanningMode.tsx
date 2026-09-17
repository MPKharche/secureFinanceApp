import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { useMutation } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { formatCurrency } from '@/lib/format'
import { tax } from '@/lib/api'
import { Loader2, ArrowRight } from 'lucide-react'
import type { TaxIncomeSource, TaxDeduction, WhatIfScenarioResponse } from '@/types'

interface TaxPlanningModeProps {
  baseIncome: TaxIncomeSource | null | undefined
  baseDeductions: TaxDeduction | null | undefined
  financialYear: string
}

export function TaxPlanningMode({
  baseIncome,
  baseDeductions,
  financialYear,
}: TaxPlanningModeProps) {
  const { t } = useTranslation()
  const locale = useDisplayLocale()

  // Local state for sliders
  const [salaryAnnual, setSalaryAnnual] = useState(baseIncome?.salary_annual || 0)
  const [rentalIncome, setRentalIncome] = useState(baseIncome?.rental_income || 0)
  const [interestIncome, setInterestIncome] = useState(baseIncome?.interest_income || 0)
  const [epfEmployee, setEpfEmployee] = useState(baseDeductions?.epf_employee || 0)
  const [ppf, setPpf] = useState(baseDeductions?.ppf || 0)
  const [elss, setElss] = useState(baseDeductions?.elss || 0)
  const [npsAdditional, setNpsAdditional] = useState(baseDeductions?.nps_additional || 0)
  const [healthInsuranceSelf, setHealthInsuranceSelf] = useState(baseDeductions?.health_insurance_self || 0)
  const [homeLoanInterest, setHomeLoanInterest] = useState(baseDeductions?.home_loan_interest || 0)

  const [result, setResult] = useState<WhatIfScenarioResponse | null>(null)

  const whatIfMutation = useMutation({
    mutationFn: () => tax.whatIf({
      financial_year: financialYear,
      income: {
        salary_annual: salaryAnnual,
        rental_income: rentalIncome,
        interest_income: interestIncome,
        dividend_income: baseIncome?.dividend_income || 0,
        capital_gains_short_term: baseIncome?.capital_gains_short_term || 0,
        capital_gains_long_term: baseIncome?.capital_gains_long_term || 0,
        business_income: baseIncome?.business_income || 0,
        other_income: baseIncome?.other_income || 0,
      },
      deductions: {
        epf_employee: epfEmployee,
        ppf,
        elss,
        nps_additional: npsAdditional,
        health_insurance_self: healthInsuranceSelf,
        home_loan_interest: homeLoanInterest,
        health_insurance_parents: baseDeductions?.health_insurance_parents || 0,
        parents_are_senior_citizens: baseDeductions?.parents_are_senior_citizens || false,
        preventive_checkup: baseDeductions?.preventive_checkup || 0,
        education_loan_interest: baseDeductions?.education_loan_interest || 0,
        donations_100_percent: baseDeductions?.donations_100_percent || 0,
        donations_50_percent: baseDeductions?.donations_50_percent || 0,
        savings_interest_claimed: baseDeductions?.savings_interest_claimed || 0,
        property_is_self_occupied: baseDeductions?.property_is_self_occupied ?? true,
        rent_paid_annual: baseDeductions?.rent_paid_annual || 0,
        city: baseDeductions?.city || null,
        lic_premium: baseDeductions?.lic_premium || 0,
        nsc: baseDeductions?.nsc || 0,
        tuition_fees: baseDeductions?.tuition_fees || 0,
        principal_repayment_home_loan: baseDeductions?.principal_repayment_home_loan || 0,
        other_80c: baseDeductions?.other_80c || 0,
      },
    }),
    onSuccess: (data) => {
      setResult(data)
    },
  })

  // Debounced recalculation
  useEffect(() => {
    const timer = setTimeout(() => {
      whatIfMutation.mutate()
    }, 500)
    return () => clearTimeout(timer)
  }, [salaryAnnual, rentalIncome, interestIncome, epfEmployee, ppf, elss, npsAdditional, healthInsuranceSelf, homeLoanInterest])

  const total80C = epfEmployee + ppf + elss
  const is80CMaxed = total80C >= 150000

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: Input Sliders */}
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('tax.adjustIncome', 'Adjust Income')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="salary">{t('tax.salaryAnnual', 'Annual Salary')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="salary"
                  type="number"
                  value={salaryAnnual}
                  onChange={(e) => setSalaryAnnual(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(salaryAnnual, 'INR', locale)}
                </span>
              </div>
            </div>

            <div>
              <Label htmlFor="rental">{t('tax.rentalIncome', 'Rental Income')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="rental"
                  type="number"
                  value={rentalIncome}
                  onChange={(e) => setRentalIncome(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(rentalIncome, 'INR', locale)}
                </span>
              </div>
            </div>

            <div>
              <Label htmlFor="interest">{t('tax.interestIncome', 'Interest Income')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="interest"
                  type="number"
                  value={interestIncome}
                  onChange={(e) => setInterestIncome(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(interestIncome, 'INR', locale)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              {t('tax.adjustDeductions', 'Adjust Deductions')}
              {is80CMaxed && (
                <span className="ml-2 text-xs font-normal text-amber-600">
                  {t('tax.80CMaxed', '80C Limit Reached (₹1.5L)')}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="epf">{t('tax.epf', 'EPF Contribution')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="epf"
                  type="number"
                  value={epfEmployee}
                  onChange={(e) => setEpfEmployee(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(epfEmployee, 'INR', locale)}
                </span>
              </div>
            </div>

            <div>
              <Label htmlFor="ppf">{t('tax.ppf', 'PPF')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="ppf"
                  type="number"
                  value={ppf}
                  onChange={(e) => setPpf(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(ppf, 'INR', locale)}
                </span>
              </div>
            </div>

            <div>
              <Label htmlFor="elss">{t('tax.elss', 'ELSS')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="elss"
                  type="number"
                  value={elss}
                  onChange={(e) => setElss(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(elss, 'INR', locale)}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t">
              <Label htmlFor="nps">{t('tax.npsAdditional', 'NPS Additional (80CCD1B)')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="nps"
                  type="number"
                  value={npsAdditional}
                  onChange={(e) => setNpsAdditional(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(npsAdditional, 'INR', locale)}
                </span>
              </div>
            </div>

            <div>
              <Label htmlFor="health">{t('tax.healthInsuranceSelf', 'Health Insurance (Self)')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="health"
                  type="number"
                  value={healthInsuranceSelf}
                  onChange={(e) => setHealthInsuranceSelf(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(healthInsuranceSelf, 'INR', locale)}
                </span>
              </div>
            </div>

            <div>
              <Label htmlFor="homeLoan">{t('tax.homeLoanInterest', 'Home Loan Interest')}</Label>
              <div className="flex items-center gap-3 mt-2">
                <Input
                  id="homeLoan"
                  type="number"
                  value={homeLoanInterest}
                  onChange={(e) => setHomeLoanInterest(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatCurrency(homeLoanInterest, 'INR', locale)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right: Comparison Results */}
      <div className="space-y-6">
        {whatIfMutation.isPending && !result && (
          <Card>
            <CardContent className="py-12 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">{t('tax.calculating', 'Calculating...')}</p>
            </CardContent>
          </Card>
        )}

        {result && (
          <>
            <Card className={`border-2 ${result.recommended_regime === 'old' ? 'border-emerald-500' : 'border-border'}`}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {t('tax.oldRegime', 'Old Regime')}
                  {result.recommended_regime === 'old' && (
                    <span className="text-xs font-normal px-2 py-1 rounded-full bg-emerald-500 text-white">
                      {t('tax.recommended', 'Recommended')}
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">{t('tax.grossIncome', 'Gross Income')}</span>
                  <span className="font-semibold">{formatCurrency(result.old_regime.gross_income, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">{t('tax.deductions', 'Deductions')}</span>
                  <span className="font-semibold text-emerald-600">
                    −{formatCurrency(result.old_regime.total_deductions || 0, 'INR', locale)}
                  </span>
                </div>
                <div className="flex justify-between pt-2 border-t">
                  <span className="text-sm text-muted-foreground">{t('tax.taxableIncome', 'Taxable Income')}</span>
                  <span className="font-semibold">{formatCurrency(result.old_regime.taxable_income, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between text-lg pt-2">
                  <span className="font-bold">{t('tax.totalTax', 'Total Tax')}</span>
                  <span className="font-bold text-rose-600">{formatCurrency(result.old_regime.total_tax, 'INR', locale)}</span>
                </div>
              </CardContent>
            </Card>

            <div className="flex items-center justify-center">
              <div className="text-center">
                <ArrowRight className="h-6 w-6 text-muted-foreground mx-auto mb-2 rotate-90 lg:rotate-0" />
                <p className="text-xs text-muted-foreground">{t('tax.difference', 'Difference')}</p>
                <p className="text-xl font-bold text-emerald-600">
                  {formatCurrency(result.savings_with_recommendation, 'INR', locale)}
                </p>
              </div>
            </div>

            <Card className={`border-2 ${result.recommended_regime === 'new' ? 'border-emerald-500' : 'border-border'}`}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {t('tax.newRegime', 'New Regime')}
                  {result.recommended_regime === 'new' && (
                    <span className="text-xs font-normal px-2 py-1 rounded-full bg-emerald-500 text-white">
                      {t('tax.recommended', 'Recommended')}
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">{t('tax.grossIncome', 'Gross Income')}</span>
                  <span className="font-semibold">{formatCurrency(result.new_regime.gross_income, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">{t('tax.stdDeduction', 'Std. Deduction')}</span>
                  <span className="font-semibold text-emerald-600">−{formatCurrency(75000, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between pt-2 border-t">
                  <span className="text-sm text-muted-foreground">{t('tax.taxableIncome', 'Taxable Income')}</span>
                  <span className="font-semibold">{formatCurrency(result.new_regime.taxable_income, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between text-lg pt-2">
                  <span className="font-bold">{t('tax.totalTax', 'Total Tax')}</span>
                  <span className="font-bold text-rose-600">{formatCurrency(result.new_regime.total_tax, 'INR', locale)}</span>
                </div>
              </CardContent>
            </Card>

            {whatIfMutation.isPending && (
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground py-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('tax.recalculating', 'Recalculating...')}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
