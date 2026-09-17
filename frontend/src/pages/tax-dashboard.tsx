import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { tax } from '@/lib/api'
import { PageHeader } from '@/components/page-header'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { TaxDashboardView } from '@/components/tax/TaxDashboardView'
import { TaxPlanningMode } from '@/components/tax/TaxPlanningMode'
import { TaxSettingsIncome } from '@/components/tax/TaxSettingsIncome'
import { TaxSettingsDeductions } from '@/components/tax/TaxSettingsDeductions'
import { TaxAutoDetectReview } from '@/components/tax/TaxAutoDetectReview'
import { Button } from '@/components/ui/button'
import { Calculator, Settings, Sparkles } from 'lucide-react'
import { toast } from 'sonner'

const CURRENT_FY = '2026-27'

export default function TaxDashboardPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'dashboard' | 'planning' | 'settings'>('dashboard')
  const [showAutoDetect, setShowAutoDetect] = useState(false)

  const { data: incomeSource } = useQuery({
    queryKey: ['tax', 'income', CURRENT_FY],
    queryFn: () => tax.incomeSource.get(CURRENT_FY),
  })

  const { data: deductions } = useQuery({
    queryKey: ['tax', 'deductions', CURRENT_FY],
    queryFn: () => tax.deductions.get(CURRENT_FY),
  })

  const { data: projection } = useQuery({
    queryKey: ['tax', 'projection', CURRENT_FY],
    queryFn: () => tax.projection.get(CURRENT_FY),
  })

  const { data: payment } = useQuery({
    queryKey: ['tax', 'payment', CURRENT_FY],
    queryFn: () => tax.payment.get(CURRENT_FY),
  })

  const autoDetectMutation = useMutation({
    mutationFn: () => tax.autoDetect(CURRENT_FY),
    onSuccess: (data) => {
      if (data.detected_salary > 0 || data.detected_interest > 0) {
        setShowAutoDetect(true)
      } else {
        toast.info(t('tax.noDataDetected', 'No income data detected from transactions'))
      }
    },
    onError: () => {
      toast.error(t('common.error', 'An error occurred'))
    },
  })

  const recalculateMutation = useMutation({
    mutationFn: () => tax.projection.calculate(CURRENT_FY),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tax', 'projection', CURRENT_FY] })
      toast.success(t('tax.recalculateSuccess', 'Tax projection recalculated'))
    },
    onError: () => {
      toast.error(t('common.error', 'An error occurred'))
    },
  })

  return (
    <div>
      <PageHeader
        section={t('tax.title', 'Tax Planning')}
        title={t('tax.fyTitle', `FY ${CURRENT_FY}`)}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => autoDetectMutation.mutate()}
              disabled={autoDetectMutation.isPending}
            >
              <Sparkles className="h-4 w-4 mr-2" />
              {t('tax.autoDetect', 'Auto-Detect')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => recalculateMutation.mutate()}
              disabled={recalculateMutation.isPending}
            >
              <Calculator className="h-4 w-4 mr-2" />
              {t('tax.recalculate', 'Recalculate')}
            </Button>
          </div>
        }
      />

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="mb-6">
          <TabsTrigger value="dashboard">
            <Calculator className="h-4 w-4 mr-2" />
            {t('tax.dashboardTab', 'Dashboard')}
          </TabsTrigger>
          <TabsTrigger value="planning">
            <Calculator className="h-4 w-4 mr-2" />
            {t('tax.planningTab', 'What-If Planning')}
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="h-4 w-4 mr-2" />
            {t('tax.settingsTab', 'Settings')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard">
          <TaxDashboardView
            projection={projection}
            payment={payment}
            incomeSource={incomeSource}
            deductions={deductions}
            financialYear={CURRENT_FY}
          />
        </TabsContent>

        <TabsContent value="planning">
          <TaxPlanningMode
            baseIncome={incomeSource}
            baseDeductions={deductions}
            financialYear={CURRENT_FY}
          />
        </TabsContent>

        <TabsContent value="settings">
          <div className="space-y-6">
            <TaxSettingsIncome
              incomeSource={incomeSource}
              financialYear={CURRENT_FY}
            />
            <TaxSettingsDeductions
              deductions={deductions}
              financialYear={CURRENT_FY}
            />
          </div>
        </TabsContent>
      </Tabs>

      {showAutoDetect && (
        <TaxAutoDetectReview
          financialYear={CURRENT_FY}
          onClose={() => setShowAutoDetect(false)}
          onSave={() => {
            setShowAutoDetect(false)
            queryClient.invalidateQueries({ queryKey: ['tax'] })
          }}
        />
      )}
    </div>
  )
}
