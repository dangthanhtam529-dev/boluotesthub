import { createFileRoute } from "@tanstack/react-router"
import { useState, useEffect } from "react"
import { useNavigate } from "@tanstack/react-router"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { toast } from "sonner"
import { apiGet, apiPost } from "@/lib/api"
import {
  BarChart3,
  CheckCircle,
  XCircle,
  Clock,
  Play,
  RefreshCw,
  FileText,
  ChevronRight,
  Loader2,
} from "lucide-react"

interface ApifoxProjectInfo {
  id: number
  name: string
  description: string | null
  type: string
  member_count: number
  api_count: number
}

interface TestItem {
  id: string
  name: string
  type: "test-suite" | "test-scenario"
  description: string | null
  folder: string | null
  execution_count: number
  is_saved: boolean
  local_id: string | null
}

interface Execution {
  id: string
  apifox_collection_id: string
  collection_name: string
  collection_type: string | null
  status: string
  total_cases: number | null
  passed_cases: number | null
  failed_cases: number | null
  skipped_cases: number | null
  duration: number | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  environment: string | null
  has_mongodb_report: boolean
}

interface ProjectDetail {
  id: string
  name: string
  description: string | null
  apifox_project_id: string | null
  owner_id: string
  is_active: boolean
  last_sync_at: string | null
  created_at: string | null
  collection_count: number
  execution_count: number
}

interface ProjectStats {
  total_executions: number
  total_passed: number
  total_failed: number
  pass_rate: number
  avg_duration: number
}

interface TrendData {
  _id: string
  count: number
  avg_response_time: number | null
  avg_failed: number | null
}

