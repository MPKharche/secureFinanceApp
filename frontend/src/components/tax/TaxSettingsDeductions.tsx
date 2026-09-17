import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { tax } from '@/lib/api'
import { toast } from 'sonner'
import { Save } from 'lucide-react'
import type { TaxDeduction } from '@/types'

interface TaxSettingsDeductionsProps {
  deductions: TaxDeduction | null | undefined
  financialYear: string
}

const METRO_CITIES = ['Mumbai', 'Delhi', 'Kolkata', 'Chennai', 'Bangalore', 'Pune', 'Hyderabad', 'Ahmedabad']

export function TaxSettingsDeductions({ deductions, financialYear }: TaxSettingsDeductionsProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    epf_employee: deductions?.epf_employee || 0,
    ppf: deductions?.ppf || 0,
    elss: deductions?.elss || 0,
    lic_premium: deductions?.lic_premium || 0,
    nsc: deductions?.nsc || 0,
    tuition_fees: deductions?.tuition_fees || 0,
    principal_repayment_home_loan: deductions?.principal_repayment_home_loan || 0,
    other_80c: deductions?.other_80c || 0,
    nps_additional: deductions?.nps_additional || 0,
    health_insurance_self: deductions?.health_insurance_self || 0,
    health_insurance_parents: deductions?.health_insurance_parents || 0,
    parents_are_senior_citizens: deductions?.parents_are_senior_citizens || false,
    preventive_checkup: deductions?.preventive_checkup || 0,
    education_loan_interest: deductions?.education_loan_interest || 0,
    donations_100_percent: deductions?.donations_100_percent || 0,
    donations_50_percent: deductions?.donations_50_percent || 0,
    savings_interest_claimed: deductions?.savings_interest_claimed || 0,
    home_loan_interest: deductions?.home_loan_interest || 0,
    property_is_self_occupied: deductions?.property_is_self_occupied ?? true,
    rent_paid_annual: deductions?.rent_paid_annual || 0,
    city: deductions?.city || null,
  })

  const [isDirty, setIsDirty] = useState(false)

  useEffect(() => {
    if (deductions) {
      setFormData({
        epf_employee: deductions.epf_employee,
        ppf: deductions.ppf,
        elss: deductions.elss,
        lic_premium: deductions.lic_premium,
        nsc: deductions.nsc,
        tuition_fees: deductions.tuition_fees,
        principal_repayment_home_loan: deductions.principal_repayment_home_loan,
        other_80c: deductions.other_80c,
        nps_additional: deductions.nps_additional,
        health_insurance_self: deductions.health_insurance_self,
        health_insurance_parents: deductions.health_insurance_parents,
        parents_are_senior_citizens: deductions.parents_are_senior_citizens,
        preventive_checkup: deductions.preventive_checkup,
        education_loan_interest: deductions.education_loan_interest,
        donations_100_percent: deductions.donations_100_percent,
        donations_50_percent: deductions.donations_50_percent,
        savings_interest_claimed: deductions.savings_interest_claimed,
        home_loan_interest: deductions.home_loan_interest,
        property_is_self_occupied: deductions.property_is_self_occupied,
        rent_paid_annual: deductions.rent_paid_annual,
        city: deductions.city,
      })
      setIsDirty(false)
    }
  }, [deductions])

  const saveMutation = useMutation({
    mutationFn: () => {
      if (deductions) {
        return tax.deductions.update(financialYear, { ...formData, financial_year: financialYear })
      } else {
        return tax.deductions.create({ ...formData, financial_year: financialYear })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tax', 'deductions', financialYear] })
      queryClient.invalidateQueries({ queryKey: ['tax', 'projection', financialYear] })
      toast.success(t('tax.deductionsSaved', 'Deductions saved'))
      setIsDirty(false)
    },
    onError: () => {
      toast.error(t('common.error', 'An error occurred'))
    },
  })

  const handleChange = (field: keyof typeof formData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setIsDirty(true)
  }

  const total80C = formData.epf_employee + formData.ppf + formData.elss + formData.lic_premium + 
                   formData.nsc + formData.tuition_fees + formData.principal_repayment_home_loan + formData.other_80c
  const is80CMaxed = total80C >= 150000

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          {t('tax.deductionSettings', 'Deduction Settings')}
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
        <div className="space-y-6">
          {/* Section 80C */}
          <div className="p-4 rounded-lg bg-muted/50">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold">{t('tax.section80C', 'Section 80C (Max ₹1.5L)')}</h3>
              <span className={`text-sm font-bold ${is80CMaxed ? 'text-amber-600' : 'text-muted-foreground'}`}>
                {t('tax.used', 'Used')}: ₹{(total80C / 100000).toFixed(2)}L / ₹1.5L
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="epf_employee">{t('tax.epf', 'EPF Employee Contribution')}</Label>
                <Input
                  id="epf_employee"
                  type="number"
                  value={formData.epf_employee}
                  onChange={(e) => handleChange('epf_employee', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="ppf">{t('tax.ppf', 'PPF')}</Label>
                <Input
                  id="ppf"
                  type="number"
                  value={formData.ppf}
                  onChange={(e) => handleChange('ppf', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="elss">{t('tax.elss', 'ELSS')}</Label>
                <Input
                  id="elss"
                  type="number"
                  value={formData.elss}
                  onChange={(e) => handleChange('elss', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="lic_premium">{t('tax.licPremium', 'LIC Premium')}</Label>
                <Input
                  id="lic_premium"
                  type="number"
                  value={formData.lic_premium}
                  onChange={(e) => handleChange('lic_premium', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="nsc">{t('tax.nsc', 'NSC')}</Label>
                <Input
                  id="nsc"
                  type="number"
                  value={formData.nsc}
                  onChange={(e) => handleChange('nsc', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="tuition_fees">{t('tax.tuitionFees', 'Tuition Fees')}</Label>
                <Input
                  id="tuition_fees"
                  type="number"
                  value={formData.tuition_fees}
                  onChange={(e) => handleChange('tuition_fees', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="principal_repayment_home_loan">{t('tax.principalRepayment', 'Home Loan Principal')}</Label>
                <Input
                  id="principal_repayment_home_loan"
                  type="number"
                  value={formData.principal_repayment_home_loan}
                  onChange={(e) => handleChange('principal_repayment_home_loan', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="other_80c">{t('tax.other80C', 'Other 80C')}</Label>
                <Input
                  id="other_80c"
                  type="number"
                  value={formData.other_80c}
                  onChange={(e) => handleChange('other_80c', Number(e.target.value))}
                  className="mt-2"
                />
              </div>
            </div>
          </div>

          {/* Section 80CCD(1B) */}
          <div className="p-4 rounded-lg bg-muted/50">
            <h3 className="text-sm font-semibold mb-4">{t('tax.section80CCD1B', 'Section 80CCD(1B) - NPS (Max ₹50K)')}</h3>
            <div>
              <Label htmlFor="nps_additional">{t('tax.npsAdditional', 'NPS Additional Contribution')}</Label>
              <Input
                id="nps_additional"
                type="number"
                value={formData.nps_additional}
                onChange={(e) => handleChange('nps_additional', Number(e.target.value))}
                className="mt-2"
              />
            </div>
          </div>

          {/* Section 80D */}
          <div className="p-4 rounded-lg bg-muted/50">
            <h3 className="text-sm font-semibold mb-4">{t('tax.section80D', 'Section 80D - Health Insurance')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="health_insurance_self">{t('tax.healthInsuranceSelf', 'Self & Family (Max ₹25K)')}</Label>
                <Input
                  id="health_insurance_self"
                  type="number"
                  value={formData.health_insurance_self}
                  onChange={(e) => handleChange('health_insurance_self', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="health_insurance_parents">{t('tax.healthInsuranceParents', 'Parents')}</Label>
                <Input
                  id="health_insurance_parents"
                  type="number"
                  value={formData.health_insurance_parents}
                  onChange={(e) => handleChange('health_insurance_parents', Number(e.target.value))}
                  className="mt-2"
                />
                <div className="flex items-center gap-2 mt-2">
                  <Switch
                    id="parents_senior"
                    checked={formData.parents_are_senior_citizens}
                    onCheckedChange={(checked) => handleChange('parents_are_senior_citizens', checked)}
                  />
                  <Label htmlFor="parents_senior" className="text-xs cursor-pointer">
                    {t('tax.parentsSenior', 'Parents are senior citizens (Max ₹50K)')}
                  </Label>
                </div>
              </div>

              <div>
                <Label htmlFor="preventive_checkup">{t('tax.preventiveCheckup', 'Preventive Checkup (Max ₹5K)')}</Label>
                <Input
                  id="preventive_checkup"
                  type="number"
                  value={formData.preventive_checkup}
                  onChange={(e) => handleChange('preventive_checkup', Number(e.target.value))}
                  className="mt-2"
                />
              </div>
            </div>
          </div>

          {/* Section 24(b) - Home Loan */}
          <div className="p-4 rounded-lg bg-muted/50">
            <h3 className="text-sm font-semibold mb-4">{t('tax.section24B', 'Section 24(b) - Home Loan Interest')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="home_loan_interest">{t('tax.homeLoanInterest', 'Interest Paid')}</Label>
                <Input
                  id="home_loan_interest"
                  type="number"
                  value={formData.home_loan_interest}
                  onChange={(e) => handleChange('home_loan_interest', Number(e.target.value))}
                  className="mt-2"
                />
              </div>
              <div className="flex items-center gap-2 mt-8">
                <Switch
                  id="self_occupied"
                  checked={formData.property_is_self_occupied}
                  onCheckedChange={(checked) => handleChange('property_is_self_occupied', checked)}
                />
                <Label htmlFor="self_occupied" className="text-xs cursor-pointer">
                  {t('tax.selfOccupied', 'Self-occupied (Max ₹2L; Let-out has no limit)')}
                </Label>
              </div>
            </div>
          </div>

          {/* HRA */}
          <div className="p-4 rounded-lg bg-muted/50">
            <h3 className="text-sm font-semibold mb-4">{t('tax.hraExemption', 'HRA Exemption')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="rent_paid_annual">{t('tax.rentPaidAnnual', 'Annual Rent Paid')}</Label>
                <Input
                  id="rent_paid_annual"
                  type="number"
                  value={formData.rent_paid_annual}
                  onChange={(e) => handleChange('rent_paid_annual', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="city">{t('tax.city', 'City')}</Label>
                <Select
                  value={formData.city || ''}
                  onValueChange={(value) => handleChange('city', value || null)}
                >
                  <SelectTrigger className="mt-2">
                    <SelectValue placeholder={t('tax.selectCity', 'Select city')} />
                  </SelectTrigger>
                  <SelectContent>
                    {METRO_CITIES.map((city) => (
                      <SelectItem key={city} value={city}>
                        {city}
                      </SelectItem>
                    ))}
                    <SelectItem value="other">{t('tax.otherCity', 'Other (Non-metro)')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Other Deductions */}
          <div className="p-4 rounded-lg bg-muted/50">
            <h3 className="text-sm font-semibold mb-4">{t('tax.otherDeductions', 'Other Deductions')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="education_loan_interest">{t('tax.educationLoanInterest', 'Education Loan Interest (80E)')}</Label>
                <Input
                  id="education_loan_interest"
                  type="number"
                  value={formData.education_loan_interest}
                  onChange={(e) => handleChange('education_loan_interest', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="donations_100_percent">{t('tax.donations100', 'Donations 100% (80G)')}</Label>
                <Input
                  id="donations_100_percent"
                  type="number"
                  value={formData.donations_100_percent}
                  onChange={(e) => handleChange('donations_100_percent', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="donations_50_percent">{t('tax.donations50', 'Donations 50% (80G)')}</Label>
                <Input
                  id="donations_50_percent"
                  type="number"
                  value={formData.donations_50_percent}
                  onChange={(e) => handleChange('donations_50_percent', Number(e.target.value))}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="savings_interest_claimed">{t('tax.savingsInterest', 'Savings Interest (80TTA/TTB)')}</Label>
                <Input
                  id="savings_interest_claimed"
                  type="number"
                  value={formData.savings_interest_claimed}
                  onChange={(e) => handleChange('savings_interest_claimed', Number(e.target.value))}
                  className="mt-2"
                />
              </div>
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
