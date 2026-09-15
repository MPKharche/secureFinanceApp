# Budget Spreadsheet: 12-Month Multi-Section View

**Date:** 2026-09-16  
**Status:** Design Approved  
**Scope:** Phase 1 Implementation

---

## Overview

Transform the single-month budget list into a comprehensive 12-month spreadsheet with Excel-like editing, real-time sync, income/expense/investment tracking, rollover budgets, templates, spending pace indicators, goal linkage, and scenario modeling.

### User Value

- **Multi-month planning:** See 5 past months (actuals) + current + 6 future months (budgets) in one view
- **Section clarity:** Income, Expenses, and Investments grouped with subtotals
- **Real-time editing:** Click cell, type, press Enter → auto-saves with optimistic updates
- **Smart budgeting:** Rollover unspent amounts, copy/paste across months, link to goals
- **Informed decisions:** Spending pace warnings, variance tooltips, trend visualizations
- **Mobile support:** Responsive single-month swipe view on small screens
- **What-if analysis:** Create scenarios ("What if salary +10%?") and compare side-by-side

---

## Architecture

### Component Structure

```
/budgets (route)
├── BudgetSpreadsheetPage
│   ├── TrendSummaryBar
│   │   ├── MonthlyMetricsScroller (12 cards: income/expenses/savings %)
│   │   └── TrendAreaChart (recharts: income/expenses/investments/savings)
│   ├── BudgetDataGrid (react-data-grid wrapper)
│   │   ├── Section Header: INCOME
│   │   ├── Category Rows (income type)
│   │   ├── Income Subtotal Row (calculated)
│   │   ├── Section Header: EXPENSES
│   │   ├── Category Rows (expense type)
│   │   ├── Expenses Subtotal Row
│   │   ├── Section Header: INVESTMENTS
│   │   ├── Category Rows (investment type)
│   │   ├── Investments Subtotal Row
│   │   └── Net Savings Row (Income - Expenses - Investments)
│   ├── EditDialog (recurring budget: "Just this month" vs "This and future")
│   ├── TemplateDialog (save/load budget templates)
│   └── ScenarioComparisonView (side-by-side scenario grids)
└── /budgets/report (route)
    └── BudgetAnalysisPage
        ├── VarianceCharts (budget vs actual per category)
        ├── MonthOverMonthTrends
        └── CategoryBreakdowns

/budgets/scenarios/:scenarioId (route)
└── ScenarioDetailPage (editable scenario grid)
```

### Data Model Changes

#### 1. Categories Table

**Add columns:**
```sql
ALTER TABLE categories 
  ADD COLUMN category_type VARCHAR(20) DEFAULT 'expense',
  ADD COLUMN enable_rollover BOOLEAN DEFAULT false;

-- Values: 'income', 'expense', 'investment'
-- enable_rollover: if true, (budget - actual) from previous month carries forward
```

**Migration:** Existing categories default to `expense` type, `enable_rollover=false`.

#### 2. Goals Table

**Add column:**
```sql
ALTER TABLE goals 
  ADD COLUMN linked_category_ids UUID[] DEFAULT '{}';

-- Array of category IDs; goal progress shown in budget grid for linked categories
```

#### 3. Budget Templates Table (New)

```sql
CREATE TABLE budget_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  template_data JSONB NOT NULL,
  -- template_data structure:
  -- { "categories": [ { "category_id": "uuid", "amount": 1000.00 }, ... ] }
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT uq_template_name_per_workspace UNIQUE(workspace_id, name)
);

CREATE INDEX idx_budget_templates_workspace ON budget_templates(workspace_id);
```

#### 4. Budget Scenarios Table (New)

```sql
CREATE TABLE budget_scenarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  base_month DATE NOT NULL, -- YYYY-MM-01 format
  adjustments JSONB NOT NULL,
  -- adjustments structure:
  -- { "categories": [ { "category_id": "uuid", "adjustment_type": "percent|fixed", "value": 10 }, ... ] }
  -- adjustment_type: "percent" (+10% salary) or "fixed" (+500 rent)
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT uq_scenario_name_per_workspace UNIQUE(workspace_id, name)
);

CREATE INDEX idx_budget_scenarios_workspace ON budget_scenarios(workspace_id);
```

#### 5. Notifications Table (Extend or Create)

If `notifications` table doesn't exist:
```sql
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  type VARCHAR(50) NOT NULL, -- 'budget_overrun', 'goal_progress', etc.
  title VARCHAR(255) NOT NULL,
  message TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  read BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_unread ON notifications(user_id, read, created_at DESC);
```

If it exists, ensure `type='budget_overrun'` is supported.

---

## Backend API Changes

### New Endpoints

#### 1. Bulk Budget Query
```
GET /api/budgets/multi-month?start_month=2025-09-01&end_month=2026-08-01
```

**Response:**
```json
[
  {
    "id": "uuid",
    "category_id": "uuid",
    "amount": 1000.00,
    "month": "2025-09-01",
    "is_recurring": true
  },
  ...
]
```

