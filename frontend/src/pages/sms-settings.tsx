import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { sms } from '@/lib/api'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import {
  Settings,
  Smartphone,
  Download,
  Copy,
  CheckCircle2,
  AlertCircle,
  BarChart3,
  RefreshCw,
  Key,
} from 'lucide-react'

export default function SMSSettingsPage() {
  const [apiToken, setApiToken] = useState<string | null>(null)
  const [showToken, setShowToken] = useState(false)
  const [copied, setCopied] = useState(false)

  // Fetch SMS stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['sms', 'stats'],
    queryFn: sms.stats,
    refetchInterval: 60000, // Refresh every minute
  })

  // Generate API token mutation (placeholder - backend endpoint needed)
  const generateTokenMutation = useMutation({
    mutationFn: async () => {
      // This would call a backend endpoint to generate a new API token
      // For now, return a mock token
      return { token: 'sms_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15) }
    },
    onSuccess: (data) => {
      setApiToken(data.token)
      setShowToken(true)
      toast.success('API token generated successfully')
    },
    onError: () => {
      toast.error('Failed to generate API token')
    },
  })

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('Copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  const serverUrl = window.location.origin

  return (
    <div className="space-y-6 pb-16">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight flex items-center gap-2 mb-2">
          <Settings className="size-6" />
          SMS Auto-Capture Settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Configure SMS transaction capture for your Android device
        </p>
      </div>

      {/* Stats Dashboard */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="size-5" />
            SMS Capture Statistics
          </CardTitle>
          <CardDescription>Overview of SMS auto-capture activity</CardDescription>
        </CardHeader>
        <CardContent>
          {statsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <StatCard
                  label="Total SMS Captured"
                  value={stats?.total_captured || 0}
                  icon={<Smartphone className="size-4" />}
                  color="text-blue-600 dark:text-blue-400"
                />
                <StatCard
                  label="Auto-Created Transactions"
                  value={stats?.auto_created || 0}
                  icon={<CheckCircle2 className="size-4" />}
                  color="text-green-600 dark:text-green-400"
                />
                <StatCard
                  label="Needs Review"
                  value={stats?.needs_review || 0}
                  icon={<AlertCircle className="size-4" />}
                  color="text-amber-600 dark:text-amber-400"
                />
              </div>

              <Separator className="my-4" />

              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">Last 30 Days</h4>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold">{stats?.last_30_days?.captured || 0}</p>
                    <p className="text-xs text-muted-foreground">Captured</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats?.last_30_days?.created || 0}</p>
                    <p className="text-xs text-muted-foreground">Created</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats?.last_30_days?.reviewed || 0}</p>
                    <p className="text-xs text-muted-foreground">Reviewed</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* API Token */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="size-5" />
            API Token
          </CardTitle>
          <CardDescription>Generate an API token for your Android app</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!apiToken && !showToken ? (
            <>
              <Alert>
                <AlertCircle className="size-4" />
                <AlertTitle>No Active Token</AlertTitle>
                <AlertDescription>
                  You need to generate an API token to allow your Android app to send SMS data securely.
                </AlertDescription>
              </Alert>
              <Button onClick={() => generateTokenMutation.mutate()} disabled={generateTokenMutation.isPending}>
                {generateTokenMutation.isPending ? (
                  <>
                    <RefreshCw className="size-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Key className="size-4" />
                    Generate API Token
                  </>
                )}
              </Button>
            </>
          ) : (
            <div className="space-y-3">
              <Alert variant="warning">
                <AlertCircle className="size-4" />
                <AlertTitle>Save This Token</AlertTitle>
                <AlertDescription>
                  Copy this token now. You won't be able to see it again. If you lose it, you'll need to generate a new
                  one.
                </AlertDescription>
              </Alert>
              <div className="flex items-center gap-2">
                <Input
                  type="text"
                  value={apiToken || '••••••••••••••••••••'}
                  readOnly
                  className="font-mono text-sm"
                />
                <Button
                  size="icon"
                  variant="outline"
                  onClick={() => apiToken && copyToClipboard(apiToken)}
                  title="Copy to clipboard"
                >
                  {copied ? <CheckCircle2 className="size-4" /> : <Copy className="size-4" />}
                </Button>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => generateTokenMutation.mutate()}
                disabled={generateTokenMutation.isPending}
              >
                <RefreshCw className="size-4" />
                Generate New Token
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Setup Instructions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Smartphone className="size-5" />
            Android App Setup
          </CardTitle>
          <CardDescription>Follow these steps to set up SMS auto-capture on your Android device</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <SetupStep
            number={1}
            title="Download the Android App"
            description="Download and install the Securo SMS Reader app on your Android device"
          >
            <Button variant="outline" className="mt-2" asChild>
              <a href="https://github.com/yourorg/securo-sms-reader/releases/latest" target="_blank" rel="noopener noreferrer">
                <Download className="size-4" />
                Download APK
              </a>
            </Button>
            <p className="text-xs text-muted-foreground mt-2">
              Minimum Android version: 7.0 (API 24) or higher
            </p>
          </SetupStep>

          <Separator />

          <SetupStep
            number={2}
            title="Configure Server URL"
            description="Enter your Securo server URL in the app"
          >
            <div className="flex items-center gap-2 mt-2">
              <Input value={serverUrl} readOnly className="text-sm" />
              <Button size="icon" variant="outline" onClick={() => copyToClipboard(serverUrl)} title="Copy URL">
                {copied ? <CheckCircle2 className="size-4" /> : <Copy className="size-4" />}
              </Button>
            </div>
          </SetupStep>

          <Separator />

          <SetupStep
            number={3}
            title="Add API Token"
            description="Paste the API token you generated above into the app"
          >
            {!apiToken ? (
              <Alert className="mt-2">
                <AlertCircle className="size-4" />
                <AlertDescription className="text-xs">
                  Generate an API token above, then paste it into the Android app.
                </AlertDescription>
              </Alert>
            ) : null}
          </SetupStep>

          <Separator />

          <SetupStep
            number={4}
            title="Grant SMS Permissions"
            description="Allow the app to read SMS messages when prompted"
          >
            <p className="text-xs text-muted-foreground mt-2">
              The app will request READ_SMS and RECEIVE_SMS permissions. These are required to capture bank transaction
              SMS automatically.
            </p>
          </SetupStep>

          <Separator />

          <SetupStep
            number={5}
            title="Test Connection"
            description="Use the 'Test Connection' button in the app to verify setup"
          >
            <Badge variant="outline" className="mt-2">
              <CheckCircle2 className="size-3" />
              Connection successful
            </Badge>
          </SetupStep>

          <Alert className="mt-6">
            <AlertCircle className="size-4" />
            <AlertTitle>Privacy & Security</AlertTitle>
            <AlertDescription className="text-xs space-y-1">
              <p>• SMS data is sent directly to your self-hosted Securo instance</p>
              <p>• Only bank transaction SMS are captured (filtered by sender)</p>
              <p>• Data is encrypted in transit (HTTPS only)</p>
              <p>• No third-party services involved</p>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  )
}

interface StatCardProps {
  label: string
  value: number
  icon: React.ReactNode
  color: string
}

function StatCard({ label, value, icon, color }: StatCardProps) {
  return (
    <div className="bg-muted/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-muted-foreground">{label}</span>
        <div className={color}>{icon}</div>
      </div>
      <p className="text-2xl font-bold">{value.toLocaleString()}</p>
    </div>
  )
}

interface SetupStepProps {
  number: number
  title: string
  description: string
  children?: React.ReactNode
}

function SetupStep({ number, title, description, children }: SetupStepProps) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0">
        <div className="flex items-center justify-center size-8 rounded-full bg-primary text-primary-foreground font-bold text-sm">
          {number}
        </div>
      </div>
      <div className="flex-1 space-y-1">
        <h4 className="font-semibold">{title}</h4>
        <p className="text-sm text-muted-foreground">{description}</p>
        {children}
      </div>
    </div>
  )
}
