import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { LoanDetailPage } from '../LoanDetailPage';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';

vi.mock('@/contexts/auth-context', () => ({
  useAuth: () => ({
    user: { preferences: { currency_display: 'INR' } },
  }),
}));

vi.mock('@/hooks/use-display-locale', () => ({
  useDisplayLocale: () => 'en-IN',
}));

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<any>('@/lib/api');
  return {
    ...actual,
    accounts: {
      ...actual.accounts,
      get: vi.fn(async () => ({
        id: '123-456',
        currency: 'INR',
        name: 'Home Loan',
        display_name: 'Home Loan',
        interest_rate: 8.5,
        emi_amount: 25000,
        next_due_date: '2026-10-05',
      })),
    },
  };
});

const mockOverview = {
  progress_percent: 25.5,
  emis_paid: 6,
  emis_remaining: 18,
  principal_paid: '120000.00',
  principal_remaining: '480000.00',
  interest_paid: '45000.00',
  interest_remaining: '135000.00',
  total_prepayments: '20000.00',
};

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <Routes>
        <Route path="/loans/:accountId" element={children} />
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
);

vi.mock('@/components/loans/LoanSimulations', () => ({
  LoanSimulations: () => <div data-testid="loan-simulations">Simulations</div>,
}));

vi.mock('@/components/loans/CombinedLoanSimulator', () => ({
  CombinedLoanSimulator: () => <div data-testid="combined-sim">Combined</div>,
}));

vi.mock('../LoanScheduleTable', () => ({
  LoanScheduleTable: ({ accountId }: { accountId: string }) => (
    <div data-testid="schedule-table">Schedule for {accountId}</div>
  ),
}));

vi.mock('../LoanAnalyticsCharts', () => ({
  LoanAnalyticsCharts: ({ accountId }: { accountId: string }) => (
    <div data-testid="analytics-charts">Analysis for {accountId}</div>
  ),
}));

vi.mock('../PrepaymentDialog', () => ({
  PrepaymentDialog: ({ open }: any) =>
    open ? <div data-testid="prepayment-dialog">Prepayment Dialog</div> : null,
}));

describe('LoanDetailPage', () => {
  beforeEach(() => {
    queryClient.clear();
    global.fetch = vi.fn();
    window.history.pushState({}, '', '/loans/123-456');
  });

  it('shows loading state', () => {
    (global.fetch as any).mockImplementation(
      () => new Promise(() => {}),
    );

    render(<LoanDetailPage />, { wrapper });
    expect(screen.getByText('Loading loan…')).toBeInTheDocument();
  });

  it('renders hero chips only (Outstanding · EMI · Rate · Next due)', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockOverview,
    });

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Home Loan')).toBeInTheDocument();
    });

    expect(screen.getByText('Outstanding')).toBeInTheDocument();
    expect(screen.getByText('EMI')).toBeInTheDocument();
    expect(screen.getByText('Rate')).toBeInTheDocument();
    expect(screen.getByText('Next due')).toBeInTheDocument();
    expect(screen.getByText('8.50%')).toBeInTheDocument();
    // engineer KPIs gone from hero
    expect(screen.queryByText('Progress')).not.toBeInTheDocument();
    expect(screen.queryByText(/Principal \(/)).not.toBeInTheDocument();
  });

  it('renders error state on fetch failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
    });

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Failed to load loan')).toBeInTheDocument();
    });
  });

  it('opens prepayment dialog on Prepay click', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockOverview,
    });

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Home Loan')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Prepay/i }));
    expect(screen.getByTestId('prepayment-dialog')).toBeInTheDocument();
  });
});