**Logic:** For each month in range, resolve budgets using existing logic:
- Month-specific override (is_recurring=false, month=M) takes priority
- Most recent recurring default (is_recurring=true, month<=M) as fallback

#### 2. Bulk Actuals Query
```
GET /api/budgets/actuals?start_month=2025-09-01&end_month=2026-08-01
```

**Response:**
```json
{
  "category_actuals": {
    "category-uuid-1": {
      "2025-09": 950.00,
      "2025-10": 1020.00,
      ...
    },
    ...
  }
}
```

**Logic:** For each category + month, sum posted transactions:
- Type=debit (expenses/investments) or type=credit (income)
- Use `amount_primary` for multi-currency support
- Apply existing split logic (owner share, group share)
- Filter: status=posted, report_date within month range

#### 3. Budget Templates

```
POST /api/budgets/templates
Body: { "name": "Q4 2025 Default", "description": "...", "category_amounts": { "cat-uuid": 1000, ... } }
Response: BudgetTemplate

GET /api/budgets/templates
Response: BudgetTemplate[]

DELETE /api/budgets/templates/{id}

POST /api/budgets/apply-template
Body: { "template_id": "uuid", "target_months": ["2025-10-01", "2025-11-01", ...], "is_recurring": false }
Response: { "created_count": 24 }
```

**Logic:** `apply-template` creates or updates budgets for each category × target month combination.

#### 4. Budget Scenarios

```
POST /api/budgets/scenarios
Body: { "name": "Salary +10%", "description": "...", "base_month": "2025-09-01", "adjustments": [...] }
Response: BudgetScenario

GET /api/budgets/scenarios
Response: BudgetScenario[]

GET /api/budgets/scenarios/{id}/preview?months=12
Response: { "months": [ { "month": "2025-09", "categories": [ { "category_id": "...", "base_amount": 1000, "adjusted_amount": 1100, ... } ] } ] }

DELETE /api/budgets/scenarios/{id}
```

**Logic:** `preview` applies adjustments to base budgets and returns projected amounts for comparison.

#### 5. CSV Export

```
GET /api/budgets/export?start_month=2025-09-01&end_month=2026-08-01&format=csv
Response: CSV file download
```

**CSV Structure:**
```csv
Category,Type,2025-09 Budget,2025-09 Actual,2025-10 Budget,2025-10 Actual,...
Salary,income,5000,5000,5000,5100,...
Housing,expense,1200,1200,1200,1180,...
```

#### 6. Notifications

```
GET /api/notifications?type=budget_overrun&unread=true
Response: Notification[]

PATCH /api/notifications/{id}/read
```

**Backend Job:** Daily celery task checks for budget overruns (actual > budget × 1.2 for current month), creates notifications.

### Modified Endpoints

#### Update Budget Endpoint
```
PATCH /api/budgets/{id}
Body: { "amount": 1200, "apply_to_future": true } // new field
```

**Logic:** If `apply_to_future=true` and budget is recurring, create new recurring budget with `month=current_edit_month` (updates effective-from date).

---

## Frontend Implementation

### 1. BudgetSpreadsheetPage Component

**File:** `frontend/src/pages/budgets.tsx` (replace existing)

**State:**
```typescript
interface BudgetGridRow {
  type: 'category' | 'subtotal' | 'total' | 'section-header'
  categoryId?: string
  categoryName: string
  categoryType?: 'income' | 'expense' | 'investment'
  categoryIcon?: string
  categoryColor?: string
  enableRollover?: boolean
  linkedGoalId?: string
  isRecurring?: boolean
  months: {
    [monthKey: string]: {
      budget: number | null
      budgetId?: string
      actual: number | null
      rollover?: number
      projected?: number // for spending pace
      isEditable: boolean
    }
  }
}

const [rows, setRows] = useState<BudgetGridRow[]>([])
const [selectedMonth, setSelectedMonth] = useState<Date>() // center month in 12-month range
const [editingCell, setEditingCell] = useState<{ rowId: string, monthKey: string } | null>(null)
const [templates, setTemplates] = useState<BudgetTemplate[]>([])
const [scenarios, setScenarios] = useState<BudgetScenario[]>([])
```

**Data Loading:**
1. On mount, calculate 12-month range: `selectedMonth - 5 months` to `selectedMonth + 6 months`
2. Parallel fetch:
   - `budgetsApi.multiMonth(startMonth, endMonth)`
   - `budgetsApi.actuals(startMonth, endMonth)`
   - `categoriesApi.list()`
   - `goalsApi.list()`
3. Merge into `rows` structure:
   - Group categories by `category_type`
   - Calculate rollover for enabled categories: `rollover = prev_month.budget - prev_month.actual`
   - Calculate projected spend for current month: `projected = (actual / days_elapsed) × days_in_month`
   - Insert subtotal rows (calculated), section headers, net savings row

