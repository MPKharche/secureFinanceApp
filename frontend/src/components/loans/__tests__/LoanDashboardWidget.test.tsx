import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { LoanDashboardWidget } from '../LoanDashboardWidget';
import { vi } from 'vitest';

const mockDashboardData = {
  next_due_payments: [
    {
      account_id: '123',
      account_name: 'Home Loan',
      due_date: '2026-09-05',
      emi_amount: '25000.00',
      days_until_due: 5,
    },
  ],
  recent_payments: [
    {
      account_name: 'Car Loan',
      payment_date: '2026-08-25',
      amount_paid: '15000.00',
    },
  ],
  alerts: [
    {
      type: 'payment_due',
      message: 'Payment due in 3 days',
      account_id: '123',
    },
  ],
  total_monthly_emi: '40000.00',
  total_outstanding: '500000.00',
};

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>{children}</BrowserRouter>
  </QueryClientProvider>
);

describe('LoanDashboardWidget', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    queryClient.clear();
  });

  it('renders loading state', () => {
    (global.fetch as any).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<LoanDashboardWidget />, { wrapper });
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders dashboard data successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockDashboardData,
    });

    render(<LoanDashboardWidget />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Total Outstanding')).toBeInTheDocument();
    });

    expect(screen.getByText('Monthly EMI')).toBeInTheDocument();
    expect(screen.getByText('Home Loan')).toBeInTheDocument();
    expect(screen.getByText('Due This Week')).toBeInTheDocument();
    expect(screen.getByText('Recent Payments')).toBeInTheDocument();
  });

  it('renders alerts when present', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockDashboardData,
    });

    render(<LoanDashboardWidget />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Payment due in 3 days')).toBeInTheDocument();
    });
  });

  it('renders error state on fetch failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
    });

    render(<LoanDashboardWidget />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Failed to load loan data')).toBeInTheDocument();
    });
  });

  it('filters upcoming payments within 7 days', async () => {
    const dataWithFuturePayment = {
      ...mockDashboardData,
      next_due_payments: [
        ...mockDashboardData.next_due_payments,
        {
          account_id: '456',
          account_name: 'Personal Loan',
          due_date: '2026-09-20',
          emi_amount: '10000.00',
          days_until_due: 20,
        },
      ],
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => dataWithFuturePayment,
    });

    render(<LoanDashboardWidget />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Home Loan')).toBeInTheDocument();
    });

    expect(screen.queryByText('Personal Loan')).not.toBeInTheDocument();
  });
});
