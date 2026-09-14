import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Download, RefreshCw, DollarSign } from 'lucide-react';
import { formatCurrency } from '@/lib/format';
import { accounts } from '@/lib/api';
import { useAuth } from '@/contexts/auth-context';
import { useDisplayLocale } from '@/hooks/use-display-locale';
import { clientLoanTitle, formatLoanNextDue } from '@/lib/account-utils';
import { LoanScheduleTable } from './LoanScheduleTable';
import { PrepaymentDialog } from './PrepaymentDialog';
import { LoanAnalyticsCharts } from './LoanAnalyticsCharts';
import { LoanSimulations } from '@/components/loans/LoanSimulations';
import { CombinedLoanSimulator } from '@/components/loans/CombinedLoanSimulator';
import { useMemo, useState } from 'react';
import { cn } from '@/lib/utils';

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

function HeroChip({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: 'emerald' | 'sky' | 'rose' | 'default';
}) {
  const valueClass =
    accent === 'emerald'
      ? 'text-emerald-700 dark:text-emerald-300'
      : accent === 'sky'
        ? 'text-sky-700 dark:text-sky-300'
        : accent === 'rose'
          ? 'text-rose-700 dark:text-rose-300'
          : 'text-foreground';
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2.5 sm:px-4 sm:py-3 min-w-0">
      <div className="text-[10px] sm:text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          'mt-0.5 text-base sm:text-lg font-semibold tabular-nums truncate',
          valueClass,
        )}
        title={value}
      >
        {value}
      </div>
    </div>
  );
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
  const title = clientLoanTitle(account?.display_name || account?.name, 'Loan');

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex justify-center text-muted-foreground">Loading loan…</div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="container mx-auto py-8">
        <Alert variant="destructive">
          <AlertDescription>Failed to load loan</AlertDescription>
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

  const outstanding = Math.max(parseFloat(overview.principal_remaining) || 0, 0);
  const emiLabel =
    currentEmi > 0 ? formatCurrency(currentEmi, currency, locale) : 'No EMI';
  const rateLabel = currentRate > 0 ? `${currentRate.toFixed(2)}%` : '—';
  const nextDueLabel = formatLoanNextDue(
    (account as { next_due_date?: string | null } | undefined)?.next_due_date,
    locale,
  );

  return (
    <div className="container mx-auto py-5 sm:py-6 space-y-4 px-3 sm:px-4">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground leading-snug">
          {title}
        </h1>
        <div className="flex flex-wrap gap-2 shrink-0">
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

      {/* Hero chips ONLY — Outstanding · EMI · Rate · Next due */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-2.5">
        <HeroChip
          label="Outstanding"
          value={formatCurrency(outstanding, currency, locale)}
          accent="emerald"
        />
        <HeroChip label="EMI" value={emiLabel} />
        <HeroChip label="Rate" value={rateLabel} accent="sky" />
        <HeroChip label="Next due" value={nextDueLabel} />
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
            outstandingBalance={outstanding}
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
            isNrpOrCommercial={isNrp}
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

export default LoanDetailPage;