**Grid Configuration (react-data-grid):**
```typescript
import DataGrid, { Column } from 'react-data-grid'

const columns: Column<BudgetGridRow>[] = [
  {
    key: 'category',
    name: 'Category',
    frozen: true,
    width: 200,
    renderCell: ({ row }) => {
      if (row.type === 'section-header') return <strong>{row.categoryName}</strong>
      if (row.type === 'subtotal' || row.type === 'total') 
        return <strong className="text-muted-foreground">{row.categoryName}</strong>
      return (
        <span className="flex items-center gap-2">
          <CategoryIcon icon={row.categoryIcon} color={row.categoryColor} size="sm" />
          {row.categoryName}
          {row.linkedGoalId && <Badge>Goal</Badge>}
        </span>
      )
    }
  },
  ...monthColumns // one column per month in range
]

const monthColumns = monthKeys.map(monthKey => ({
  key: monthKey,
  name: format(parseISO(monthKey), 'MMM yyyy'),
  width: 120,
  renderCell: ({ row }) => <MonthCell row={row} monthKey={monthKey} />,
  renderEditCell: ({ row }) => <MonthCellEditor row={row} monthKey={monthKey} />
}))
```

### 2. MonthCell Component

**Rendering Logic:**
```typescript
function MonthCell({ row, monthKey }: { row: BudgetGridRow, monthKey: string }) {
  const cell = row.months[monthKey]
  if (!cell) return <div className="p-2">—</div>
  
  // Subtotal/Total rows
  if (row.type === 'subtotal' || row.type === 'total') {
    const sum = calculateSum(rows, monthKey, row.type)
    return <div className="p-2 font-bold bg-muted">{formatCurrency(sum)}</div>
  }
  
  // Category rows
  const isPast = isBeforeCurrentMonth(monthKey)
  const isCurrent = isCurrentMonth(monthKey)
  const displayValue = isPast ? cell.actual : cell.budget
  const effectiveValue = (cell.budget ?? 0) + (cell.rollover ?? 0)
  
  // Background color
  let bgColor = 'bg-card'
  if (isPast && cell.budget && cell.actual) {
    const variance = cell.actual - cell.budget
    if (row.categoryType === 'income') {
      bgColor = variance > 0 ? 'bg-green-50' : 'bg-red-50'
    } else {
      bgColor = variance < 0 ? 'bg-green-50' : 'bg-red-50'
    }
  }
  
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className={`p-2 ${bgColor} ${cell.isEditable ? 'cursor-pointer hover:bg-muted' : ''}`}>
          {formatCurrency(displayValue)}
          {isCurrent && cell.projected && (
            <ProgressBar value={cell.actual ?? 0} max={cell.projected} />
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent>
        {isPast ? (
          <>
            <div>Budget: {formatCurrency(cell.budget)}</div>
            <div>Actual: {formatCurrency(cell.actual)}</div>
            <div>Variance: {formatCurrency((cell.actual ?? 0) - (cell.budget ?? 0))}</div>
          </>
        ) : (
          <>
            <div>Budget: {formatCurrency(cell.budget)}</div>
            {cell.rollover && <div>Rollover: {formatCurrency(cell.rollover)}</div>}
            {cell.rollover && <div>Effective: {formatCurrency(effectiveValue)}</div>}
            {row.linkedGoalId && <div>Goal: {getGoalProgress(row.linkedGoalId)}</div>}
          </>
        )}
      </TooltipContent>
    </Tooltip>
  )
}
```

### 3. MonthCellEditor Component

**Inline Editing:**
```typescript
function MonthCellEditor({ row, monthKey }: { row: BudgetGridRow, monthKey: string }) {
  const [value, setValue] = useState(row.months[monthKey]?.budget?.toString() ?? '')
  const inputRef = useRef<HTMLInputElement>(null)
  
  useEffect(() => {
    inputRef.current?.select() // auto-select on edit
  }, [])
  
  const handleSave = async () => {
    const newAmount = parseFloat(value)
    if (isNaN(newAmount)) return
    
    // Optimistic update
    updateRowOptimistically(row.categoryId, monthKey, newAmount)
    
    // Check if recurring
    if (row.isRecurring) {
      const applyToFuture = await showRecurringDialog()
      await budgetsApi.update(row.months[monthKey].budgetId, { 
        amount: newAmount, 
        apply_to_future: applyToFuture 
      })
    } else {
      if (row.months[monthKey].budgetId) {
        await budgetsApi.update(row.months[monthKey].budgetId, { amount: newAmount })
      } else {
        await budgetsApi.create({
          category_id: row.categoryId,
          amount: newAmount,
          month: monthKey,
          is_recurring: false
        })
      }
    }
    
    // Refetch to get updated data
    queryClient.invalidateQueries(['budgets'])
  }
  
  return (
    <input
      ref={inputRef}
      type="number"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={handleSave}
      onKeyDown={(e) => e.key === 'Enter' && handleSave()}
      className="w-full h-full px-2 border-2 border-primary"
    />
  )
}
```

### 4. Copy/Paste Handler

