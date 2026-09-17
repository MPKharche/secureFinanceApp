import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { PageHeader } from '@/components/page-header'
import { toast } from 'sonner'
import { TrendingUp, Plus, Trash2, AlertCircle, Calculator } from 'lucide-react'
import { format } from 'date-fns'

interface AssetSale {
  asset_name: string
  asset_type: string
  buy_date: string
  sell_date: string
  buy_price: string
  sell_price: string
  quantity: string
}

interface CapitalGainResult {
  asset_name: string
  asset_type: string
  gain_loss: number
  holding_period_days: number
  classification: string
  asset_class: string
  tax_rate: number
  tax_amount: number
}

interface CapitalGainsSummary {
  financial_year: string
  equity_stcg_total: number
  equity_stcg_tax: number
  equity_ltcg_total: number
  equity_ltcg_exempt: number
  equity_ltcg_taxable: number
  equity_ltcg_tax: number
  debt_stcg_total: number
  debt_ltcg_total: number
  debt_ltcg_tax: number
  total_gains: number
  total_tax: number
  cess: number
  total_tax_with_cess: number
  advance_tax_required: boolean
  advance_tax_schedule: Array<{
    due_date: string
    cumulative_percent: number
    amount: number
  }>
}

const ASSET_TYPES = [
  { value: 'equity', label: 'Equity (Stocks, ETFs)' },
  { value: 'mutual_fund', label: 'Equity Mutual Funds' },
  { value: 'debt', label: 'Debt Funds/Bonds' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'gold', label: 'Gold' },
  { value: 'crypto', label: 'Cryptocurrency' },
]

const CURRENT_FY = '2026-27'

