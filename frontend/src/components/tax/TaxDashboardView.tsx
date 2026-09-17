import { useTranslation } from 'react-i18next'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatCurrency } from '@/lib/format'
import { ArrowRight, TrendingDown, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react'
import type { TaxProjection, TaxPayment, TaxIncomeSource, TaxDeduction } from '@/types'

interface TaxDashboardViewProps {
  projection: TaxProjection | null | undefined
  payment: TaxPayment | undefined
  incomeSource: TaxIncomeSource | null | undefined
  deductions: TaxDeduction | null | undefined
  financialYear: string
}

export function TaxDashboardView({
  projection,
  payment,
  incomeSource,
  deductions,
}: TaxDashboardViewProps) {
  const { t } = useTranslation()
  const locale = useDisplayLocale()

  if (!projection) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground mb-4">
            {t('tax.noProjection', 'No tax projection available. Add your income and deductions to get started.')}
          </p>
        </CardContent>
      </Card>
    )
  }

  const recommendedRegime = projection.recommended_regime
  const oldRegime = projection.old_regime
  const newRegime = projection.new_regime
  const savings = projection.savings_with_recommendation

  const taxDue = projection.tax_due_or_refund
  const isDue = taxDue > 0
  const isRefund = taxDue < 0

  return (
    <div className="space-y-6">
      {/* Regime Comparison Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t('tax.regimeComparison', 'Tax Regime Comparison')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Old Regime */}
            <div className={`rounded-lg border-2 p-4 ${recommendedRegime === 'old' ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/20' : 'border-border'}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold">{t('tax.oldRegime', 'Old Regime')}</h3>
                {recommendedRegime === 'old' && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-500 text-white text-xs font-bold">
                    <CheckCircle2 className="h-3 w-3" />
                    {t('tax.recommended', 'Recommended')}
                  </span>
                )}
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t('tax.grossIncome', 'Gross Income')}</span>
                  <span className="font-medium">{formatCurrency(oldRegime.gross_income, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t('tax.deductions', 'Deductions')}</span>
                  <span className="font-medium text-emerald-600">−{formatCurrency(oldRegime.total_deductions || 0, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between text-sm pt-2 border-t">
                  <span className="text-muted-foreground">{t('tax.taxableIncome', 'Taxable Income')}</span>
                  <span className="font-semibold">{formatCurrency(oldRegime.taxable_income, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between text-lg pt-2">
                  <span className="font-semibold">{t('tax.totalTax', 'Total Tax')}</span>
                  <span className="font-bold text-rose-600">{formatCurrency(oldRegime.total_tax, 'INR', locale)}</span>
                </div>
              </div>
            </div>

            {/* Arrow */}
            <div className="hidden md:flex items-center justify-center">
              <div className="text-center">
                <ArrowRight className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">{t('tax.youSave', 'You Save')}</p>
                <p className="text-2xl font-bold text-emerald-600">{formatCurrency(savings, 'INR', locale)}</p>
              </div>
            </div>

            {/* New Regime */}
            <div className={`rounded-lg border-2 p-4 ${recommendedRegime === 'new' ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/20' : 'border-border'}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold">{t('tax.newRegime', 'New Regime')}</h3>
                {recommendedRegime === 'new' && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-500 text-white text-xs font-bold">
                    <CheckCircle2 className="h-3 w-3" />
                    {t('tax.recommended', 'Recommended')}
                  </span>
                )}
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t('tax.grossIncome', 'Gross Income')}</span>
                  <span className="font-medium">{formatCurrency(newRegime.gross_income, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t('tax.stdDeduction', 'Std. Deduction')}</span>
                  <span className="font-medium text-emerald-600">−{formatCurrency(75000, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between text-sm pt-2 border-t">
                  <span className="text-muted-foreground">{t('tax.taxableIncome', 'Taxable Income')}</span>
                  <span className="font-semibold">{formatCurrency(newRegime.taxable_income, 'INR', locale)}</span>
                </div>
                <div className="flex justify-between text-lg pt-2">
                  <span className="font-semibold">{t('tax.totalTax', 'Total Tax')}</span>
                  <span className="font-bold text-rose-600">{formatCurrency(newRegime.total_tax, 'INR', locale)}</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs font-medium text-muted-foreground mb-1">{t('tax.effectiveTaxRate', 'Effective Tax Rate')}</p>
            <p className="text-2xl font-bold">
              {((recommendedRegime === 'old' ? oldRegime.total_tax : newRegime.total_tax) / oldRegime.gross_income * 100).toFixed(1)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-xs font-medium text-muted-foreground mb-1">{t('tax.totalDeductions', 'Total Deductions')}</p>
            <p className="text-2xl font-bold text-emerald-600">
              {formatCurrency(recommendedRegime === 'old' ? (oldRegime.total_deductions || 0) : 75000, 'INR', locale)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-xs font-medium text-muted-foreground mb-1">{t('tax.tdsPaid', 'TDS Paid')}</p>
            <p className="text-2xl font-bold">{formatCurrency(payment?.tds_deducted || 0, 'INR', locale)}</p>
          </CardContent>
        </Card>

        <Card className={isDue ? 'border-rose-500' : isRefund ? 'border-emerald-500' : ''}>
          <CardContent className="pt-6">
            <p className="text-xs font-medium text-muted-foreground mb-1">
              {isDue ? t('tax.taxDue', 'Tax Due') : isRefund ? t('tax.refundExpected', 'Refund Expected') : t('tax.balance', 'Balance')}
            </p>
            <p className={`text-2xl font-bold ${isDue ? 'text-rose-600' : isRefund ? 'text-emerald-600' : 'text-foreground'}`}>
              {formatCurrency(Math.abs(taxDue), 'INR', locale)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Deduction Breakdown */}
      {recommendedRegime === 'old' && deductions && (
        <Card>
          <CardHeader>
            <CardTitle>{t('tax.deductionBreakdown', 'Deduction Breakdown (Old Regime)')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {deductions.epf_employee + deductions.ppf + deductions.elss + deductions.lic_premium + deductions.nsc + deductions.tuition_fees + deductions.principal_repayment_home_loan + deductions.other_80c > 0 && (
                <div className="p-4 rounded-lg bg-muted/50">
                  <h4 className="text-sm font-semibold mb-3">{t('tax.section80C', 'Section 80C (Max ₹1.5L)')}</h4>
                  <div className="space-y-2">
                    {deductions.epf_employee > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">{t('tax.epf', 'EPF')}</span>
                        <span className="font-medium">{formatCurrency(deductions.epf_employee, 'INR', locale)}</span>
                      </div>
                    )}
                    {deductions.ppf > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">{t('tax.ppf', 'PPF')}</span>
                        <span className="font-medium">{formatCurrency(deductions.ppf, 'INR', locale)}</span>
                      </div>
                    )}
                    {deductions.elss > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">{t('tax.elss', 'ELSS')}</span>
                        <span className="font-medium">{formatCurrency(deductions.elss, 'INR', locale)}</span>
                      </div>
                    )}
                    {/* Add more 80C items as needed */}
                  </div>
                </div>
              )}

              {deductions.nps_additional > 0 && (
                <div className="p-4 rounded-lg bg-muted/50">
                  <h4 className="text-sm font-semibold mb-3">{t('tax.section80CCD1B', 'Section 80CCD(1B) NPS')}</h4>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t('tax.npsAdditional', 'NPS Additional (Max ₹50K)')}</span>
                    <span className="font-medium">{formatCurrency(deductions.nps_additional, 'INR', locale)}</span>
                  </div>
                </div>
              )}

              {(deductions.health_insurance_self > 0 || deductions.health_insurance_parents > 0) && (
                <div className="p-4 rounded-lg bg-muted/50">
                  <h4 className="text-sm font-semibold mb-3">{t('tax.section80D', 'Section 80D Health Insurance')}</h4>
                  <div className="space-y-2">
                    {deductions.health_insurance_self > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">{t('tax.healthSelf', 'Self & Family')}</span>
                        <span className="font-medium">{formatCurrency(deductions.health_insurance_self, 'INR', locale)}</span>
                      </div>
                    )}
                    {deductions.health_insurance_parents > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">{t('tax.healthParents', 'Parents')}</span>
                        <span className="font-medium">{formatCurrency(deductions.health_insurance_parents, 'INR', locale)}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {deductions.home_loan_interest > 0 && (
                <div className="p-4 rounded-lg bg-muted/50">
                  <h4 className="text-sm font-semibold mb-3">{t('tax.section24B', 'Section 24(b) Home Loan Interest')}</h4>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t('tax.homeLoanInterest', 'Interest Paid')}</span>
                    <span className="font-medium">{formatCurrency(deductions.home_loan_interest, 'INR', locale)}</span>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Payment Tracker */}
      {payment && (
        <Card>
          <CardHeader>
            <CardTitle>{t('tax.paymentTracker', 'Payment Tracker')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                <div>
                  <p className="text-sm font-medium">{t('tax.tdsDeducted', 'TDS Deducted')}</p>
                  <p className="text-xs text-muted-foreground">{t('tax.tdsDesc', 'Tax deducted at source by employer')}</p>
                </div>
                <p className="text-xl font-bold">{formatCurrency(payment.tds_deducted, 'INR', locale)}</p>
              </div>

              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                <div>
                  <p className="text-sm font-medium">{t('tax.advanceTax', 'Advance Tax Paid')}</p>
                  <p className="text-xs text-muted-foreground">{t('tax.advanceTaxDesc', 'Quarterly advance tax payments')}</p>
                </div>
                <p className="text-xl font-bold">{formatCurrency(payment.advance_tax_paid, 'INR', locale)}</p>
              </div>

              <div className={`flex items-center justify-between p-4 rounded-lg ${isDue ? 'bg-rose-50 dark:bg-rose-950/20 border-2 border-rose-500' : isRefund ? 'bg-emerald-50 dark:bg-emerald-950/20 border-2 border-emerald-500' : 'bg-muted/50'}`}>
                <div>
                  <p className="text-sm font-semibold">
                    {isDue ? t('tax.remainingDue', 'Remaining Tax Due') : isRefund ? t('tax.refundAmount', 'Refund Amount') : t('tax.settled', 'Settled')}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {isDue ? t('tax.payBefore', 'Pay before July 31, 2027') : isRefund ? t('tax.refundDesc', 'Expected after filing returns') : t('tax.noAction', 'No action needed')}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-bold ${isDue ? 'text-rose-600' : isRefund ? 'text-emerald-600' : 'text-foreground'}`}>
                    {formatCurrency(Math.abs(taxDue), 'INR', locale)}
                  </p>
                  {isDue && (
                    <div className="flex items-center gap-1 text-xs text-rose-600 mt-1">
                      <TrendingUp className="h-3 w-3" />
                      {t('tax.actionRequired', 'Action Required')}
                    </div>
                  )}
                  {isRefund && (
                    <div className="flex items-center gap-1 text-xs text-emerald-600 mt-1">
                      <TrendingDown className="h-3 w-3" />
                      {t('tax.refundDue', 'Refund Due')}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