```typescript
useEffect(() => {
  const handleCopy = (e: ClipboardEvent) => {
    if (!selectedCells.length) return
    const tsvData = selectedCells.map(cell => 
      rows.find(r => r.categoryId === cell.rowId)?.months[cell.monthKey]?.budget ?? ''
    ).join('\t')
    e.clipboardData?.setData('text/plain', tsvData)
    e.preventDefault()
  }
  
  const handlePaste = async (e: ClipboardEvent) => {
    if (!selectedCells.length) return
    const tsvData = e.clipboardData?.getData('text/plain')
    if (!tsvData) return
    
    const values = tsvData.split('\t').map(v => parseFloat(v)).filter(v => !isNaN(v))
    const updates = selectedCells.slice(0, values.length).map((cell, i) => ({
      categoryId: cell.rowId,
      monthKey: cell.monthKey,
      amount: values[i]
    }))
    
    const confirmed = await confirmBatchUpdate(updates.length)
    if (!confirmed) return
    
    // Batch update
    for (const update of updates) {
      await budgetsApi.update(/* ... */)
    }
    
    queryClient.invalidateQueries(['budgets'])
    e.preventDefault()
  }
  
  document.addEventListener('copy', handleCopy)
  document.addEventListener('paste', handlePaste)
  return () => {
    document.removeEventListener('copy', handleCopy)
    document.removeEventListener('paste', handlePaste)
  }
}, [selectedCells])
```

### 5. TrendSummaryBar Component

```typescript
function TrendSummaryBar({ rows, monthKeys }: { rows: BudgetGridRow[], monthKeys: string[] }) {
  const metrics = monthKeys.map(monthKey => {
    const income = sumByType(rows, monthKey, 'income')
    const expenses = sumByType(rows, monthKey, 'expense')
    const investments = sumByType(rows, monthKey, 'investment')
    const savingsRate = income > 0 ? ((income - expenses) / income * 100) : 0
    
    return { monthKey, income, expenses, investments, savingsRate }
  })
  
  return (
    <div className="mb-6 space-y-4">
      {/* Monthly Metrics Scroller */}
      <div className="flex gap-4 overflow-x-auto pb-2">
        {metrics.map(m => (
          <Card key={m.monthKey} className="min-w-[140px] p-3">
            <div className="text-xs text-muted-foreground">{format(parseISO(m.monthKey), 'MMM yyyy')}</div>
            <div className="mt-1 space-y-1">
              <div className="flex items-center gap-1 text-sm">
                <ArrowDown className="w-3 h-3 text-green-600" />
                {formatCurrency(m.income)}
              </div>
              <div className="flex items-center gap-1 text-sm">
                <ArrowUp className="w-3 h-3 text-red-600" />
                {formatCurrency(m.expenses)}
              </div>
              <div className="flex items-center gap-1 text-sm font-semibold">
                <Coins className="w-3 h-3 text-amber-600" />
                {m.savingsRate.toFixed(0)}%
              </div>
            </div>
          </Card>
        ))}
      </div>
      
      {/* 12-Month Trend Chart */}
      <Card className="p-4">
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={metrics}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="monthKey" tickFormatter={(v) => format(parseISO(v), 'MMM')} />
            <YAxis />
            <Tooltip />
            <Area type="monotone" dataKey="income" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.6} />
            <Area type="monotone" dataKey="expenses" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.6} />
            <Area type="monotone" dataKey="investments" stackId="1" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    </div>
  )
}
```

### 6. Budget Templates Dialog

```typescript
function TemplateDialog({ open, onClose }: { open: boolean, onClose: () => void }) {
  const [templates, setTemplates] = useState<BudgetTemplate[]>([])
  const [mode, setMode] = useState<'save' | 'load'>('load')
  
  const handleSaveTemplate = async (name: string, description: string) => {
    const currentBudgets = rows
      .filter(r => r.type === 'category')
      .map(r => ({
        category_id: r.categoryId,
        amount: r.months[selectedMonth]?.budget ?? 0
      }))
    
    await budgetsApi.createTemplate({ name, description, category_amounts: currentBudgets })
    toast.success('Template saved')
    onClose()
  }
  
  const handleLoadTemplate = async (templateId: string, targetMonths: string[]) => {
    await budgetsApi.applyTemplate({ template_id: templateId, target_months: targetMonths })
    queryClient.invalidateQueries(['budgets'])
    toast.success('Template applied')
    onClose()
  }
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Budget Templates</DialogTitle>
          <Tabs value={mode} onValueChange={setMode}>
            <TabsList>
              <TabsTrigger value="load">Load Template</TabsTrigger>
              <TabsTrigger value="save">Save as Template</TabsTrigger>
            </TabsList>
          </Tabs>
        </DialogHeader>
        
        {mode === 'load' ? (
          <div className="space-y-4">
            {templates.map(t => (
              <Card key={t.id} className="p-4">
                <h4 className="font-semibold">{t.name}</h4>
                <p className="text-sm text-muted-foreground">{t.description}</p>
                <Button onClick={() => handleLoadTemplate(t.id, /* select months */)}>
                  Apply to Months...
                </Button>
              </Card>
            ))}
          </div>
        ) : (
          <form onSubmit={(e) => { /* handleSaveTemplate */ }}>
            <Label>Template Name</Label>
            <Input name="name" required />
            <Label>Description</Label>
            <Textarea name="description" />
            <Button type="submit">Save Template</Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
```

