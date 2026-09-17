import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { 
  TrendingUp, 
  TrendingDown, 
  Calendar, 
  DollarSign, 
  AlertCircle,
  Target,
  BarChart3,
  Clock
} from 'lucide-react'
import { format } from 'date-fns'

interface DashboardSummary {
  total_monthly_emi: number
  total_outstanding: number
  principal_paid_ytd: number
  interest_paid_ytd: number
  active_loan_count: number
  debt_free_date: string | null
  months_to_debt_free: number
}

interface UpcomingPayment {
  schedule_entry_id: string
  loan_id: string
  loan_name: string
  due_date: string
  emi_amount: number
  principal_component: number
  interest_component: number
  payment_status: string
  days_until_due: number
}

interface DebtHealth {
  dti: number | null
  foir: number | null
  status: 'good' | 'moderate' | 'high' | 'unknown'
  breakdown: {
    monthly_income: number
    total_emi: number
    other_obligations: number
    total_obligations: number
  }
  thresholds: {
    dti_good: number
    dti_high: number
    foir_good: number
    foir_high: number
  }
  recommendations: string[]
}

interface TimelineEntry {
  month: string
  month_label: string
  total_emi: number
  total_principal: number
  total_interest: number
  payment_count: number
}

export default function LoanDashboardPage() {
  const [monthlyIncome, setMonthlyIncome] = useState<string>('')
  const [showHealthCalc, setShowHealthCalc] = useState(false)

  // Fetch dashboard summary
  const { data: summary, isLoading: summaryLoading } = useQuery<DashboardSummary>({
    queryKey: ['loan-dashboard', 'summary'],
    queryFn: async () => {
      const response = await fetch('/api/v1/loans/dashboard/summary', {
        credentials: 'include',
      })
      if (!response.ok) throw new Error('Failed to fetch summary')
      return response.json()
    },
  })

  // Fetch upcoming payments
  const { data: upcomingPayments, isLoading: paymentsLoading } = useQuery<UpcomingPayment[]>({
    queryKey: ['loan-dashboard', 'upcoming-payments'],
    queryFn: async () => {
      const response = await fetch('/api/v1/loans/dashboard/upcoming-payments?days=30', {
        credentials: 'include',
      })
      if (!response.ok) throw new Error('Failed to fetch payments')
      return response.json()
    },
  })

  // Fetch timeline
  const { data: timeline, isLoading: timelineLoading } = useQuery<{ timeline: TimelineEntry[] }>({
    queryKey: ['loan-dashboard', 'timeline'],
    queryFn: async () => {
      const response = await fetch('/api/v1/loans/dashboard/timeline?months=12', {
        credentials: 'include',
      })
      if (!response.ok) throw new Error('Failed to fetch timeline')
      return response.json()
    },
  })

  // Calculate debt health
  const { data: debtHealth, refetch: refetchHealth, isFetching: healthFetching } = useQuery<DebtHealth>({
    queryKey: ['loan-dashboard', 'debt-health', monthlyIncome],
    queryFn: async () => {
      const response = await fetch('/api/v1/loans/dashboard/calculate-debt-health', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          monthly_income: parseFloat(monthlyIncome),
          other_obligations: 0,
        }),
      })
      if (!response.ok) throw new Error('Failed to calculate debt health')
      return response.json()
    },
    enabled: false, // Only run when manually triggered
  })

  const handleCalculateHealth = () => {
    if (!monthlyIncome || parseFloat(monthlyIncome) <= 0) {
      toast.error('Please enter a valid monthly income')
      return
    }
    refetchHealth()
    setShowHealthCalc(true)
  }

  const isLoading = summaryLoading || paymentsLoading || timelineLoading

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    )
  }

  const statusConfig = {
    good: { color: 'bg-green-500', label: 'Healthy', icon: TrendingUp },
    moderate: { color: 'bg-yellow-500', label: 'Moderate', icon: AlertCircle },
    high: { color: 'bg-red-500', label: 'High Risk', icon: TrendingDown },
    unknown: { color: 'bg-gray-500', label: 'Unknown', icon: AlertCircle },
  }

  return (
    <div className="space-y-6 pb-16">
      <PageHeader
        section="Loans"
        title="EMI Dashboard"
        description="Track your loan payments, debt health, and payoff timeline"
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Monthly EMI</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <DollarSign className="size-5 text-muted-foreground" />
              <span className="text-2xl font-bold">₹{summary?.total_monthly_emi.toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Outstanding</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Target className="size-5 text-muted-foreground" />
              <span className="text-2xl font-bold">₹{summary?.total_outstanding.toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active Loans</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <BarChart3 className="size-5 text-muted-foreground" />
              <span className="text-2xl font-bold">{summary?.active_loan_count}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Debt Free In</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Clock className="size-5 text-muted-foreground" />
              <span className="text-2xl font-bold">
                {summary?.months_to_debt_free ? `${summary.months_to_debt_free} months` : 'N/A'}
              </span>
            </div>
            {summary?.debt_free_date && (
              <p className="text-xs text-muted-foreground mt-1">
                {format(new Date(summary.debt_free_date), 'MMM yyyy')}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* YTD Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Year-to-Date Progress</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Principal Paid</span>
              <span className="text-sm font-bold text-green-600">₹{summary?.principal_paid_ytd.toLocaleString()}</span>
            </div>
            <Progress value={65} className="h-2" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Interest Paid</span>
              <span className="text-sm font-bold text-orange-600">₹{summary?.interest_paid_ytd.toLocaleString()}</span>
            </div>
            <Progress value={35} className="h-2 [&>div]:bg-orange-500" />
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="upcoming" className="space-y-4">
        <TabsList>
          <TabsTrigger value="upcoming">Upcoming Payments</TabsTrigger>
          <TabsTrigger value="timeline">Payment Timeline</TabsTrigger>
          <TabsTrigger value="health">Debt Health</TabsTrigger>
        </TabsList>

        {/* Upcoming Payments */}
        <TabsContent value="upcoming" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="size-5" />
                Next 30 Days
              </CardTitle>
              <CardDescription>{upcomingPayments?.length || 0} payments due</CardDescription>
            </CardHeader>
            <CardContent>
              {upcomingPayments && upcomingPayments.length > 0 ? (
                <div className="space-y-3">
                  {upcomingPayments.map((payment) => (
                    <div
                      key={payment.schedule_entry_id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium">{payment.loan_name}</span>
                          {payment.days_until_due <= 7 && (
                            <Badge variant="destructive" className="text-xs">
                              Due in {payment.days_until_due} days
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {format(new Date(payment.due_date), 'MMM dd, yyyy')}
                        </p>
                        <div className="flex gap-4 mt-2 text-xs">
                          <span className="text-muted-foreground">
                            Principal: <span className="font-medium">₹{payment.principal_component.toLocaleString()}</span>
                          </span>
                          <span className="text-muted-foreground">
                            Interest: <span className="font-medium">₹{payment.interest_component.toLocaleString()}</span>
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold">₹{payment.emi_amount.toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">No upcoming payments in the next 30 days</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Timeline */}
        <TabsContent value="timeline">
          <Card>
            <CardHeader>
              <CardTitle>12-Month Payment Timeline</CardTitle>
              <CardDescription>Monthly breakdown of EMI payments</CardDescription>
            </CardHeader>
            <CardContent>
              {timeline?.timeline && timeline.timeline.length > 0 ? (
                <div className="space-y-2">
                  {timeline.timeline.map((entry) => (
                    <div key={entry.month} className="flex items-center gap-4 p-3 border rounded-lg">
                      <div className="min-w-[80px]">
                        <span className="text-sm font-medium">{entry.month_label}</span>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Progress value={(entry.total_principal / entry.total_emi) * 100} className="h-2 flex-1" />
                          <span className="text-xs text-muted-foreground whitespace-nowrap">
                            {entry.payment_count} payment{entry.payment_count !== 1 ? 's' : ''}
                          </span>
                        </div>
                        <div className="flex gap-4 text-xs">
                          <span>
                            Principal: <span className="font-medium">₹{entry.total_principal.toLocaleString()}</span>
                          </span>
                          <span>
                            Interest: <span className="font-medium">₹{entry.total_interest.toLocaleString()}</span>
                          </span>
                        </div>
                      </div>
                      <div className="text-right min-w-[100px]">
                        <div className="text-lg font-bold">₹{entry.total_emi.toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">No timeline data available</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Debt Health */}
        <TabsContent value="health" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Calculate Debt Health</CardTitle>
              <CardDescription>
                Check your Debt-to-Income (DTI) and Fixed Obligation to Income Ratio (FOIR)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="text-sm font-medium">Monthly Gross Income (₹)</label>
                  <input
                    type="number"
                    className="w-full mt-1 px-3 py-2 border rounded-md"
                    placeholder="e.g., 100000"
                    value={monthlyIncome}
                    onChange={(e) => setMonthlyIncome(e.target.value)}
                  />
                </div>
                <div className="flex items-end">
                  <Button onClick={handleCalculateHealth} disabled={healthFetching}>
                    {healthFetching ? 'Calculating...' : 'Calculate'}
                  </Button>
                </div>
              </div>

              {showHealthCalc && debtHealth && (
                <div className="space-y-4 mt-6">
                  {/* Status Badge */}
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-full ${statusConfig[debtHealth.status].color}`}>
                      {(() => {
                        const Icon = statusConfig[debtHealth.status].icon
                        return <Icon className="size-6 text-white" />
                      })()}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold">{statusConfig[debtHealth.status].label}</h3>
                      <p className="text-sm text-muted-foreground">Your debt health status</p>
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 border rounded-lg">
                      <div className="text-sm text-muted-foreground mb-1">Debt-to-Income (DTI)</div>
                      <div className="text-3xl font-bold">
                        {debtHealth.dti ? `${(debtHealth.dti * 100).toFixed(1)}%` : 'N/A'}
                      </div>
                      <Progress
                        value={debtHealth.dti ? debtHealth.dti * 100 : 0}
                        className="mt-2"
                      />
                      <p className="text-xs text-muted-foreground mt-2">
                        Target: Below {(debtHealth.thresholds.dti_good * 100).toFixed(0)}%
                      </p>
                    </div>

                    <div className="p-4 border rounded-lg">
                      <div className="text-sm text-muted-foreground mb-1">FOIR</div>
                      <div className="text-3xl font-bold">
                        {debtHealth.foir ? `${(debtHealth.foir * 100).toFixed(1)}%` : 'N/A'}
                      </div>
                      <Progress
                        value={debtHealth.foir ? debtHealth.foir * 100 : 0}
                        className="mt-2"
                      />
                      <p className="text-xs text-muted-foreground mt-2">
                        Target: Below {(debtHealth.thresholds.foir_good * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>

                  {/* Recommendations */}
                  {debtHealth.recommendations.length > 0 && (
                    <Alert>
                      <AlertCircle className="size-4" />
                      <AlertTitle>Recommendations</AlertTitle>
                      <AlertDescription>
                        <ul className="list-disc list-inside space-y-1 mt-2">
                          {debtHealth.recommendations.map((rec, idx) => (
                            <li key={idx} className="text-sm">{rec}</li>
                          ))}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
