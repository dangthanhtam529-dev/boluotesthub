import { createFileRoute } from "@tanstack/react-router"
import {
  BarChart3,
  Calendar,
  CheckCircle,
  Check,
  ChevronRight,
  Copy,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  Trash2,
  XCircle,
  Zap,
} from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"

// 执行记录类型
interface ExecutionRecord {
  id: string
  apifox_collection_id: string
  project_id: string | null
  project_name: string | null
  status: "pending" | "running" | "completed" | "failed"
  total_cases: number | null
  passed_cases: number | null
  failed_cases: number | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  report_json: string | null
}

interface Project {
  id: string
  name: string
  apifox_project_id: string | null
}

// 模拟数据
const mockExecutions: ExecutionRecord[] = [
  {
    id: "1",
    apifox_collection_id: "proj_123456",
    project_name: "用户模块测试",
    status: "completed",
    total_cases: 5,
    passed_cases: 4,
    failed_cases: 1,
    created_at: "2025-02-09T10:00:00",
    started_at: "2025-02-09T10:00:05",
    completed_at: "2025-02-09T10:00:30",
    error_message: null,
    report_json: JSON.stringify({
      details: [
        { name: "登录接口", status: "passed", time: 120 },
        { name: "获取用户信息", status: "passed", time: 80 },
        { name: "更新用户信息", status: "passed", time: 150 },
        { name: "创建订单", status: "failed", time: 200, error: "参数错误" },
        { name: "查询订单", status: "passed", time: 90 },
      ],
    }),
  },
  {
    id: "2",
    apifox_collection_id: "proj_789012",
    project_name: "订单模块测试",
    status: "completed",
    total_cases: 8,
    passed_cases: 8,
    failed_cases: 0,
    created_at: "2025-02-09T09:30:00",
    started_at: "2025-02-09T09:30:02",
    completed_at: "2025-02-09T09:30:45",
    error_message: null,
    report_json: null,
  },
  {
    id: "3",
    apifox_collection_id: "proj_345678",
    project_name: "支付接口测试",
    status: "failed",
    total_cases: 3,
    passed_cases: 1,
    failed_cases: 2,
    created_at: "2025-02-09T08:00:00",
    started_at: "2025-02-09T08:00:03",
    completed_at: "2025-02-09T08:00:20",
    error_message: "连接超时",
    report_json: null,
  },
]

export const Route = createFileRoute("/_layout/executions")({
  component: ExecutionsPage,
  head: () => ({
    meta: [
      {
        title: "测试执行 - 测试管理平台",
      },
    ],
  }),
})