### 7. Scenario Comparison View

```typescript
function ScenarioComparisonView({ baseScenarioId, compareScenarioId }: { baseScenarioId: string, compareScenarioId: string }) {
  const { data: basePreview } = useQuery(['scenarios', baseScenarioId, 'preview'], () => 
    budgetsApi.getScenarioPreview(baseScenarioId, 12)
  )
  const { data: comparePreview } = useQuery(['scenarios', compareScenarioId, 'preview'], () =>
    budgetsApi.getScenarioPreview(compareScenarioId, 12)
  )
  
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <h3 className="font-semibold mb-2">Base Scenario</h3>
        <BudgetDataGrid rows={transformPreviewToRows(basePreview)} readonly />
      </div>
      <div>
        <h3 className="font-semibold mb-2">Comparison Scenario</h3>
        <BudgetDataGrid rows={transformPreviewToRows(comparePreview)} readonly />
      </div>
    </div>
  )
}
```

### 8. Mobile Responsive View

```typescript
// In BudgetSpreadsheetPage
const isMobile = useMediaQuery('(max-width: 768px)')

{isMobile ? (
  <MobileBudgetView
    rows={rows}
    selectedMonth={selectedMonth}
    onMonthChange={setSelectedMonth}
  />
) : (
  <BudgetDataGrid rows={rows} columns={columns} />
)}

function MobileBudgetView({ rows, selectedMonth, onMonthChange }) {
  return (
    <div className="space-y-4">
      {/* Swipeable month selector */}
      <div className="flex items-center justify-between">
        <Button size="icon" onClick={() => onMonthChange(subMonths(selectedMonth, 1))}>
          <ChevronLeft />
        </Button>
        <h3 className="font-semibold">{format(selectedMonth, 'MMMM yyyy')}</h3>
        <Button size="icon" onClick={() => onMonthChange(addMonths(selectedMonth, 1))}>
          <ChevronRight />
        </Button>
      </div>
      
      {/* Single-month table */}
      {rows.map(row => (
        <Card key={row.categoryId} className="p-4">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <CategoryIcon icon={row.categoryIcon} />
              {row.categoryName}
            </span>
            <input
              type="number"
              value={row.months[format(selectedMonth, 'yyyy-MM')]?.budget ?? ''}
              onChange={(e) => handleCellEdit(row.categoryId, format(selectedMonth, 'yyyy-MM'), e.target.value)}
              className="w-24 text-right border rounded px-2 py-1"
            />
          </div>
        </Card>
      ))}
    </div>
  )
}
```

---

## Budget vs Actual Report Page

**File:** `frontend/src/pages/budgets/report.tsx`

```typescript
export default function BudgetAnalysisPage() {
  const [selectedMonth, setSelectedMonth] = useState<Date>(startOfMonth(new Date()))
  const { data: comparison } = useQuery(['budgets', 'comparison', selectedMonth], () =>
    budgetsApi.comparison(format(selectedMonth, 'yyyy-MM-dd'))
  )
  
  return (
    <div className="space-y-6">
      <PageHeader section="Budgets" title="Budget vs Actual Report" />
      
      {/* Variance Chart */}
      <Card className="p-4">
        <h3 className="font-semibold mb-4">Budget vs Actual by Category</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={comparison}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="category_name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="budget_amount" fill="#3b82f6" name="Budget" />
            <Bar dataKey="actual_amount" fill="#10b981" name="Actual" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
      
      {/* Month-over-Month Trends */}
      <Card className="p-4">
        <h3 className="font-semibold mb-4">Spending Trends (Last 6 Months)</h3>
        {/* Line chart showing category trends over time */}
      </Card>
      
      {/* Top Overspenders */}
      <Card className="p-4">
        <h3 className="font-semibold mb-4">Categories Over Budget</h3>
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-left">Category</th>
              <th className="text-right">Budget</th>
              <th className="text-right">Actual</th>
              <th className="text-right">Variance</th>
            </tr>
          </thead>
          <tbody>
            {comparison?.filter(c => c.actual_amount > c.budget_amount).map(c => (
              <tr key={c.category_id}>
                <td>{c.category_name}</td>
                <td className="text-right">{formatCurrency(c.budget_amount)}</td>
                <td className="text-right">{formatCurrency(c.actual_amount)}</td>
                <td className="text-right text-red-600">
                  +{formatCurrency(c.actual_amount - c.budget_amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
```

---

## Backend Service Logic

### 1. Multi-Month Budget Service

**File:** `backend/app/services/budget_service.py`

