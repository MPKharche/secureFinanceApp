import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Download, RefreshCw, DollarSign } from 'lucide-react';
import { formatCurrency } from '@/lib/format';
import { accounts } from '@/lib/api';
import { useAuth } from '@/contexts/auth-context';
import { useDisplayLocale } from '@/hooks/use-display-locale';
import { LoanScheduleTable } from './LoanScheduleTable';
import { PrepaymentDialog } from './PrepaymentDialog';
import { LoanAnalyticsCharts } from './LoanAnalyticsCharts';
import { LoanSimulations } from '@/components/loans/LoanSimulations';
import { CombinedLoanSimulator } from '@/components/loans/CombinedLoanSimulator';
import { useMemo, useState } from 'react';

interface LoanOverview {
  progress_percent: number;
  emis_paid: number;
  emis_remaining: number;
  principal_paid: string;
  principal_remaining: string;
  interest_paid: string;
  interest_remaining: string;
  total_prepayments: string;
  principal_progress_percent?: number;
  interest_progress_percent?: number;
}

/** Completion % of paid / (paid + remaining); 0 when total is 0. */
function completionPercent(paid: number, remaining: number, fromApi?: number): number {
  if (typeof fromApi === 'number' && Number.isFinite(fromApi)) {
    return fromApi;
  }
  const safePaid = Number.isFinite(paid) ? Math.max(paid, 0) : 0;
  const safeRemaining = Number.isFinite(remaining) ? Math.max(remaining, 0) : 0;
  const total = safePaid + safeRemaining;
  if (!total) return 0;
  return (safePaid / total) * 100;
}

function detectNrpOrCommercial(account: {
  name?: string;
  display_name?: string | null;
  notes?: string | null;
  loan_kind?: string | null;
} | undefined): boolean {
  if (!account) return false;
  const blob = `${account.display_name || ''} ${account.name || ''} ${account.notes || ''} ${account.loan_kind || ''}`.toLowerCase();
  return ['nrp', 'commercial', 'tbpun', 'unit 114', 'u114', 'godrej emerald'].some((m) =>
    blob.includes(m),
  );
}

async function fetchLoanOverview(accountId: string): Promise<LoanOverview> {
  const response = await fetch(`/api/v1/loans/${accountId}/overview`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
    },
  });
  if (!response.ok) throw new Error('Failed to fetch loan overview');
  return response.json();
}

