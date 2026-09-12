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
      get: vi.fn(async () => ({ id: '123-456', currency: 'INR', name: 'Home Loan' })),
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

// Mock child components
vi.mock('@/components/loans/LoanSimulations', () => ({
  LoanSimulations: () => <div data-testid="loan-simulations">Simulations</div>,
}));

vi.mock('@/components/loans/CombinedLoanSimulator', () => ({
  CombinedLoanSimulator: () => <div data-testid="combined-sim">Combined</div>,
}));

vi.mock('./LoanScheduleTable', () => ({
  LoanScheduleTable: ({ accountId }: { accountId: string }) => (
    <div data-testid="schedule-table">Schedule for {accountId}</div>
  ),
}));

vi.mock('./LoanAnalyticsCharts', () => ({
  LoanAnalyticsCharts: ({ accountId }: { accountId: string }) => (
    <div data-testid="analytics-charts">Analytics for {accountId}</div>
  ),
}));

vi.mock('./PrepaymentDialog', () => ({
  PrepaymentDialog: ({ open }: any) => (
    open ? <div data-testid="prepayment-dialog">Prepayment Dialog</div> : null
  ),
}));


describe('LoanDetailPage', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
    window.history.pushState({}, '', '/loans/123-456');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    queryClient.clear();
  });

  it('renders loading state', () => {
    (global.fetch as any).mockImplementation(
      () => new Promise(() => {})
    );

    render(<LoanDetailPage />, { wrapper });
    expect(screen.getByText('Loading loan details...')).toBeInTheDocument();
  });

  it('renders overview cards successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockOverview,
    });

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('25.5%')).toBeInTheDocument();
    });

    expect(screen.getByText('6 of 24 EMIs paid')).toBeInTheDocument();
    // 120000 / (120000+480000) = 20.0%; 45000 / (45000+135000) = 25.0%
    expect(screen.getByText('Principal Paid (20.0%)')).toBeInTheDocument();
    expect(screen.getByText('Interest Paid (25.0%)')).toBeInTheDocument();
    expect(screen.getByText('Prepayments')).toBeInTheDocument();
  });

  it('renders error state on fetch failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
    });

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Failed to load loan details')).toBeInTheDocument();
    });
  });

  it('opens prepayment dialog on button click', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockOverview,
    });

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Loan Details')).toBeInTheDocument();
    });

    const prepaymentButton = screen.getByRole('button', { name: /Make Prepayment/i });
    await user.click(prepaymentButton);

    expect(screen.getByTestId('prepayment-dialog')).toBeInTheDocument();
  });

  it('exports CSV when export button clicked', async () => {
    const user = userEvent.setup();
    const mockBlob = new Blob(['csv content'], { type: 'text/csv' });

    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockOverview,
      })
      .mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

    const createElementSpy = vi.spyOn(document, 'createElement');
    const createObjectURLSpy = vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:url');

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Loan Details')).toBeInTheDocument();
    });

    const exportButton = screen.getByRole('button', { name: /Export CSV/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(createObjectURLSpy).toHaveBeenCalledWith(mockBlob);
    });

    createObjectURLSpy.mockRestore();
  });

  it('renders schedule table in schedule tab', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockOverview,
    });

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('schedule-table')).toBeInTheDocument();
    });
  });

  it('switches to analytics tab', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockOverview,
    });

    render(<LoanDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Loan Details')).toBeInTheDocument();
    });

    const analyticsTab = screen.getByRole('tab', { name: /Analytics/i });
    await user.click(analyticsTab);

    expect(screen.getByTestId('analytics-charts')).toBeInTheDocument();
  });
});