**Add function:**
```python
async def get_budgets_multi_month(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    start_month: date,
    end_month: date,
) -> list[Budget]:
    """
    Fetch all effective budgets for each month in range.
    Uses existing resolution logic: month-specific override > most recent recurring.
    """
    all_budgets = []
    current = start_month.replace(day=1)
    
    while current <= end_month:
        month_budgets = await get_budgets(session, workspace_id, current)
        all_budgets.extend(month_budgets)
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # Deduplicate by (category_id, month) — keep most specific entry
    unique_budgets = {}
    for b in all_budgets:
        key = (str(b.category_id), b.month.strftime('%Y-%m'))
        if key not in unique_budgets or not b.is_recurring:
            unique_budgets[key] = b
    
    return list(unique_budgets.values())
```

### 2. Bulk Actuals Service

**Add function:**
```python
async def get_actuals_multi_month(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    start_month: date,
    end_month: date,
) -> dict[str, dict[str, Decimal]]:
    """
    Returns: { "category_uuid": { "2025-09": 950.00, "2025-10": 1020.00, ... }, ... }
    """
    user = await session.get(User, user_id)
    primary_currency = user.primary_currency if user else get_settings().default_currency
    accounting_mode = await get_credit_card_accounting_mode(session)
    report_date = reporting_date_col(accounting_mode)
    
    # Query all transactions in range
    result = await session.execute(
        select(
            Transaction.category_id,
            func.date_trunc('month', report_date).label('month'),
            func.sum(_primary_amount_expr()).label('total'),
        )
        .where(
            Transaction.workspace_id == workspace_id,
            report_date >= start_month,
            report_date < end_month,
            Transaction.category_id.isnot(None),
            Transaction.status == 'posted',
            counts_as_user_pnl(),
        )
        .group_by(Transaction.category_id, func.date_trunc('month', report_date))
    )
    
    actuals = {}
    for row in result.all():
        cat_id = str(row.category_id)
        month_key = row.month.strftime('%Y-%m')
        if cat_id not in actuals:
            actuals[cat_id] = {}
        actuals[cat_id][month_key] = abs(row.total or Decimal("0"))
    
    # Apply split adjustments (owner share, group share) per month
    # ... (iterate months, call existing offset functions)
    
    return actuals
```

### 3. Budget Template Service

**File:** `backend/app/services/budget_template_service.py` (new)

```python
async def create_template(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: BudgetTemplateCreate,
) -> BudgetTemplate:
    template = BudgetTemplate(
        user_id=user_id,
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        template_data={"categories": [{"category_id": str(c.category_id), "amount": float(c.amount)} for c in data.categories]}
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template

async def apply_template(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    template_id: uuid.UUID,
    target_months: list[date],
    is_recurring: bool,
) -> int:
    template = await session.get(BudgetTemplate, template_id)
    if not template or template.workspace_id != workspace_id:
        raise ValueError("Template not found")
    
    created_count = 0
    for month in target_months:
        for cat_data in template.template_data["categories"]:
            # Check if budget exists
            existing = await session.execute(
                select(Budget).where(
                    Budget.workspace_id == workspace_id,
                    Budget.category_id == uuid.UUID(cat_data["category_id"]),
                    Budget.month == month.replace(day=1),
                    Budget.is_recurring == is_recurring,
                )
            )
            if existing.scalar_one_or_none():
                continue  # Skip existing
            
            budget = Budget(
                user_id=user_id,
                workspace_id=workspace_id,
                category_id=uuid.UUID(cat_data["category_id"]),
                amount=Decimal(str(cat_data["amount"])),
                month=month.replace(day=1),
                is_recurring=is_recurring,
            )
            session.add(budget)
            created_count += 1
    
    await session.commit()
    return created_count
```

### 4. Scenario Service

**File:** `backend/app/services/budget_scenario_service.py` (new)

```python
async def create_scenario(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: BudgetScenarioCreate,
) -> BudgetScenario:
    scenario = BudgetScenario(
        user_id=user_id,
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        base_month=data.base_month.replace(day=1),
        adjustments={"categories": [adj.dict() for adj in data.adjustments]}
    )
    session.add(scenario)
    await session.commit()
    await session.refresh(scenario)
    return scenario

async def preview_scenario(
    session: AsyncSession,
    scenario_id: uuid.UUID,
    workspace_id: uuid.UUID,
    months: int,
) -> dict:
    scenario = await session.get(BudgetScenario, scenario_id)
    if not scenario or scenario.workspace_id != workspace_id:
        raise ValueError("Scenario not found")
    
    # Get base budgets for scenario.base_month + months range
    end_month = scenario.base_month
    for _ in range(months - 1):
        if end_month.month == 12:
            end_month = end_month.replace(year=end_month.year + 1, month=1)
        else:
            end_month = end_month.replace(month=end_month.month + 1)
    
    base_budgets = await get_budgets_multi_month(session, workspace_id, scenario.base_month, end_month)
    
    # Apply adjustments
    adjusted_budgets = []
    for budget in base_budgets:
        adjusted_amount = budget.amount
        for adj in scenario.adjustments["categories"]:
            if str(budget.category_id) == adj["category_id"]:
                if adj["adjustment_type"] == "percent":
                    adjusted_amount = budget.amount * (1 + Decimal(str(adj["value"])) / 100)
                elif adj["adjustment_type"] == "fixed":
                    adjusted_amount = budget.amount + Decimal(str(adj["value"]))
        
        adjusted_budgets.append({
            "category_id": str(budget.category_id),
            "month": budget.month.strftime('%Y-%m'),
            "base_amount": float(budget.amount),
            "adjusted_amount": float(adjusted_amount),
        })
    
    return {"months": adjusted_budgets}
```

