import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, Plus, TrendingUp, Download } from 'lucide-react'
import { 
  useEPFAccount, 
  useEPFContributions, 
  useEPFProjection, 
  useEPFWithdrawals,
  useEPFWithdrawalRules 
} from '@/hooks/use-epf'
import { AddContributionDialog } from '@/components/epf/AddContributionDialog'
import { WithdrawalDialog } from '@/components/epf/WithdrawalDialog'
import { formatCurrency, formatDate } from '@/lib/utils'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function EPFDetailPage() {
  const { accountId } = useParams<{ accountId: string }>()
  const navigate = useNavigate()
  const [contributionDialogOpen, setContributionDialogOpen] = useState(false)
  const [withdrawalDialogOpen, setWithdrawalDialogOpen] = useState(false)

  const { data: account, isLoading: accountLoading } = useEPFAccount(accountId!)
  const { data: contributions, isLoading: contributionsLoading } = useEPFContributions(accountId!)
  const { data: projection } = useEPFProjection(accountId!)
  const { data: withdrawals } = useEPFWithdrawals(accountId!)
  const { data: rules } = useEPFWithdrawalRules(accountId!)

  if (accountLoading || contributionsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!account) {
    return <div>Account not found</div>
  }

  const totalBalance = parseFloat(account.employee_balance) + parseFloat(account.employer_balance)

  // Prepare chart data
  const chartData = contributions?.slice().reverse().map((c) => ({
    month: formatDate(c.contribution_month, 'MMM yyyy'),
    employee: parseFloat(c.employee_balance),
    employer: parseFloat(c.employer_balance),
    total: parseFloat(c.employee_balance) + parseFloat(c.employer_balance),
  })) || []

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/retirement/epf')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{account.account_name}</h1>
          {account.uan_number && (
            <p className="text-muted-foreground">UAN: {account.uan_number}</p>
          )}
        </div>
      </div>

      {/* Balance Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Total Balance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(totalBalance, 'INR')}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Employee Share</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(parseFloat(account.employee_balance), 'INR')}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Employer Share</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(parseFloat(account.employer_balance), 'INR')}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="contributions" className="space-y-4">
        <TabsList>
          <TabsTrigger value="contributions">Contributions</TabsTrigger>
          <TabsTrigger value="projection">Retirement Projection</TabsTrigger>
          <TabsTrigger value="withdrawals">Withdrawals</TabsTrigger>
        </TabsList>

        <TabsContent value="contributions" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Contribution History</CardTitle>
                  <CardDescription>Monthly EPF contributions over time</CardDescription>
                </div>
                <Button onClick={() => setContributionDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Contribution
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {chartData.length > 0 && (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="employee" stroke="#8884d8" name="Employee" />
                    <Line type="monotone" dataKey="employer" stroke="#82ca9d" name="Employer" />
                    <Line type="monotone" dataKey="total" stroke="#ffc658" name="Total" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              )}

              <div className="mt-6 space-y-2">
                {contributions?.map((contribution) => (
                  <div key={contribution.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <div className="font-medium">{formatDate(contribution.contribution_month, 'MMMM yyyy')}</div>
                      <div className="text-sm text-muted-foreground">
                        Employee: {formatCurrency(parseFloat(contribution.employee_contribution), 'INR')} | 
                        Employer: {formatCurrency(parseFloat(contribution.employer_contribution), 'INR')}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold">
                        {formatCurrency(
                          parseFloat(contribution.employee_contribution) + parseFloat(contribution.employer_contribution),
                          'INR'
                        )}
                      </div>
                      {parseFloat(contribution.interest_earned) > 0 && (
                        <div className="text-sm text-green-600">
                          +{formatCurrency(parseFloat(contribution.interest_earned), 'INR')} interest
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="projection" className="space-y-4">
          {projection ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Retirement Projection</CardTitle>
                  <CardDescription>
                    Based on current balance and monthly contributions at {account.current_interest_rate}% interest
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <div className="text-sm text-muted-foreground">Current Age</div>
                      <div className="text-2xl font-bold">{projection.current_age} years</div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm text-muted-foreground">Years to Retirement</div>
                      <div className="text-2xl font-bold">{projection.years_to_retirement} years</div>
                    </div>
                  </div>

                  <div className="pt-4 border-t space-y-3">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Current Balance</span>
                      <span className="font-semibold">{formatCurrency(parseFloat(projection.current_total_balance), 'INR')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Future Contributions</span>
                      <span className="font-semibold">{formatCurrency(parseFloat(projection.projected_contributions), 'INR')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Interest Earned</span>
                      <span className="font-semibold text-green-600">{formatCurrency(parseFloat(projection.projected_interest), 'INR')}</span>
                    </div>
                    <div className="flex justify-between pt-3 border-t">
                      <span className="font-bold">Projected Balance at Retirement</span>
                      <span className="text-2xl font-bold text-primary">
                        {formatCurrency(parseFloat(projection.projected_total_at_retirement), 'INR')}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="py-16 text-center">
                <TrendingUp className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">
                  Set your date of birth to see retirement projection
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="withdrawals" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Withdrawal Rules & History</CardTitle>
                  <CardDescription>EPF withdrawal eligibility and records</CardDescription>
                </div>
                <Button onClick={() => setWithdrawalDialogOpen(true)}>
                  <Download className="h-4 w-4 mr-2" />
                  Record Withdrawal
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {rules && (
                <div className="p-4 bg-muted rounded-lg space-y-2">
                  <div className="font-semibold">Eligibility (After {rules.years_of_service} years of service)</div>
                  <ul className="space-y-1 text-sm">
                    {rules.notes.map((note, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-600">✓</span>
                        <span>{note}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="space-y-2">
                {withdrawals && withdrawals.length > 0 ? (
                  withdrawals.map((withdrawal) => (
                    <div key={withdrawal.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <div className="font-medium">{formatDate(withdrawal.withdrawal_date)}</div>
                        <div className="text-sm text-muted-foreground">
                          {withdrawal.withdrawal_type} {withdrawal.form_type && `(Form ${withdrawal.form_type})`}
                        </div>
                        {withdrawal.purpose && (
                          <div className="text-sm text-muted-foreground">{withdrawal.purpose}</div>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="font-bold">
                          {formatCurrency(
                            parseFloat(withdrawal.employee_amount) + parseFloat(withdrawal.employer_amount),
                            'INR'
                          )}
                        </div>
                        {withdrawal.is_taxable && withdrawal.tax_amount && (
                          <div className="text-sm text-red-600">
                            Tax: {formatCurrency(parseFloat(withdrawal.tax_amount), 'INR')}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No withdrawals recorded
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <AddContributionDialog 
        accountId={accountId!} 
        open={contributionDialogOpen} 
        onOpenChange={setContributionDialogOpen} 
      />
      
      <WithdrawalDialog 
        accountId={accountId!} 
        open={withdrawalDialogOpen} 
        onOpenChange={setWithdrawalDialogOpen} 
      />
    </div>
  )
}