function ProjectDetailPage() {
  const projectId = Route.useParams().projectId
  const navigate = useNavigate()
  
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [apifoxInfo, setApifoxInfo] = useState<ApifoxProjectInfo | null>(null)
  const [testSuites, setTestSuites] = useState<TestItem[]>([])
  const [testScenarios, setTestScenarios] = useState<TestItem[]>([])
  const [executions, setExecutions] = useState<Execution[]>([])
  const [stats, setStats] = useState<ProjectStats | null>(null)
  const [trendData, setTrendData] = useState<TrendData[]>([])
  
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncToken, setSyncToken] = useState("")
  const [executingItem, setExecutingItem] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"suites" | "scenarios" | "history">("suites")
  
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState<TestItem | null>(null)
  const [itemExecutions, setItemExecutions] = useState<Execution[]>([])
  const [loadingItemDetail, setLoadingItemDetail] = useState(false)
  
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false)
  const [settingsForm, setSettingsForm] = useState({
    name: "",
    description: "",
    apifox_project_id: "",
  })
  const [savingSettings, setSavingSettings] = useState(false)

  const loadProject = async () => {
    try {
      setLoading(true)
      const res = await apiGet<ProjectDetail>(`/api/v1/projects/${projectId}`)
      setProject(res)
      if (res) {
        setSettingsForm({
          name: res.name || "",
          description: res.description || "",
          apifox_project_id: res.apifox_project_id || "",
        })
      }
    } catch (e: any) {
      toast.error(e.message || "加载项目失败")
      setProject(null)
    } finally {
      setLoading(false)
    }
  }

  const loadExecutions = async () => {
    try {
      const res = await apiGet<{ data: Execution[], count: number }>(
        `/api/v1/executions/?project_id=${projectId}&limit=10`
      )
      setExecutions(res.data || [])
      
      if (res.data && res.data.length > 0) {
        const totalExecutions = res.data.length
        const totalPassed = res.data.filter((e: Execution) => e.status === "completed").length
        const totalFailed = res.data.filter((e: Execution) => e.status === "failed").length
        const totalCases = res.data.reduce((sum: number, e: Execution) => sum + (e.total_cases || 0), 0)
        const passedCases = res.data.reduce((sum: number, e: Execution) => sum + (e.passed_cases || 0), 0)
        const avgDuration = res.data.reduce((sum: number, e: Execution) => sum + (e.duration || 0), 0) / totalExecutions
        
        setStats({
          total_executions: totalExecutions,
          total_passed: totalPassed,
          total_failed: totalFailed,
          pass_rate: totalCases > 0 ? Math.round((passedCases / totalCases) * 100) : 0,
          avg_duration: avgDuration,
        })
      }
    } catch (e: any) {
      console.error("加载执行历史失败:", e)
    }
  }

  const loadTrendData = async () => {
    try {
      const res = await apiGet<{ data: TrendData[] }>(
        `/api/v1/executions/analytics/trend?project_id=${projectId}&days=7`
      )
      setTrendData(res.data || [])
    } catch (e: any) {
      console.error("加载趋势数据失败:", e)
    }
  }

  useEffect(() => {
    loadProject()
  }, [projectId])

  useEffect(() => {
    if (project?.apifox_project_id) {
      loadExecutions()
      loadTrendData()
    }
  }, [project?.apifox_project_id])

  const handleSync = async () => {
    if (!project?.apifox_project_id) {
      toast.error("项目未关联 Apifox 项目")
      return
    }
    setSyncToken("")
    setSyncDialogOpen(true)
  }

  const doSync = async () => {
    try {
      setSyncing(true)
      const tokenQuery = syncToken ? `?access_token=${encodeURIComponent(syncToken)}` : ""
      
      const [infoRes, collectionsRes] = await Promise.all([
        apiGet<{ data: ApifoxProjectInfo }>(
          `/api/v1/projects/${projectId}/apifox-info${tokenQuery}`
        ),
        apiGet<{ data: TestItem[] }>(
          `/api/v1/projects/${projectId}/apifox-collections${tokenQuery}`
        ),
      ])
      
      setApifoxInfo(infoRes.data || null)
      const allItems = collectionsRes.data || []
      
      const mappedItems = allItems.map((item: any) => ({
        ...item,
        is_saved: item.is_synced || item.is_saved || false,
      }))
      
      const suites = mappedItems.filter((item: TestItem) => item.type === "test-suite")
      const scenarios = mappedItems.filter((item: TestItem) => item.type === "test-scenario")
      
      setTestSuites(suites)
      setTestScenarios(scenarios)
      
      toast.success(`同步成功：${suites.length} 个测试套件，${scenarios.length} 个测试场景`)
      setSyncDialogOpen(false)
      loadExecutions()
    } catch (e: any) {
      toast.error(e.message || "同步失败")
    } finally {
      setSyncing(false)
    }
  }

  const saveItem = async (item: TestItem) => {
    if (item.is_saved) return
    
    try {
      const tokenQuery = syncToken ? `?access_token=${encodeURIComponent(syncToken)}` : ""
      await apiPost(
        `/api/v1/projects/${projectId}/collections${tokenQuery}`,
        {
          project_id: projectId,
          name: item.name,
          apifox_collection_id: item.id,
          collection_type: item.type,
          description: item.description,
        }
      )
      toast.success(`已保存: ${item.name}`)
      
      if (item.type === "test-suite") {
        setTestSuites(prev => prev.map(s => 
          s.id === item.id ? { ...s, is_saved: true } : s
        ))
      } else {
        setTestScenarios(prev => prev.map(s => 
          s.id === item.id ? { ...s, is_saved: true } : s
        ))
      }
    } catch (e: any) {
      toast.error(e.message || "保存失败")
    }
  }

  const executeItem = async (item: TestItem) => {
    try {
      setExecutingItem(item.id)
      
      await apiPost<{ execution_id: string }>(
        `/api/v1/executions/run`,
        {
          project_id: projectId,
          collection_id: item.id,
          collection_type: item.type,
          access_token: syncToken || undefined,
        }
      )
      
      toast.success(`开始执行: ${item.name}`)
      
      setTimeout(() => {
        loadExecutions()
      }, 2000)
    } catch (e: any) {
      toast.error(e.message || "执行失败")
    } finally {
      setExecutingItem(null)
    }
  }

  const showItemDetail = async (item: TestItem) => {
    setSelectedItem(item)
    setDetailDialogOpen(true)
    setLoadingItemDetail(true)
    
    try {
      const res = await apiGet<{ data: Execution[], count: number }>(
        `/api/v1/executions/?collection_id=${item.id}&limit=10`
      )
      setItemExecutions(res.data || [])
    } catch (e: any) {
      console.error("加载执行详情失败:", e)
      setItemExecutions([])
    } finally {
      setLoadingItemDetail(false)
    }
  }

  const saveSettings = async () => {
    try {
      setSavingSettings(true)
      const res = await fetch(`/api/v1/projects/${projectId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(settingsForm),
      })
      
      if (res.ok) {
        toast.success("设置已保存")
        setSettingsDialogOpen(false)
        loadProject()
      } else {
        const err = await res.json()
        toast.error(err.detail || "保存失败")
      }
    } catch (e: any) {
      toast.error(e.message || "保存失败")
    } finally {
      setSavingSettings(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      completed: "bg-green-50 text-green-700",
      failed: "bg-red-50 text-red-700",
      running: "bg-primary/10 text-primary",
      pending: "bg-muted text-foreground",
    }
    const labels: Record<string, string> = {
      completed: "已完成",
      failed: "失败",
      running: "执行中",
      pending: "等待中",
    }
    return (
      <Badge className={styles[status] || styles.pending}>
        {labels[status] || status}
      </Badge>
    )
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "-"
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const mins = Math.floor(seconds / 60)
    const secs = (seconds % 60).toFixed(0)
    return `${mins}m ${secs}s`
  }

  const renderTestItem = (item: TestItem) => (
    <div
      key={item.id}
      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 cursor-pointer"
      onClick={() => showItemDetail(item)}
    >
      <div className="flex items-center gap-3">
        <span className="text-xl">
          {item.type === "test-suite" ? "📁" : "🎬"}
        </span>
        <div>
          <div className="font-medium">{item.name}</div>
          <div className="text-sm text-muted-foreground">
            <Badge variant="outline" className="mr-2">
              {item.type === "test-suite" ? "测试套件" : "测试场景"}
            </Badge>
            ID: {item.id}
            {item.folder && <span className="ml-2">· {item.folder}</span>}
          </div>
          {item.description && (
            <div className="text-xs text-muted-foreground mt-1">{item.description}</div>
          )}
        </div>
      </div>
      <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
        {item.is_saved ? (
          <Badge className="bg-green-50 text-green-700">已保存</Badge>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={() => saveItem(item)}
          >
            保存
          </Button>
        )}
        <Button
          size="sm"
          onClick={() => executeItem(item)}
          disabled={executingItem === item.id}
        >
          {executingItem === item.id ? (
            <>
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
              执行中
            </>
          ) : (
            <>
              <Play className="w-4 h-4 mr-1" />
              执行
            </>
          )}
        </Button>
        <Button variant="ghost" size="sm">
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  )

  const renderExecutionItem = (execution: Execution, compact: boolean = false) => (
    <div
      key={execution.id}
      className={`flex items-center justify-between ${compact ? 'p-3' : 'p-4'} border rounded-lg hover:bg-muted/50 cursor-pointer`}
      onClick={() => navigate({ to: "/reports", search: { execution_id: execution.id } })}
    >
      <div className="flex items-center gap-3">
        {execution.status === "completed" ? (
          <CheckCircle className="w-5 h-5 text-green-500" />
        ) : execution.status === "failed" ? (
          <XCircle className="w-5 h-5 text-red-500" />
        ) : execution.status === "running" ? (
          <Loader2 className="w-5 h-5 text-primary animate-spin" />
        ) : (
          <Clock className="w-5 h-5 text-muted-foreground" />
        )}
        <div>
          <div className="font-medium">
            {execution.collection_name || `集合 ${execution.apifox_collection_id}`}
          </div>
          <div className="text-sm text-muted-foreground">
            {new Date(execution.created_at).toLocaleString("zh-CN")}
            {execution.environment && (
              <span className="ml-2">· 环境: {execution.environment}</span>
            )}
            {execution.duration && (
              <span className="ml-2">· 耗时 {formatDuration(execution.duration)}</span>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-4">
        {!compact && (
          <div className="text-right text-sm">
            {execution.total_cases !== null && (
              <>
                <div className="font-medium">
                  {execution.passed_cases || 0}/{execution.total_cases} 通过
                </div>
                {execution.failed_cases && execution.failed_cases > 0 && (
                  <div className="text-red-500">{execution.failed_cases} 失败</div>
                )}
              </>
            )}
          </div>
        )}
        {getStatusBadge(execution.status)}
        {execution.has_mongodb_report && (
          <span title="有详细报告">
            <FileText className="w-4 h-4 text-primary" />
          </span>
        )}
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">项目不存在</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          {project.description && (
            <p className="text-muted-foreground mt-1">{project.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate({ to: "/projects" })}>
            返回列表
          </Button>
          <Button variant="outline" onClick={() => setSettingsDialogOpen(true)}>
            ⚙️ 设置
          </Button>
          {project.apifox_project_id && (
            <Button onClick={handleSync} disabled={syncing}>
              {syncing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  同步中...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  同步测试套件/场景
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {project.apifox_project_id && apifoxInfo && (
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="py-4">
            <div className="flex items-center gap-4">
              <div className="text-primary text-2xl">📦</div>
              <div>
                <div className="font-medium text-foreground">
                  Apifox 项目: {apifoxInfo.name}
                </div>
                <div className="text-sm text-primary/80">
                  ID: {apifoxInfo.id}
                  {apifoxInfo.api_count && ` · API 数量: ${apifoxInfo.api_count}`}
                  {apifoxInfo.member_count && ` · 成员: ${apifoxInfo.member_count}`}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">测试套件</p>
                <p className="text-2xl font-bold">{testSuites.length}</p>
              </div>
              <div className="p-2 bg-primary/5 rounded-lg">
                <span className="text-xl">📁</span>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">测试场景</p>
                <p className="text-2xl font-bold">{testScenarios.length}</p>
              </div>
              <div className="p-2 bg-accent rounded-lg">
                <span className="text-xl">🎬</span>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">执行次数</p>
                <p className="text-2xl font-bold">{stats?.total_executions || 0}</p>
              </div>
              <div className="p-2 bg-chart-2/10 rounded-lg">
                <BarChart3 className="w-5 h-5 text-chart-2" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">通过率</p>
                <p className="text-2xl font-bold">{stats?.pass_rate || 0}%</p>
              </div>
              <div className="p-2 bg-emerald-50/60 rounded-lg">
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">平均耗时</p>
                <p className="text-2xl font-bold">{formatDuration(stats?.avg_duration || 0)}</p>
              </div>
              <div className="p-2 bg-amber-50/60 rounded-lg">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {trendData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">最近7天执行趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 h-32">
              {trendData.map((item) => {
                const maxCount = Math.max(...trendData.map(d => d.count), 1)
                const height = (item.count / maxCount) * 100
                return (
                  <div key={item._id} className="flex-1 flex flex-col items-center">
                    <div
                      className="w-full bg-primary rounded-t"
                      style={{ height: `${height}%`, minHeight: item.count > 0 ? '4px' : '0' }}
                    />
                    <div className="text-xs text-muted-foreground mt-1">{item.count}</div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex gap-4">
            <Button
              variant={activeTab === "suites" ? "default" : "ghost"}
              onClick={() => setActiveTab("suites")}
            >
              测试套件 ({testSuites.length})
            </Button>
            <Button
              variant={activeTab === "scenarios" ? "default" : "ghost"}
              onClick={() => setActiveTab("scenarios")}
            >
              测试场景 ({testScenarios.length})
            </Button>
            <Button
              variant={activeTab === "history" ? "default" : "ghost"}
              onClick={() => setActiveTab("history")}
            >
              执行历史 ({executions.length})
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {activeTab === "suites" && (
            <div className="space-y-3">
              {testSuites.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无测试套件，点击"同步测试套件/场景"从 Apifox 获取
                </div>
              ) : (
                testSuites.map(renderTestItem)
              )}
            </div>
          )}
          {activeTab === "scenarios" && (
            <div className="space-y-3">
              {testScenarios.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无测试场景，点击"同步测试套件/场景"从 Apifox 获取
                </div>
              ) : (
                testScenarios.map(renderTestItem)
              )}
            </div>
          )}
          {activeTab === "history" && (
            <div className="space-y-3">
              {executions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无执行记录
                </div>
              ) : (
                executions.map((e) => renderExecutionItem(e))
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>同步 Apifox 测试套件/场景</DialogTitle>
            <DialogDescription>
              从 Apifox 项目同步测试套件和测试场景数据
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="sync-token">Apifox Access Token</Label>
              <Input
                id="sync-token"
                type="password"
                value={syncToken}
                onChange={(e) => setSyncToken(e.target.value)}
                placeholder="留空则使用系统配置的令牌"
              />
              <p className="text-xs text-muted-foreground">
                在 Apifox 网站生成：账号设置 → API 访问令牌
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={doSync} disabled={syncing}>
              {syncing ? "同步中..." : "开始同步"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {selectedItem?.type === "test-suite" ? "📁 " : "🎬 "}
              {selectedItem?.name}
            </DialogTitle>
            <DialogDescription>
              {selectedItem?.description || "暂无描述"}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">类型：</span>
                <Badge variant="outline" className="ml-2">
                  {selectedItem?.type === "test-suite" ? "测试套件" : "测试场景"}
                </Badge>
              </div>
              <div>
                <span className="text-muted-foreground">ID：</span>
                <span className="ml-2 font-mono">{selectedItem?.id}</span>
              </div>
              {selectedItem?.folder && (
                <div className="col-span-2">
                  <span className="text-muted-foreground">所属文件夹：</span>
                  <span className="ml-2">{selectedItem.folder}</span>
                </div>
              )}
            </div>
            
            <Separator />
            
            <div>
              <h4 className="font-medium mb-3">最近执行记录</h4>
              {loadingItemDetail ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : itemExecutions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无执行记录
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {itemExecutions.map((e) => renderExecutionItem(e, true))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailDialogOpen(false)}>
              关闭
            </Button>
            {selectedItem && !selectedItem.is_saved && (
              <Button onClick={() => { saveItem(selectedItem); setDetailDialogOpen(false); }}>
                保存到项目
              </Button>
            )}
            {selectedItem && (
              <Button onClick={() => { executeItem(selectedItem); setDetailDialogOpen(false); }}>
                <Play className="w-4 h-4 mr-1" />
                执行
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={settingsDialogOpen} onOpenChange={setSettingsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>项目设置</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="settings-name">项目名称</Label>
              <Input
                id="settings-name"
                value={settingsForm.name}
                onChange={(e) => setSettingsForm({ ...settingsForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="settings-description">项目描述</Label>
              <Input
                id="settings-description"
                value={settingsForm.description}
                onChange={(e) => setSettingsForm({ ...settingsForm, description: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="settings-apifox">Apifox 项目 ID</Label>
              <Input
                id="settings-apifox"
                value={settingsForm.apifox_project_id}
                onChange={(e) => setSettingsForm({ ...settingsForm, apifox_project_id: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSettingsDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={saveSettings} disabled={savingSettings}>
              {savingSettings ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute("/_layout/projects/$projectId")({
  component: ProjectDetailPage,
})