export default function CapitalGainsPage() {
  const [sales, setSales] = useState<AssetSale[]>([
    {
      asset_name: '',
      asset_type: 'equity',
      buy_date: '',
      sell_date: '',
      buy_price: '',
      sell_price: '',
      quantity: '1',
    },
  ])
  const [taxSlabRate, setTaxSlabRate] = useState('0.30')
  const [results, setResults] = useState<{
    gains: CapitalGainResult[]
    summary: CapitalGainsSummary
  } | null>(null)

  const calculateMutation = useMutation({
    mutationFn: async (data: { financial_year: string; sales: AssetSale[]; user_income_tax_slab_rate: number }) => {
      const response = await fetch('/api/capital-gains/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to calculate capital gains')
      }
      return response.json()
    },
    onSuccess: (data) => {
      setResults(data)
      toast.success('Capital gains calculated successfully')
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const addSale = () => {
    setSales([
      ...sales,
      {
        asset_name: '',
        asset_type: 'equity',
        buy_date: '',
        sell_date: '',
        buy_price: '',
        sell_price: '',
        quantity: '1',
      },
    ])
  }

  const removeSale = (index: number) => {
    setSales(sales.filter((_, i) => i !== index))
  }

  const updateSale = (index: number, field: keyof AssetSale, value: string) => {
    const updated = [...sales]
    updated[index][field] = value
    setSales(updated)
  }

  const handleCalculate = () => {
    // Validate
    const invalidSales = sales.filter(
      (s) =>
        !s.asset_name ||
        !s.buy_date ||
        !s.sell_date ||
        !s.buy_price ||
        !s.sell_price ||
        parseFloat(s.buy_price) <= 0 ||
        parseFloat(s.sell_price) <= 0
    )

    if (invalidSales.length > 0) {
      toast.error('Please fill all fields with valid values')
      return
    }

    calculateMutation.mutate({
      financial_year: CURRENT_FY,
      sales,
      user_income_tax_slab_rate: parseFloat(taxSlabRate),
    })
  }

  return (
    <div className="space-y-6 pb-16">
      <PageHeader
        section="Tax Planning"
        title="Capital Gains Calculator"
        description={`Calculate capital gains tax for FY ${CURRENT_FY}`}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="size-5" />
            Asset Sales
          </CardTitle>
          <CardDescription>Add all asset sales made during the financial year</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Tax Slab Rate */}
          <div className="flex items-end gap-4 mb-4">
            <div className="flex-1">
              <Label>Your Income Tax Slab Rate</Label>
              <Select value={taxSlabRate} onValueChange={setTaxSlabRate}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0.05">5% (₹2.5L - ₹5L)</SelectItem>
                  <SelectItem value="0.10">10% (₹5L - ₹7.5L)</SelectItem>
                  <SelectItem value="0.15">15% (₹7.5L - ₹10L)</SelectItem>
                  <SelectItem value="0.20">20% (₹10L - ₹12.5L)</SelectItem>
                  <SelectItem value="0.25">25% (₹12.5L - ₹15L)</SelectItem>
                  <SelectItem value="0.30">30% (Above ₹15L)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">
                Used for debt short-term capital gains tax calculation
              </p>
            </div>
          </div>

          <Separator />

          {/* Sales List */}
          {sales.map((sale, index) => (
            <div key={index} className="grid grid-cols-1 md:grid-cols-7 gap-4 p-4 border rounded-lg relative">
              {sales.length > 1 && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2 size-8"
                  onClick={() => removeSale(index)}
                >
                  <Trash2 className="size-4" />
                </Button>
              )}

              <div className="md:col-span-2">
                <Label>Asset Name</Label>
                <Input
                  placeholder="e.g., Reliance"
                  value={sale.asset_name}
                  onChange={(e) => updateSale(index, 'asset_name', e.target.value)}
                />
              </div>

              <div>
                <Label>Asset Type</Label>
                <Select value={sale.asset_type} onValueChange={(v) => updateSale(index, 'asset_type', v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ASSET_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Buy Date</Label>
                <Input
                  type="date"
                  value={sale.buy_date}
                  onChange={(e) => updateSale(index, 'buy_date', e.target.value)}
                />
              </div>

              <div>
                <Label>Sell Date</Label>
                <Input
                  type="date"
                  value={sale.sell_date}
                  onChange={(e) => updateSale(index, 'sell_date', e.target.value)}
                />
              </div>

              <div>
                <Label>Buy Price (₹)</Label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="1000.00"
                  value={sale.buy_price}
                  onChange={(e) => updateSale(index, 'buy_price', e.target.value)}
                />
              </div>

              <div>
                <Label>Sell Price (₹)</Label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="1500.00"
                  value={sale.sell_price}
                  onChange={(e) => updateSale(index, 'sell_price', e.target.value)}
                />
              </div>
            </div>
          ))}

          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={addSale}>
              <Plus className="size-4 mr-2" />
              Add Another Sale
            </Button>
            <Button onClick={handleCalculate} disabled={calculateMutation.isPending}>
              <Calculator className="size-4 mr-2" />
              {calculateMutation.isPending ? 'Calculating...' : 'Calculate Tax'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {results && (
        <>
          {/* Individual Gains */}
          <Card>
            <CardHeader>
              <CardTitle>Transaction Details</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Asset</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Gain/Loss</TableHead>
                    <TableHead className="text-center">Holding Period</TableHead>
                    <TableHead className="text-center">Classification</TableHead>
                    <TableHead className="text-right">Tax Rate</TableHead>
                    <TableHead className="text-right">Tax Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.gains.map((gain, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{gain.asset_name}</TableCell>
                      <TableCell className="capitalize">{gain.asset_type.replace('_', ' ')}</TableCell>
                      <TableCell
                        className={`text-right font-medium ${
                          gain.gain_loss >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        ₹{gain.gain_loss.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-center">{gain.holding_period_days} days</TableCell>
                      <TableCell className="text-center">
                        <Badge variant={gain.classification === 'LTCG' ? 'default' : 'secondary'}>
                          {gain.classification}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">{(gain.tax_rate * 100).toFixed(1)}%</TableCell>
                      <TableCell className="text-right">₹{gain.tax_amount.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Tax Summary - FY {results.summary.financial_year}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Equity */}
                <div className="space-y-3">
                  <h3 className="font-semibold text-lg border-b pb-2">Equity</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Short-term gains:</span>
                      <span className="font-medium">₹{results.summary.equity_stcg_total.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">STCG tax (15%):</span>
                      <span className="font-medium">₹{results.summary.equity_stcg_tax.toFixed(2)}</span>
                    </div>
                    <Separator />
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Long-term gains:</span>
                      <span className="font-medium">₹{results.summary.equity_ltcg_total.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Less: Exemption:</span>
                      <span className="font-medium text-green-600">
                        -₹{results.summary.equity_ltcg_exempt.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Taxable LTCG:</span>
                      <span className="font-medium">₹{results.summary.equity_ltcg_taxable.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">LTCG tax (10%):</span>
                      <span className="font-medium">₹{results.summary.equity_ltcg_tax.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                {/* Debt */}
                <div className="space-y-3">
                  <h3 className="font-semibold text-lg border-b pb-2">Debt</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Short-term gains:</span>
                      <span className="font-medium">₹{results.summary.debt_stcg_total.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Long-term gains:</span>
                      <span className="font-medium">₹{results.summary.debt_ltcg_total.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">LTCG tax (20% + indexation):</span>
                      <span className="font-medium">₹{results.summary.debt_ltcg_tax.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Total */}
              <div className="space-y-2 bg-primary/5 p-4 rounded-lg">
                <div className="flex justify-between text-lg">
                  <span className="font-semibold">Total Tax:</span>
                  <span className="font-bold">₹{results.summary.total_tax.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Cess (4%):</span>
                  <span className="font-medium">₹{results.summary.cess.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-xl">
                  <span className="font-bold">Total Tax Payable:</span>
                  <span className="font-bold text-primary">₹{results.summary.total_tax_with_cess.toFixed(2)}</span>
                </div>
              </div>

              {/* Advance Tax */}
              {results.summary.advance_tax_required && (
                <Alert>
                  <AlertCircle className="size-4" />
                  <AlertTitle>Advance Tax Required</AlertTitle>
                  <AlertDescription>
                    <p className="mb-3">
                      Your tax liability exceeds ₹10,000. You must pay advance tax as per the following schedule:
                    </p>
                    <div className="space-y-2">
                      {results.summary.advance_tax_schedule.map((schedule, index) => (
                        <div key={index} className="flex justify-between text-sm">
                          <span>
                            By {format(new Date(schedule.due_date), 'dd MMM yyyy')} (
                            {(schedule.cumulative_percent * 100).toFixed(0)}%):
                          </span>
                          <span className="font-medium">₹{schedule.amount.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