### 5. Notification Service (Budget Alerts)

**File:** `backend/app/services/notification_service.py` (extend or create)

**Celery Task:**
```python
@celery_app.task
def check_budget_overruns():
    """
    Daily task: check all workspaces for budget overruns in current month.
    Create notifications for categories where actual > budget × 1.2 (20% over).
    """
    session = get_sync_session()
    current_month = date.today().replace(day=1)
    
    # Get all workspaces
    workspaces = session.execute(select(Workspace)).scalars().all()
    
    for workspace in workspaces:
        # Get budgets and actuals for current month
        budgets = get_budgets(session, workspace.id, current_month)
        actuals = get_actuals_multi_month(session, workspace.id, workspace.owner_id, current_month, current_month)
        
        for budget in budgets:
            cat_id = str(budget.category_id)
            actual_amount = actuals.get(cat_id, {}).get(current_month.strftime('%Y-%m'), Decimal("0"))
            
            if actual_amount > budget.amount * Decimal("1.2"):
                # Create notification
                notification = Notification(
                    user_id=workspace.owner_id,
                    workspace_id=workspace.id,
                    type='budget_overrun',
                    title=f"Budget Alert: {budget.category.name}",
                    message=f"You've spent {actual_amount} vs budget {budget.amount} (20% over)",
                    metadata={"category_id": cat_id, "month": current_month.strftime('%Y-%m')}
                )
                session.add(notification)
        
        session.commit()
```

**Register task in celery beat schedule:**
```python
# backend/app/celeryconfig.py
beat_schedule = {
    'check-budget-overruns': {
        'task': 'app.services.notification_service.check_budget_overruns',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
}
```

---

## Testing Strategy

### 1. Backend Unit Tests

**File:** `backend/tests/test_budget_spreadsheet.py`

```python
async def test_multi_month_budget_query(session):
    # Create recurring budget for Sep 2025
    budget = Budget(...)
    # Assert get_budgets_multi_month returns it for Sep-Aug range
    
async def test_rollover_calculation(session):
    # Budget $500, actual $450 in Sep
    # Assert Oct budget includes $50 rollover
    
async def test_template_apply(session):
    # Create template, apply to 3 months
    # Assert 3 × N budgets created
    
async def test_scenario_adjustment(session):
    # Create scenario with +10% salary
    # Assert preview shows adjusted amounts
```

### 2. Frontend Integration Tests

**File:** `frontend/src/pages/__tests__/budgets.test.tsx`

```typescript
test('renders 12-month grid', async () => {
  render(<BudgetSpreadsheetPage />)
  expect(await screen.findByText('Sep 2025')).toBeInTheDocument()
  expect(await screen.findByText('Aug 2026')).toBeInTheDocument()
})

test('edits budget cell and saves', async () => {
  const { user } = renderWithUser(<BudgetSpreadsheetPage />)
  const cell = await screen.findByText('$1,000')
  await user.click(cell)
  await user.type('{selectall}1200{enter}')
  expect(await screen.findByText('$1,200')).toBeInTheDocument()
})

test('copy/paste across cells', async () => {
  // Simulate copy from one cell, paste to multiple
})
```

---

## Migration Plan

### Phase 1: Database Schema (Day 1)

1. Run Alembic migration:
   - Add `category_type`, `enable_rollover` to categories
   - Add `linked_category_ids` to goals
   - Create `budget_templates`, `budget_scenarios`, `notifications` tables
2. Backfill existing categories: `category_type='expense'`, `enable_rollover=false`
3. Verify migration in staging

### Phase 2: Backend API (Days 2-3)

1. Implement multi-month budget/actuals endpoints
2. Add template CRUD + apply logic
3. Add scenario CRUD + preview logic
4. Add CSV export endpoint
5. Implement notification service + celery task
6. Write unit tests
7. Deploy to staging, test with Postman/curl

### Phase 3: Frontend Core Grid (Days 4-5)

1. Install `react-data-grid`: `npm install react-data-grid`
2. Build `BudgetDataGrid` component with frozen columns
3. Implement `MonthCell` renderer (color coding, tooltips)
4. Implement `MonthCellEditor` (inline editing, debounced save)
5. Build `TrendSummaryBar` with recharts
6. Wire up API calls (multi-month fetch, optimistic updates)
7. Test locally

### Phase 4: Advanced Features (Days 6-7)

1. Implement copy/paste handler
2. Build template dialog (save/load/apply)
3. Build scenario comparison view
4. Add mobile responsive layout
5. Build budget report page
6. Add notifications UI (bell icon, alerts list)
7. CSV export button

### Phase 5: Testing & Polish (Day 8)

