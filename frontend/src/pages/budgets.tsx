import React, { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { budgets as budgetsApi, categories as categoriesApi, goals as goalsApi } from '@/lib/api'
import { PageHeader } from '@/components/page-header'
import { useAuth } from '@/contexts/auth-context'
import { useWorkspace } from '@/contexts/workspace-context'
import { addMonths, subMonths, startOfMonth, format } from 'date-fns'
import { toast } from 'sonner'
import type { Budget, Category, Goal } from '@/types'

interface BudgetGridRow {
  id: string
  type: 'category' | 'subtotal' | 'total' | 'section-header'
  categoryId?: string
  categoryName: string
  categoryType?: 'income' | 'expense' | 'investment'
  categoryIcon?: string
  categoryColor?: string
  enableRollover?: boolean
  linkedGoalId?: string
  isRecurring?: boolean
  months: Record<string, {
    budget: number | null
    budgetId?: string
    actual: number | null
    rollover?: number
    projected?: number
    isEditable: boolean
  }>
}

export default function BudgetSpreadsheetPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { canWrite } = useWorkspace()
  const queryClient = useQueryClient()
  
  // State: current center month for 12-month range
  const [selectedMonth, setSelectedMonth] = useState<Date>(startOfMonth(new Date()))
  
  // Calculate 12-month range: -5 months to +6 months
  const startMonth = useMemo(() => subMonths(selectedMonth, 5), [selectedMonth])
  const endMonth = useMemo(() => addMonths(selectedMonth, 6), [selectedMonth])
  
  const startMonthStr = format(startMonth, 'yyyy-MM-dd')
  const endMonthStr = format(endMonth, 'yyyy-MM-dd')
  
  // Fetch data in parallel
  const { data: budgetsList, isLoading: budgetsLoading } = useQuery({
    queryKey: ['budgets', 'multi-month', startMonthStr, endMonthStr],
    queryFn: () => budgetsApi.multiMonth(startMonthStr, endMonthStr),
  })
  
  const { data: actualsData, isLoading: actualsLoading } = useQuery({
    queryKey: ['budgets', 'actuals', startMonthStr, endMonthStr],
    queryFn: () => budgetsApi.actuals(startMonthStr, endMonthStr),
  })
  
  const { data: categoriesList, isLoading: categoriesLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
  })
  
  const { data: goalsList } = useQuery({
    queryKey: ['goals'],
    queryFn: goalsApi.list,
  })
  
  const isLoading = budgetsLoading || actualsLoading || categoriesLoading
  
  // Build rows structure
  const rows = useMemo<BudgetGridRow[]>(() => {
    if (!categoriesList || !budgetsList || !actualsData) return []
    
    // Generate month keys
    const monthKeys: string[] = []
    let current = startMonth
    while (current <= endMonth) {
      monthKeys.push(format(current, 'yyyy-MM'))
      current = addMonths(current, 1)
    }
    
    // Group categories by type
    const incomeCategories = categoriesList.filter((c: Category) => c.category_type === 'income')
    const expenseCategories = categoriesList.filter((c: Category) => c.category_type === 'expense')
    const investmentCategories = categoriesList.filter((c: Category) => c.category_type === 'investment')
    
    // Build budget map: category_id -> month -> budget
    const budgetMap: Record<string, Record<string, { amount: number, budgetId: string, isRecurring: boolean }>> = {}
    budgetsList.forEach((b: Budget) => {
      const catId = b.category_id
      const monthKey = format(new Date(b.month), 'yyyy-MM')
      if (!budgetMap[catId]) budgetMap[catId] = {}
      budgetMap[catId][monthKey] = { amount: b.amount, budgetId: b.id, isRecurring: b.is_recurring }
    })
    
    // Build category rows helper
    const buildCategoryRow = (cat: Category): BudgetGridRow => {
      const catId = cat.id
      const months: Record<string, any> = {}
      
      monthKeys.forEach(monthKey => {
        const monthDate = new Date(monthKey + '-01')
        const isPast = monthDate < startOfMonth(new Date())
        const budgetEntry = budgetMap[catId]?.[monthKey]
        const actualAmount = actualsData.category_actuals[catId]?.[monthKey] ?? null
        
        months[monthKey] = {
          budget: budgetEntry?.amount ?? null,
          budgetId: budgetEntry?.budgetId,
          actual: actualAmount,
          rollover: 0, // TODO: Calculate rollover
          projected: null, // TODO: Calculate projected
          isEditable: !isPast && canWrite,
        }
      })
      
      return {
        id: catId,
        type: 'category',
        categoryId: catId,
        categoryName: cat.name,
        categoryType: cat.category_type as 'income' | 'expense' | 'investment',
        categoryIcon: cat.icon,
        categoryColor: cat.color,
        enableRollover: cat.enable_rollover,
        linkedGoalId: goalsList?.find((g: Goal) => g.linked_category_ids?.includes(catId))?.id,
        isRecurring: budgetMap[catId]?.[monthKeys[0]]?.isRecurring ?? false,
        months,
      }
    }
    
    // Build subtotal row helper
    const buildSubtotalRow = (id: string, name: string, categoryRows: BudgetGridRow[]): BudgetGridRow => {
      const months: Record<string, any> = {}
      monthKeys.forEach(monthKey => {
        const budgetSum = categoryRows.reduce((sum, row) => sum + (row.months[monthKey]?.budget ?? 0), 0)
        const actualSum = categoryRows.reduce((sum, row) => sum + (row.months[monthKey]?.actual ?? 0), 0)
        months[monthKey] = {
          budget: budgetSum,
          budgetId: undefined,
          actual: actualSum,
          rollover: 0,
          projected: null,
          isEditable: false,
        }
      })
      
      return { id, type: 'subtotal', categoryName: name, months }
    }
    
    // Assemble rows
    const allRows: BudgetGridRow[] = []
    
    // Income section
    if (incomeCategories.length > 0) {
      allRows.push({ id: 'income-header', type: 'section-header', categoryName: 'INCOME', months: {} })
      const incomeRows = incomeCategories.map(buildCategoryRow)
      allRows.push(...incomeRows)
      allRows.push(buildSubtotalRow('income-subtotal', 'Income Subtotal', incomeRows))
    }
    
    // Expenses section
    if (expenseCategories.length > 0) {
      allRows.push({ id: 'expenses-header', type: 'section-header', categoryName: 'EXPENSES', months: {} })
      const expenseRows = expenseCategories.map(buildCategoryRow)
      allRows.push(...expenseRows)
      allRows.push(buildSubtotalRow('expenses-subtotal', 'Expenses Subtotal', expenseRows))
    }
    
    // Investments section
    if (investmentCategories.length > 0) {
      allRows.push({ id: 'investments-header', type: 'section-header', categoryName: 'INVESTMENTS', months: {} })
      const investmentRows = investmentCategories.map(buildCategoryRow)
      allRows.push(...investmentRows)
      allRows.push(buildSubtotalRow('investments-subtotal', 'Investments Subtotal', investmentRows))
    }
    
    // Net Savings total row
    const netSavingsMonths: Record<string, any> = {}
    monthKeys.forEach(monthKey => {
      const income = allRows.find(r => r.id === 'income-subtotal')?.months[monthKey]?.budget ?? 0
      const expenses = allRows.find(r => r.id === 'expenses-subtotal')?.months[monthKey]?.budget ?? 0
      const investments = allRows.find(r => r.id === 'investments-subtotal')?.months[monthKey]?.budget ?? 0
      netSavingsMonths[monthKey] = {
        budget: income - expenses - investments,
        actual: null,
        isEditable: false,
      }
    })
    allRows.push({ id: 'net-savings', type: 'total', categoryName: 'NET SAVINGS', months: netSavingsMonths })
    
    return allRows
  }, [categoriesList, budgetsList, actualsData, goalsList, startMonth, endMonth, canWrite])
  
  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }
  
  // Generate month keys for columns
  const monthKeys = useMemo(() => {
    const keys: string[] = []
    let current = startMonth
    while (current <= endMonth) {
      keys.push(format(current, 'yyyy-MM'))
      current = addMonths(current, 1)
    }
    return keys
  }, [startMonth, endMonth])
  
  // Update budget mutation
  const updateBudgetMutation = useMutation({
    mutationFn: async ({ budgetId, amount, applyToFuture, categoryId, month }: { budgetId?: string, amount: number, applyToFuture: boolean, categoryId: string, month: string }) => {
      if (budgetId) {
        return budgetsApi.update(budgetId, { amount, apply_to_future: applyToFuture })
      } else {
        return budgetsApi.create({
          category_id: categoryId,
          amount,
          month: month + '-01',
          is_recurring: false
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      toast.success('Budget updated')
    },
    onError: () => {
      toast.error('Failed to update budget')
    }
  })
  
  const handleCellEdit = (row: BudgetGridRow, monthKey: string, newValue: string) => {
    if (row.type !== 'category' || !row.categoryId) return
    
    const amount = parseFloat(newValue)
    if (isNaN(amount)) return
    
    const cellData = row.months[monthKey]
    updateBudgetMutation.mutate({
      budgetId: cellData.budgetId,
      amount,
      applyToFuture: false,
      categoryId: row.categoryId,
      month: monthKey
    })
  }
  
  return (
    <div className="space-y-6">
      <PageHeader
        section={t('budgets.title')}
        title="12-Month Budget Spreadsheet"
      />
      
      <div className="text-sm text-muted-foreground">
        Showing {format(startMonth, 'MMM yyyy')} - {format(endMonth, 'MMM yyyy')}
      </div>
      
      {/* Simple table-based grid */}
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 sticky top-0">
            <tr>
              <th className="px-4 py-2 text-left font-semibold border-r sticky left-0 bg-muted/50 z-10">Category</th>
              {monthKeys.map(month => (
                <th key={month} className="px-4 py-2 text-center font-semibold border-r min-w-[120px]">
                  {format(new Date(month + '-01'), 'MMM yyyy')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(row => {
              if (row.type === 'section-header') {
                return (
                  <tr key={row.id} className="bg-primary/10">
                    <td colSpan={monthKeys.length + 1} className="px-4 py-2 font-bold">
                      {row.categoryName}
                    </td>
                  </tr>
                )
              }
              
              if (row.type === 'subtotal' || row.type === 'total') {
                return (
                  <tr key={row.id} className="bg-muted font-semibold border-t-2">
                    <td className="px-4 py-2 sticky left-0 bg-muted z-10">{row.categoryName}</td>
                    {monthKeys.map(month => (
                      <td key={month} className="px-4 py-2 text-right border-r">
                        {row.months[month]?.budget?.toFixed(2) ?? '-'}
                      </td>
                    ))}
                  </tr>
                )
              }
              
              return (
                <tr key={row.id} className="border-b hover:bg-muted/30">
                  <td className="px-4 py-2 sticky left-0 bg-background z-10 border-r">
                    <div className="flex items-center gap-2">
                      <span className="w-4 h-4 rounded" style={{ backgroundColor: row.categoryColor }}></span>
                      {row.categoryName}
                    </div>
                  </td>
                  {monthKeys.map(month => {
                    const cellData = row.months[month]
                    const isPast = new Date(month + '-01') < startOfMonth(new Date())
                    const displayValue = isPast ? cellData?.actual : cellData?.budget
                    
                    return (
                      <td key={month} className="px-4 py-2 text-right border-r">
                        {cellData?.isEditable ? (
                          <input
                            type="number"
                            step="0.01"
                            defaultValue={displayValue ?? ''}
                            onBlur={(e) => handleCellEdit(row, month, e.target.value)}
                            className="w-full text-right border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary"
                          />
                        ) : (
                          <span className={isPast && cellData?.actual ? 'text-muted-foreground' : ''}>
                            {displayValue?.toFixed(2) ?? '-'}
                          </span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      
      <div className="text-xs text-muted-foreground">
        {rows.length} categories loaded. Click on future month cells to edit budgets.
      </div>
    </div>
  )
}
