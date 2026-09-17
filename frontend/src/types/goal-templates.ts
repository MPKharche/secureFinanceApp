export interface GoalTemplate {
  type: string
  name: string
  description: string
  icon: string
  color: string
  priority: number
}

// Extend existing Goal type with new fields
export interface GoalWithTemplate extends Goal {
  priority?: number | null
  template_type?: string | null
}