1. Write frontend integration tests
2. Manual QA: test all editing flows, copy/paste, templates, scenarios
3. Performance test: 50 categories × 12 months = 600 cells
4. Fix bugs, polish UI
5. Deploy to production

---

## Performance Considerations

1. **Virtualization:** `react-data-grid` virtualizes rows; with 50 categories, only ~20 render at a time
2. **Debounced saves:** 300ms debounce prevents API spam during rapid editing
3. **Optimistic updates:** Grid updates immediately; API calls happen in background
4. **Bulk queries:** Single multi-month query (2 endpoints) vs 12 sequential calls = 6× fewer HTTP requests
5. **Memoization:** Use `useMemo` for calculated rows (subtotals, net savings)
6. **IndexedDB caching:** Consider caching actuals locally for offline viewing (future enhancement)

---

## Edge Cases

1. **Category deleted:** If category deleted, existing budgets remain; grid shows "(Deleted Category)"
2. **Goal deleted:** Linked categories show broken link icon, budget still editable
3. **Concurrent edits:** Last write wins; optimistic updates may revert if backend state changed
4. **Rollover on new month boundary:** Cron job calculates rollover at month-end, stores in next month's budget
5. **Scenario adjustments on missing categories:** Skip categories not in base budgets
6. **CSV export with 0 budgets:** Export empty grid with category names only
7. **Mobile landscape mode:** Show 3-month view instead of 1 on wider mobile screens

---

## Security Considerations

1. **Workspace isolation:** All queries filter by `workspace_id` from auth context
2. **User permissions:** Only writable workspace members can edit budgets (existing `canWrite` check)
3. **Template ownership:** Users can only load templates from their workspace
4. **Scenario isolation:** Scenarios scoped to workspace, not shared across users
5. **CSV export rate limit:** Add rate limit (10 exports/hour) to prevent abuse

---

## Rollout Plan

1. **Feature flag:** Add `BUDGET_SPREADSHEET_ENABLED` env var, default false
2. **Beta users:** Enable for select workspaces, gather feedback
3. **Iterate:** Fix bugs, polish UX based on feedback
4. **General availability:** Enable for all users after 2 weeks of beta
5. **Deprecation:** Keep old single-month view for 1 release cycle, then remove

---

## Success Metrics

1. **Adoption:** % of active users who use budget spreadsheet view
2. **Engagement:** Average time spent on budgets page (expect 2× increase)
3. **Edits per session:** Track number of budget edits per visit
4. **Template usage:** % of users who create/apply templates
5. **Scenario usage:** % of users who create scenarios
6. **Mobile usage:** % of budget edits on mobile devices
7. **NPS:** Survey users after 30 days of use

---

## Future Enhancements (Phase 2+)

1. **Budget rules engine:** Auto-create budgets based on historical spending averages
2. **Forecasting:** ML-based spending predictions per category
3. **Collaborative budgeting:** Multiple workspace members edit simultaneously with CRDT sync
4. **Budget approval workflow:** Request approval for budget increases
5. **Integration with goals:** Auto-adjust category budgets to hit goal targets
6. **Recurring budget patterns:** Seasonal budgets (higher grocery spend in Dec)
7. **Budget alerts via email/SMS:** Not just in-app notifications
8. **Budget gamification:** Badges for staying under budget, streaks
9. **Budget comparison with peers:** Anonymous aggregate data (opt-in)
10. **Voice input:** "Add $100 to dining budget for October"

---

## Open Questions

1. **Rollover reset:** Should rollover reset annually, or carry forward indefinitely?
   - **Decision:** Carry forward indefinitely; user can manually adjust if needed
2. **Negative rollover:** If overspend, should deficit carry forward (reduce next month's budget)?
   - **Decision:** Yes, show as negative rollover; user can override
3. **Template conflicts:** If applying template to months with existing budgets, overwrite or skip?
   - **Decision:** Skip existing; show warning "X budgets already exist"
4. **Scenario comparison limit:** Max 2 scenarios compared at once, or unlimited?
   - **Decision:** Start with 2-way comparison; add N-way in phase 2
5. **Mobile swipe direction:** Swipe left = next month or previous month?
   - **Decision:** Swipe right = previous, swipe left = next (matches calendar apps)

---

## Documentation Updates

1. **User guide:** Add "Budget Spreadsheet" section to docs
2. **API docs:** Document new endpoints in OpenAPI spec
3. **Changelog:** Add to release notes for next version
4. **Video tutorial:** Record 3-minute walkthrough for YouTube/docs site
5. **Blog post:** Announce feature with screenshots and use cases

---

## Spec Review Checklist

- [x] All 17 core features covered
- [x] Scenarios feature specified
- [x] Database schema changes documented
- [x] API endpoints designed
- [x] Frontend components outlined
- [x] Copy/paste behavior defined
- [x] Mobile responsive approach
- [x] Testing strategy
- [x] Migration plan
- [x] Performance considerations
- [x] Security review
- [x] Edge cases identified
- [x] Success metrics defined

---

**End of Design Document**

Ready for user review before proceeding to implementation plan.