async function exportScheduleCSV(accountId: string) {
  const response = await fetch(`/api/v1/loans/${accountId}/schedule/export`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
    },
  });
  if (!response.ok) throw new Error('Failed to export schedule');

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `loan_${accountId}_schedule.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export function LoanDetailPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const [prepaymentDialogOpen, setPrepaymentDialogOpen] = useState(false);
  const { user } = useAuth();
  const locale = useDisplayLocale();
  const userCurrency = user?.preferences?.currency_display ?? 'USD';

  const { data: overview, isLoading, error, refetch } = useQuery({
    queryKey: ['loan-overview', accountId],
    queryFn: () => fetchLoanOverview(accountId!),
    enabled: !!accountId,
  });

  const { data: account } = useQuery({
    queryKey: ['accounts', accountId],
    queryFn: () => accounts.get(accountId!),
    enabled: !!accountId,
  });

  const currency = account?.currency ?? userCurrency;
  const isNrp = useMemo(() => detectNrpOrCommercial(account), [account]);
  const currentRate = Number(account?.interest_rate ?? 0);
  const currentEmi = Number(account?.emi_amount ?? 0);

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex justify-center text-muted-foreground">Loading loan details...</div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="container mx-auto py-8">
        <Alert variant="destructive">
          <AlertDescription>Failed to load loan details</AlertDescription>
        </Alert>
      </div>
    );
  }

  const handleExport = async () => {
    try {
      await exportScheduleCSV(accountId!);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const principalPaid = parseFloat(overview.principal_paid);
  const principalRemaining = parseFloat(overview.principal_remaining);
  const interestPaid = parseFloat(overview.interest_paid);
  const interestRemaining = Math.max(parseFloat(overview.interest_remaining) || 0, 0);

  return (
    <div className="container mx-auto py-6 sm:py-8 space-y-5 px-3 sm:px-4">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            {account?.display_name || account?.name || 'Loan'}
          </h1>
          {currentRate > 0 && (
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              {currentRate.toFixed(2)}%
              {currentEmi > 0 && (
                <>
                  {' '}
                  · EMI {formatCurrency(currentEmi, currency, locale)}
                </>
              )}
              {currentEmi <= 0 && <> · No EMI</>}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-1.5" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-1.5" />
            Export
          </Button>
          <Button size="sm" onClick={() => setPrepaymentDialogOpen(true)}>
            <DollarSign className="h-4 w-4 mr-1.5" />
            Prepay
          </Button>
        </div>
      </div>

      {/* Overview — high-contrast KPI strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3">
        <Card className="border-border bg-card">
          <CardHeader className="pb-1 pt-3 px-3 sm:px-4">
            <CardTitle className="text-[11px] sm:text-xs font-medium text-muted-foreground">
              Progress
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 sm:px-4 pb-3">
            <div className="text-xl sm:text-2xl font-bold tabular-nums text-foreground">
              {overview.progress_percent.toFixed(1)}%
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-0.5">
              {overview.emis_paid} of {overview.emis_paid + overview.emis_remaining} EMIs
            </p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="pb-1 pt-3 px-3 sm:px-4">
            <CardTitle className="text-[11px] sm:text-xs font-medium text-muted-foreground">
              Principal (
              {completionPercent(
                principalPaid,
                principalRemaining,
                overview.principal_progress_percent,
              ).toFixed(1)}
              %)
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 sm:px-4 pb-3">
            <div className="text-xl sm:text-2xl font-bold tabular-nums text-emerald-700 dark:text-emerald-300">
              {formatCurrency(principalPaid, currency, locale)}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-0.5">
              Left {formatCurrency(principalRemaining, currency, locale)}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="pb-1 pt-3 px-3 sm:px-4">
            <CardTitle className="text-[11px] sm:text-xs font-medium text-muted-foreground">
              Interest (
              {completionPercent(
                interestPaid,
                interestRemaining,
                overview.interest_progress_percent,
              ).toFixed(1)}
              %)
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 sm:px-4 pb-3">
            <div className="text-xl sm:text-2xl font-bold tabular-nums text-foreground">
              {formatCurrency(interestPaid, currency, locale)}
            </div>
            <p className="text-[10px] sm:text-xs text-rose-700/80 dark:text-rose-300/80 mt-0.5">
              Left {formatCurrency(interestRemaining, currency, locale)}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="pb-1 pt-3 px-3 sm:px-4">
            <CardTitle className="text-[11px] sm:text-xs font-medium text-muted-foreground">
              Prepayments
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 sm:px-4 pb-3">
            <div className="text-xl sm:text-2xl font-bold tabular-nums text-sky-700 dark:text-sky-300">
              {formatCurrency(parseFloat(overview.total_prepayments), currency, locale)}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-0.5">Total prepaid</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="schedule" className="w-full">
        <TabsList className="h-auto flex flex-wrap w-full sm:w-auto gap-0.5">
          <TabsTrigger value="schedule" className="text-xs sm:text-sm">
            Schedule
          </TabsTrigger>
          <TabsTrigger value="analysis" className="text-xs sm:text-sm">
            Analysis
          </TabsTrigger>
          <TabsTrigger value="simulations" className="text-xs sm:text-sm">
            Simulations
          </TabsTrigger>
          <TabsTrigger value="combined" className="text-xs sm:text-sm">
            Combined plan
          </TabsTrigger>
        </TabsList>

        <TabsContent value="schedule" className="mt-4">
          <LoanScheduleTable accountId={accountId!} currency={currency} locale={locale} />
        </TabsContent>

        <TabsContent value="analysis" className="mt-4">
          <LoanAnalyticsCharts accountId={accountId!} currency={currency} locale={locale} />
        </TabsContent>

        <TabsContent value="simulations" className="mt-4">
          <LoanSimulations
            accountId={accountId!}
            currentEmi={currentEmi}
            outstandingBalance={principalRemaining}
            currentRate={currentRate}
            remainingMonths={overview.emis_remaining}
            currency={currency}
            locale={locale}
            isNrpOrCommercial={isNrp}
          />
        </TabsContent>

        <TabsContent value="combined" className="mt-4">
          <CombinedLoanSimulator
            accountId={accountId!}
            currentRate={currentRate}
            currency={currency}
            locale={locale}
          />
        </TabsContent>
      </Tabs>

      <PrepaymentDialog
        accountId={accountId!}
        open={prepaymentDialogOpen}
        onOpenChange={setPrepaymentDialogOpen}
        onSuccess={() => refetch()}
        isNrpOrCommercial={isNrp}
      />
    </div>
  );
}

export default LoanDetailPage