function ExecutionsPage() {
  const [executions, setExecutions] = useState<ExecutionRecord[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [collectionId, setCollectionId] = useState("")
  const [collectionType, setCollectionType] = useState<
    "test-suite" | "test-scenario" | "test-scenario-folder"
  >("test-suite")
  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [environmentId, setEnvironmentId] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [_selectedExecution, setSelectedExecution] =
    useState<ExecutionRecord | null>(null)
  const [copiedText, copy] = useCopyToClipboard()

  // 分页和筛选状态
  const [currentPage, setCurrentPage] = useState(0)
  const [pageSize, setPageSize] = useState(10)
  const [totalCount, setTotalCount] = useState(0)
  const [filterStatus, setFilterStatus] = useState<string>("")
  const [filterProjectId, setFilterProjectId] = useState<string>("")
  const [filterProjectName, setFilterProjectName] = useState("")
  const [searchInput, setSearchInput] = useState("")

  // API 基础 URL - 使用绝对路径确保正确访问
  const API_BASE = import.meta.env.VITE_API_URL

  // 获取项目列表
  const fetchProjects = async () => {
    try {
      const token = localStorage.getItem("access_token")
      if (!token) return
      
      const response = await fetch(`${API_BASE}/api/v1/projects/`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      })
      
      if (response.ok) {
        const data = await response.json()
        setProjects(data.data || [])
      }
    } catch (error) {
      console.error("获取项目列表失败:", error)
    }
  }

  // 获取执行列表
  const fetchExecutions = async () => {
    try {
      const token = localStorage.getItem("access_token")
      if (!token) {
        toast.error("请先登录")
        return
      }
      
      // 构建查询参数
      const params = new URLSearchParams()
      params.append("skip", (currentPage * pageSize).toString())
      params.append("limit", pageSize.toString())
      if (filterStatus) params.append("status", filterStatus)
      if (filterProjectId) params.append("project_id", filterProjectId)
      if (filterProjectName) params.append("project_name", filterProjectName)
      
      const url = `${API_BASE}/api/v1/executions/?${params.toString()}`
      console.log("Fetching from:", url)
      
      const response = await fetch(url, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      })
      
      if (response.ok) {
        const data = await response.json()
        setExecutions(data.data || [])
        setTotalCount(data.count || 0)
      } else if (response.status === 401) {
        toast.error("登录已过期，请重新登录")
        localStorage.removeItem("access_token")
        window.location.href = "/login"
      } else {
        const errorData = await response.json().catch(() => ({}))
        toast.error(errorData.detail || "获取执行列表失败")
      }
    } catch (_error) {
      console.error("Fetch error:", _error)
      toast.error("网络错误，请检查后端服务是否启动")
    }
  }

  // 初始加载和筛选/分页变化时重新获取数据
  useEffect(() => {
    fetchExecutions()
  }, [currentPage, pageSize, filterStatus, filterProjectId, filterProjectName])

  // 初始加载项目列表
  useEffect(() => {
    fetchProjects()
  }, [])

  // 获取状态对应的样式
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return (
          <Badge
            variant="outline"
            className="text-amber-600 border-amber-300 bg-amber-50"
          >
            等待中
          </Badge>
        )
      case "running":
        return <Badge className="bg-primary">执行中</Badge>
      case "completed":
        return <Badge className="bg-green-500">已完成</Badge>
      case "failed":
        return <Badge variant="destructive">失败</Badge>
      default:
        return <Badge variant="outline">未知</Badge>
    }
  }

  const CopyExecutionId = ({ id }: { id: string }) => {
    const isCopied = copiedText === id
    return (
      <div className="flex items-center gap-1.5 group">
        <span className="font-mono text-xs text-muted-foreground">
          {id.slice(0, 8)}…
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={() => copy(id)}
        >
          {isCopied ? (
            <Check className="size-3 text-green-500" />
          ) : (
            <Copy className="size-3" />
          )}
          <span className="sr-only">Copy ID</span>
        </Button>
      </div>
    )
  }

  // 触发执行 - 调用真实后端 API
  const handleExecute = async () => {
    if (!collectionId.trim()) {
      toast.error("请输入Apifox集合ID")
      return
    }

    const token = localStorage.getItem("access_token")
    if (!token) {
      toast.error("请先登录")
      return
    }

    setIsLoading(true)

    try {
      const runUrl = `${API_BASE}/api/v1/executions/run`
      console.log("Running execution at:", runUrl)
      
      const runResponse = await fetch(runUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          project_id: selectedProjectId || null,
          collection_id: collectionId,
          collection_type: collectionType,
          environment: environmentId || null,
        }),
      })

      if (runResponse.status === 401) {
        toast.error("登录已过期，请重新登录")
        localStorage.removeItem("access_token")
        window.location.href = "/login"
        return
      }

      if (!runResponse.ok) {
        const errorData = await runResponse.json().catch(() => ({}))
        throw new Error(errorData.detail || "执行失败")
      }

      const result = await runResponse.json()

      setExecutions((prev) => [result, ...prev])
      toast.success("测试执行完成")
      setCollectionId("")
      setSelectedProjectId("")

      await fetchExecutions()
    } catch (error: any) {
      console.error("Execute error:", error)
      toast.error(error.message || "执行失败")
    } finally {
      setIsLoading(false)
    }
  }

  // 删除记录
  const handleDelete = async (id: string) => {
    const token = localStorage.getItem("access_token")
    if (!token) {
      toast.error("请先登录")
      return
    }

    try {
      const deleteUrl = `${API_BASE}/api/v1/executions/${id}`
      console.log("Deleting execution at:", deleteUrl)
      
      const response = await fetch(deleteUrl, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      })

      if (response.status === 401) {
        toast.error("登录已过期，请重新登录")
        localStorage.removeItem("access_token")
        window.location.href = "/login"
        return
      }

      if (response.ok) {
        setExecutions((prev) => prev.filter((e) => e.id !== id))
        toast.success("记录已删除")
      } else {
        const errorData = await response.json().catch(() => ({}))
        toast.error(errorData.detail || "删除失败")
      }
    } catch (_error) {
      console.error("Delete error:", _error)
      toast.error("网络错误，请检查后端服务是否启动")
    }
  }

  // 刷新列表
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await fetchExecutions()
    setIsRefreshing(false)
    toast.info("已刷新")
  }

  // 格式化时间
  const formatTime = (time: string | null) => {
    if (!time) return "-"
    return new Date(time).toLocaleString("zh-CN")
  }

  // 计算统计数据
  const totalExecutions = executions.length
  const completedExecutions = executions.filter(
    (e) => e.status === "completed",
  ).length
  const failedExecutions = executions.filter(
    (e) => e.status === "failed",
  ).length
  const totalCases = executions.reduce(
    (sum, e) => sum + (e.total_cases || 0),
    0,
  )
  const passedCases = executions.reduce(
    (sum, e) => sum + (e.passed_cases || 0),
    0,
  )
  const passRate =
    totalCases > 0 ? Math.round((passedCases / totalCases) * 100) : 0

  return (
    <div className="p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Zap className="w-6 h-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">测试执行</h1>
          <p className="text-muted-foreground text-sm">
            触发Apifox测试集合并查看执行结果
          </p>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border border-border shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">总执行次数</p>
                <p className="text-2xl font-bold text-foreground mt-1">
                  {totalExecutions}
                </p>
              </div>
<div className="p-3 bg-primary/10 rounded-lg">
                    <BarChart3 className="w-5 h-5 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">成功次数</p>
                <p className="text-2xl font-bold text-green-600 mt-1">
                  {completedExecutions}
                </p>
              </div>
<div className="p-3 bg-emerald-50/60 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">失败次数</p>
                <p className="text-2xl font-bold text-red-600 mt-1">
                  {failedExecutions}
                </p>
              </div>
<div className="p-3 bg-rose-50 rounded-lg">
                    <XCircle className="w-5 h-5 text-rose-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">通过率</p>
                <div className="flex items-baseline gap-1 mt-1">
                  <p className="text-2xl font-bold text-foreground">{passRate}</p>
                  <span className="text-sm text-muted-foreground">%</span>
                </div>
              </div>
<div className="p-3 bg-muted rounded-lg">
                    <BarChart3 className="w-5 h-5 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 执行表单 */}
      <Card className="border border-border shadow-sm">
        <CardHeader className="border-b border-border bg-muted/30">
          <CardTitle className="text-lg font-semibold text-foreground">
            新建执行
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="w-full md:w-40 space-y-2">
              <label className="text-sm font-medium text-foreground/70">
                执行类型
              </label>
              <select
                value={collectionType}
                onChange={(e) =>
                  setCollectionType(
                    e.target.value as
                      | "test-suite"
                      | "test-scenario"
                      | "test-scenario-folder",
                  )
                }
                className="h-10 w-full px-3 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="test-suite">测试套件</option>
                <option value="test-scenario">测试场景</option>
                <option value="test-scenario-folder">场景目录</option>
              </select>
            </div>
            <div className="w-full md:w-48 space-y-2">
              <label className="text-sm font-medium text-muted-foreground">
                关联项目
              </label>
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="h-10 w-full px-3 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">不关联项目</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1 space-y-2 w-full">
              <label className="text-sm font-medium text-muted-foreground">
                Apifox集合ID
              </label>
              <Input
                placeholder="请输入Apifox集合ID，例如：proj_123456"
                value={collectionId}
                onChange={(e) => setCollectionId(e.target.value)}
                className="h-10"
              />
            </div>
            <div className="flex-1 space-y-2 w-full">
              <label className="text-sm font-medium text-muted-foreground">
                环境 ID（可选）
              </label>
              <Input
                placeholder="例如：42511518"
                value={environmentId}
                onChange={(e) => setEnvironmentId(e.target.value)}
                className="h-10"
              />
            </div>
            <Button
              onClick={handleExecute}
              disabled={isLoading}
              className="h-10 px-6 bg-primary hover:bg-primary/90"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  执行中...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  开始执行
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 执行记录列表 */}
      <Card className="border border-border shadow-sm">
        <CardHeader className="border-b border-border bg-muted/50">
          <div className="flex flex-col gap-4">
            {/* 标题和刷新按钮 */}
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold text-foreground">
                执行记录
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  (共 {totalCount} 条)
                </span>
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="border-border"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
                刷新
              </Button>
            </div>
            
            {/* 筛选栏 */}
            <div className="flex flex-wrap items-center gap-3">
              {/* 项目筛选 */}
              <select
                value={filterProjectId}
                onChange={(e) => {
                  setFilterProjectId(e.target.value)
                  setCurrentPage(0)
                }}
                className="h-9 px-3 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">所有项目</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
              
              {/* 状态筛选 */}
              <select
                value={filterStatus}
                onChange={(e) => {
                  setFilterStatus(e.target.value)
                  setCurrentPage(0)
                }}
                className="h-9 px-3 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">所有状态</option>
                <option value="pending">等待中</option>
                <option value="running">执行中</option>
                <option value="completed">已完成</option>
                <option value="failed">失败</option>
              </select>
              
              {/* 项目名称搜索 */}
              <div className="flex items-center gap-2">
                <Input
                  placeholder="搜索项目名称"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="h-9 w-48"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setFilterProjectName(searchInput)
                    setCurrentPage(0)
                  }}
                  className="h-9"
                >
                  搜索
                </Button>
                {(filterStatus || filterProjectId || filterProjectName) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setFilterStatus("")
                      setFilterProjectId("")
                      setFilterProjectName("")
                      setSearchInput("")
                      setCurrentPage(0)
                    }}
                    className="h-9 text-muted-foreground"
                  >
                    清除筛选
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50 hover:bg-muted/50">
                  <TableHead className="font-medium text-muted-foreground">
                    集合ID
                  </TableHead>
                  <TableHead className="font-medium text-muted-foreground">
                    执行ID
                  </TableHead>
                  <TableHead className="font-medium text-muted-foreground">
                    项目名称
                  </TableHead>
                  <TableHead className="font-medium text-muted-foreground">
                    状态
                  </TableHead>
                  <TableHead className="font-medium text-muted-foreground">
                    用例数
                  </TableHead>
                  <TableHead className="font-medium text-muted-foreground">
                    执行结果
                  </TableHead>
                  <TableHead className="font-medium text-muted-foreground">
                    创建时间
                  </TableHead>
                  <TableHead className="font-medium text-muted-foreground text-right">
                    操作
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {executions.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className="text-center py-12 text-muted-foreground"
                    >
                      暂无执行记录
                    </TableCell>
                  </TableRow>
                ) : (
                  executions.map((execution) => (
                    <TableRow key={execution.id} className="hover:bg-muted/50">
                      <TableCell>
                        <span className="font-mono text-sm bg-muted px-2 py-1 rounded text-foreground">
                          {execution.apifox_collection_id}
                        </span>
                      </TableCell>
                      <TableCell>
                        <CopyExecutionId id={execution.id} />
                      </TableCell>
                      <TableCell>
                        <span className="font-medium text-foreground">
                          {execution.project_name || "-"}
                        </span>
                      </TableCell>
                      <TableCell>{getStatusBadge(execution.status)}</TableCell>
                      <TableCell>
                        <span className="font-medium text-foreground">
                          {execution.total_cases || "-"}
                        </span>
                        <span className="text-muted-foreground text-sm ml-1">个</span>
                      </TableCell>
                      <TableCell>
                        {execution.passed_cases !== null ? (
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1">
                              <CheckCircle className="w-4 h-4 text-green-500" />
                              <span className="text-sm text-green-600">
                                {execution.passed_cases}
                              </span>
                            </div>
                            <Separator orientation="vertical" className="h-4" />
                            <div className="flex items-center gap-1">
                              <XCircle className="w-4 h-4 text-destructive" />
                              <span className="text-sm text-red-600">
                                {execution.failed_cases}
                              </span>
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="w-4 h-4" />
                          {formatTime(execution.created_at)}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSelectedExecution(execution)}
                                className="text-primary hover:text-primary/80 hover:bg-accent"
                              >
                                查看详情
                                <ChevronRight className="w-4 h-4 ml-1" />
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-2xl">
                              <DialogHeader>
                                <DialogTitle className="text-xl font-bold text-foreground">
                                  执行详情
                                </DialogTitle>
                                <DialogDescription className="text-muted-foreground">
                                  执行ID:{" "}
                                  <span className="font-mono text-foreground">
                                    {execution.id}
                                  </span>
                                  <span className="mx-2">|</span>
                                  集合ID:{" "}
                                  <span className="font-mono text-foreground">
                                    {execution.apifox_collection_id}
                                  </span>
                                </DialogDescription>
                              </DialogHeader>
                              <div className="space-y-4 mt-4">
                                {/* 状态 */}
                                <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                                  <span className="font-medium text-foreground">
                                    执行状态
                                  </span>
                                  {getStatusBadge(execution.status)}
                                </div>

                                {/* 基本信息 */}
                                <div className="grid grid-cols-2 gap-4">
                                  <div className="space-y-1">
                                    <label className="text-sm text-muted-foreground">
                                      项目名称
                                    </label>
                                    <div className="font-medium text-foreground">
                                      {execution.project_name || "-"}
                                    </div>
                                  </div>
                                  <div className="space-y-1">
                                    <label className="text-sm text-muted-foreground">
                                      总用例数
                                    </label>
                                    <div className="font-medium text-foreground">
                                      {execution.total_cases || "-"} 个
                                    </div>
                                  </div>
                                  <div className="space-y-1">
                                    <label className="text-sm text-muted-foreground">
                                      创建时间
                                    </label>
                                    <div className="font-medium text-foreground">
                                      {formatTime(execution.created_at)}
                                    </div>
                                  </div>
                                  <div className="space-y-1">
                                    <label className="text-sm text-muted-foreground">
                                      完成时间
                                    </label>
                                    <div className="font-medium text-foreground">
                                      {formatTime(execution.completed_at)}
                                    </div>
                                  </div>
                                </div>

                                {/* 执行结果 */}
                                {execution.passed_cases !== null && (
                                  <div className="p-4 bg-muted/50 rounded-lg space-y-3">
                                    <label className="text-sm font-medium text-muted-foreground">
                                      执行结果统计
                                    </label>
                                    <div className="flex items-center gap-6">
                                      <div className="flex items-center gap-2">
                                        <CheckCircle className="w-5 h-5 text-green-500" />
                                        <span className="text-green-600 font-medium">
                                          {execution.passed_cases} 通过
                                        </span>
                                      </div>
                                      <div className="flex items-center gap-2">
                                        <XCircle className="w-5 h-5 text-destructive" />
                                        <span className="text-red-600 font-medium">
                                          {execution.failed_cases} 失败
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                )}

                                {/* 错误信息 */}
                                {execution.error_message && (
                                  <div className="p-4 bg-red-50/60 border border-destructive/30 rounded-lg">
                                    <label className="text-sm font-medium text-red-600 flex items-center gap-2 mb-2">
                                      <XCircle className="w-4 h-4" />
                                      错误信息
                                    </label>
                                    <div className="text-red-600 text-sm">
                                      {execution.error_message}
                                    </div>
                                  </div>
                                )}

                                {/* 详细报告 */}
                                {execution.report_json && (
                                  <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                      <FileText className="w-4 h-4" />
                                      详细报告
                                    </label>
                                    <div className="p-4 bg-foreground rounded-lg font-mono text-sm overflow-auto max-h-60">
                                      <pre className="text-green-400">
                                        {JSON.stringify(
                                          JSON.parse(execution.report_json),
                                          null,
                                          2,
                                        )}
                                      </pre>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </DialogContent>
                          </Dialog>

                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(execution.id)}
                            className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          
          {/* 分页 */}
          {totalCount > 0 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-border">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>每页</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value))
                    setCurrentPage(0)
                  }}
                  className="h-8 px-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
                <span>条</span>
                <span className="ml-4">
                  第 {currentPage + 1} 页，共 {Math.ceil(totalCount / pageSize)} 页
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(0)}
                  disabled={currentPage === 0}
                  className="h-8 px-3"
                >
                  首页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
                  disabled={currentPage === 0}
                  className="h-8 px-3"
                >
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => prev + 1)}
                  disabled={(currentPage + 1) * pageSize >= totalCount}
                  className="h-8 px-3"
                >
                  下一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(Math.ceil(totalCount / pageSize) - 1)}
                  disabled={(currentPage + 1) * pageSize >= totalCount}
                  className="h-8 px-3"
                >
                  末页
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
