import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { tax } from '@/lib/api'
import { toast } from 'sonner'
import { Save } from 'lucide-react'
import type { TaxIncomeSource } from '@/types'

interface TaxSettingsIncomeProps {
  incomeSource: TaxIncomeSource | null | undefined
  financialYear: string
}

export function TaxSettingsIncome({ incomeSource, financialYear }: TaxSettingsIncomeProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    salary_annual: incomeSource?.salary_annual || 0,
    basic_salary: incomeSource?.basic_salary || null,
    hra_received: incomeSource?.hra_received || null,
    special_allowance: incomeSource?.special_allowance || null,
    rental_income: incomeSource?.rental_income || 0,
    interest_income: incomeSource?.interest_income || 0,
    dividend_income: incomeSource?.dividend_income || 0,
    capital_gains_short_term: incomeSource?.capital_gains_short_term || 0,
    capital_gains_long_term: incomeSource?.capital_gains_long_term || 0,
    business_income: incomeSource?.business_income || 0,
    other_income: incomeSource?.other_income || 0,
  })

  const [isDirty, setIsDirty] = useState(false)

  useEffect(() => {
    if (incomeSource) {
      setFormData({
        salary_annual: incomeSource.salary_annual,
        basic_salary: incomeSource.basic_salary,
        hra_received: incomeSource.hra_received,
        special_allowance: incomeSource.special_allowance,
        rental_income: incomeSource.rental_income,
        interest_income: incomeSource.interest_income,
        dividend_income: incomeSource.dividend_income,
        capital_gains_short_term: incomeSource.capital_gains_short_term,
        capital_gains_long_term: incomeSource.capital_gains_long_term,
        business_income: incomeSource.business_income,
        other_income: incomeSource.other_income,
      })
      setIsDirty(false)
    }
  }, [incomeSource])

  const saveMutation = useMutation({
    mutationFn: () => {
      if (incomeSource) {
        return tax.incomeSource.update(financialYear, { ...formData, financial_year: financialYear })
      } else {
        return tax.incomeSource.create({ ...formData, financial_year: financialYear })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tax', 'income', financialYear] })
      queryClient.invalidateQueries({ queryKey: ['tax', 'projection', financialYear] })
      toast.success(t('tax.incomeSaved', 'Income details saved'))
      setIsDirty(false)
    },
    onError: () => {
      toast.error(t('common.error', 'An error occurred'))
    },
  })

  const handleChange = (field: keyof typeof formData, value: number | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setIsDirty(true)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          {t('tax.incomeSettings', 'Income Settings')}
          {isDirty && (
            <Button
              size="sm"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
            >
              <Save className="h-4 w-4 mr-2" />
              {t('common.save', 'Save')}
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <Label htmlFor="salary_annual">{t('tax.salaryAnnual', 'Annual Salary')}</Label>
              <Input
                id="salary_annual"
                type="number"
                value={formData.salary_annual}
                onChange={(e) => handleChange('salary_annual', Number(e.target.value))}
                className="mt-2"
              />
            </div>

            <div className="pt-4 border-t">
              <p className="text-sm font-medium mb-3">{t('tax.salaryBreakdown', 'Salary Breakdown (for HRA)')}</p>
              <div className="space-y-3">
                <div>
                  <Label htmlFor="basic_salary">{t('tax.basicSalary', 'Basic Salary')}</Label>
                  <Input
                    id="basic_salary"
                    type="number"
                    value={formData.basic_salary || ''}
                    onChange={(e) => handleChange('basic_salary', e.target.value ? Number(e.target.value) : null)}
                    className="mt-2"
                    placeholder="Optional"
                  />
                </div>

                <div>
                  <Label htmlFor="hra_received">{t('tax.hraReceived', 'HRA Received')}</Label>
                  <Input
                    id="hra_received"
                    type="number"
                    value={formData.hra_received || ''}
                    onChange={(e) => handleChange('hra_received', e.target.value ? Number(e.target.value) : null)}
                    className="mt-2"
                    placeholder="Optional"
                  />
                </div>

                <div>
                  <Label htmlFor="special_allowance">{t('tax.specialAllowance', 'Special Allowance')}</Label>
                  <Input
                    id="special_allowance"
                    type="number"
                    value={formData.special_allowance || ''}
                    onChange={(e) => handleChange('special_allowance', e.target.value ? Number(e.target.value) : null)}
                    className="mt-2"
                    placeholder="Optional"
                  />
                </div>
              </div>
            </div>

            <div>
              <Label htmlFor="rental_income">{t('tax.rentalIncome', 'Rental Income')}</Label>
              <Input
                id="rental_income"
                type="number"
                value={formData.rental_income}
                onChange={(e) => handleChange('rental_income', Number(e.target.value))}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="interest_income">{t('tax.interestIncome', 'Interest Income')}</Label>
              <Input
                id="interest_income"
                type="number"
                value={formData.interest_income}
                onChange={(e) => handleChange('interest_income', Number(e.target.value))}
                className="mt-2"
              />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <Label htmlFor="dividend_income">{t('tax.dividendIncome', 'Dividend Income')}</Label>
              <Input
                id="dividend_income"
                type="number"
                value={formData.dividend_income}
                onChange={(e) => handleChange('dividend_income', Number(e.target.value))}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="capital_gains_short_term">{t('tax.capitalGainsShortTerm', 'Short-term Capital Gains')}</Label>
              <Input
                id="capital_gains_short_term"
                type="number"
                value={formData.capital_gains_short_term}
                onChange={(e) => handleChange('capital_gains_short_term', Number(e.target.value))}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="capital_gains_long_term">{t('tax.capitalGainsLongTerm', 'Long-term Capital Gains')}</Label>
              <Input
                id="capital_gains_long_term"
                type="number"
                value={formData.capital_gains_long_term}
                onChange={(e) => handleChange('capital_gains_long_term', Number(e.target.value))}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="business_income">{t('tax.businessIncome', 'Business Income')}</Label>
              <Input
                id="business_income"
                type="number"
                value={formData.business_income}
                onChange={(e) => handleChange('business_income', Number(e.target.value))}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="other_income">{t('tax.otherIncome', 'Other Income')}</Label>
              <Input
                id="other_income"
                type="number"
                value={formData.other_income}
                onChange={(e) => handleChange('other_income', Number(e.target.value))}
                className="mt-2"
              />
            </div>
          </div>
        </div>

        {!isDirty && (
          <div className="mt-6 flex justify-end">
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
            >
              <Save className="h-4 w-4 mr-2" />
              {t('common.save', 'Save')}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
