import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { formatCurrency } from '@/lib/format'
import { tax } from '@/lib/api'
import { toast } from 'sonner'
import { CheckCircle2, Sparkles, AlertCircle, Loader2 } from 'lucide-react'

interface TaxAutoDetectReviewProps {
  financialYear: string
  onClose: () => void
  onSave: () => void
}

export function TaxAutoDetectReview({ financialYear, onClose, onSave }: TaxAutoDetectReviewProps) {
  const { t } = useTranslation()
  const locale = useDisplayLocale()
  const queryClient = useQueryClient()

  const [adjustedSalary, setAdjustedSalary] = useState<number | null>(null)
  const [adjustedInterest, setAdjustedInterest] = useState<number | null>(null)

  const { data: detectedData, isLoading } = useQuery({
    queryKey: ['tax', 'auto-detect', financialYear],
    queryFn: () => tax.autoDetect(financialYear),
  })

  const { data: currentIncome } = useQuery({
    queryKey: ['tax', 'income', financialYear],
    queryFn: () => tax.incomeSource.get(financialYear),
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      const salary = adjustedSalary ?? detectedData?.detected_salary ?? 0
      const interest = adjustedInterest ?? detectedData?.detected_interest ?? 0

      if (currentIncome) {
        return tax.incomeSource.update(financialYear, {
          salary_annual: salary,
          interest_income: interest,
        })
      } else {
        return tax.incomeSource.create({
          financial_year: financialYear,
          salary_annual: salary,
          interest_income: interest,
          rental_income: 0,
          dividend_income: 0,
          capital_gains_short_term: 0,
          capital_gains_long_term: 0,
          business_income: 0,
          other_income: 0,
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tax'] })
      toast.success(t('tax.autoDetectSaved', 'Auto-detected income saved'))
      onSave()
    },
    onError: () => {
      toast.error(t('common.error', 'An error occurred'))
    },
  })

  if (isLoading) {
    return (
      <Dialog open onOpenChange={onClose}>
        <DialogContent>
          <div className="py-12 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">{t('tax.detecting', 'Detecting income from transactions...')}</p>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  const detectedSalary = detectedData?.detected_salary || 0
  const detectedInterest = detectedData?.detected_interest || 0
  const hasDetections = detectedSalary > 0 || detectedInterest > 0

  if (!hasDetections) {
    return (
      <Dialog open onOpenChange={onClose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-500" />
              {t('tax.noDetections', 'No Income Detected')}
            </DialogTitle>
          </DialogHeader>
          <div className="py-6">
            <p className="text-muted-foreground">
              {t('tax.noDetectionsDesc', 'We couldn\'t detect any salary or interest income from your transactions. Please enter your income details manually in the Settings tab.')}
            </p>
          </div>
          <DialogFooter>
            <Button onClick={onClose}>{t('common.close', 'Close')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-emerald-500" />
            {t('tax.reviewDetectedIncome', 'Review Detected Income')}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <p className="text-sm text-muted-foreground">
            {t('tax.reviewDesc', 'We\'ve analyzed your transactions and detected the following income. Review and adjust if needed before saving.')}
          </p>

          {detectedSalary > 0 && (
            <Card className="border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      <h3 className="text-sm font-semibold">{t('tax.salaryDetected', 'Salary Detected')}</h3>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">
                      {t('tax.salaryDetectedDesc', 'Based on credit transactions matching salary patterns')}
                    </p>
                    {currentIncome && currentIncome.salary_annual > 0 && (
                      <p className="text-xs text-amber-600 mb-2">
                        {t('tax.currentValue', 'Current value')}: {formatCurrency(currentIncome.salary_annual, 'INR', locale)}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-emerald-600">
                      {formatCurrency(adjustedSalary ?? detectedSalary, 'INR', locale)}
                    </p>
                    <button
                      className="text-xs text-blue-600 hover:underline mt-1"
                      onClick={() => {
                        const newValue = prompt(
                          t('tax.adjustSalary', 'Adjust detected salary'),
                          String(adjustedSalary ?? detectedSalary)
                        )
                        if (newValue) setAdjustedSalary(Number(newValue))
                      }}
                    >
                      {t('tax.adjust', 'Adjust')}
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {detectedInterest > 0 && (
            <Card className="border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      <h3 className="text-sm font-semibold">{t('tax.interestDetected', 'Interest Income Detected')}</h3>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">
                      {t('tax.interestDetectedDesc', 'Based on credit transactions from bank interest')}
                    </p>
                    {currentIncome && currentIncome.interest_income > 0 && (
                      <p className="text-xs text-amber-600 mb-2">
                        {t('tax.currentValue', 'Current value')}: {formatCurrency(currentIncome.interest_income, 'INR', locale)}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-emerald-600">
                      {formatCurrency(adjustedInterest ?? detectedInterest, 'INR', locale)}
                    </p>
                    <button
                      className="text-xs text-blue-600 hover:underline mt-1"
                      onClick={() => {
                        const newValue = prompt(
                          t('tax.adjustInterest', 'Adjust detected interest'),
                          String(adjustedInterest ?? detectedInterest)
                        )
                        if (newValue) setAdjustedInterest(Number(newValue))
                      }}
                    >
                      {t('tax.adjust', 'Adjust')}
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800">
            <p className="text-xs text-blue-700 dark:text-blue-300">
              <strong>{t('tax.note', 'Note')}:</strong> {t('tax.autoDetectNote', 'Auto-detection uses transaction patterns and may not be 100% accurate. Please verify these amounts against your Form 16, bank statements, or other official documents before filing your tax return.')}
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t('common.cancel', 'Cancel')}
          </Button>
          <Button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {t('tax.saveDetected', 'Save Detected Income')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
