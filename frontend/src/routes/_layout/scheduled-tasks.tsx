import { createFileRoute } from "@tanstack/react-router"
import {
  Clock,
  Plus,
  RefreshCw,
  Settings,
  Trash2,
  Play,
  Pause,
  Calendar,
  History,
  CheckCircle,
  XCircle,
  Loader2,
} from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

interface ScheduledTask {
  id: string
  name: string
  description: string | null
  project_id: string | null
  collection_id: string
  collection_type: string
  environment: string | null
  trigger_type: "cron" | "interval" | "date"
  trigger_config: string
  is_enabled: boolean
  notification_rule_id: string | null
  max_retries: number
  retry_interval: number
  timeout_seconds: number
  last_run_at: string | null
  next_run_at: string | null
  created_at: string
  updated_at: string
}

interface TaskExecutionLog {
  id: string
  task_id: string
  execution_id: string | null
  status: "pending" | "running" | "completed" | "failed" | "timeout"
  error_message: string | null
  retry_count: number
  attempt_number: number
  started_at: string
  finished_at: string | null
  created_at: string
}

interface Project {
  id: string
  name: string
}

interface NotificationRule {
  id: string
  name: string
}

export const Route = createFileRoute("/_layout/scheduled-tasks")({
  component: ScheduledTasksPage,
  head: () => ({
    meta: [
      {
        title: "定时任务 - 测试管理平台",
      },
    ],
  }),
})

function ScheduledTasksPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [logs, setLogs] = useState<TaskExecutionLog[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [rules, setRules] = useState<NotificationRule[]>([])
  const [isLoading, setIsLoading] = useState(false)
  
  const [taskDialogOpen, setTaskDialogOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null)
  
  const [taskForm, setTaskForm] = useState({
    name: "",
    description: "",
    project_id: "",
    collection_id: "",
    collection_type: "test-suite",
    environment: "",
    trigger_type: "cron" as "cron" | "interval" | "date",
    trigger_config_cron: "0 2 * * *",
    trigger_config_interval_minutes: 60,
    trigger_config_interval_hours: 0,
    trigger_config_date: "",
    notification_rule_id: "",
    max_retries: 3,
    retry_interval: 60,
    timeout_seconds: 300,
  })

  const fetchTasks = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) return
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/scheduled-tasks/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        const data = await response.json()
        setTasks(data.data || [])
      }
    } catch (error) {
      console.error("获取任务失败:", error)
    }
  }

  const fetchLogs = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) return
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/scheduled-tasks/logs/all?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        const data = await response.json()
        setLogs(data.data || [])
      }
    } catch (error) {
      console.error("获取日志失败:", error)
    }
  }

  const fetchProjects = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) return
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/projects/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        const data = await response.json()
        setProjects(data.data || [])
      }
    } catch (error) {
      console.error("获取项目失败:", error)
    }
  }

  const fetchRules = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) return
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/notifications/rules`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        const data = await response.json()
        setRules(data.data || [])
      }
    } catch (error) {
      console.error("获取规则失败:", error)
    }
  }

  useEffect(() => {
    fetchTasks()
    fetchLogs()
    fetchProjects()
    fetchRules()
  }, [])

  const buildTriggerConfig = () => {
    if (taskForm.trigger_type === "cron") {
      return JSON.stringify({ cron: taskForm.trigger_config_cron })
    } else if (taskForm.trigger_type === "interval") {
      return JSON.stringify({
        minutes: taskForm.trigger_config_interval_minutes,
        hours: taskForm.trigger_config_interval_hours,
      })
    } else if (taskForm.trigger_type === "date") {
      return JSON.stringify({ run_date: taskForm.trigger_config_date })
    }
    return "{}"
  }

  const parseTriggerConfig = (task: ScheduledTask) => {
    try {
      const config = JSON.parse(task.trigger_config)
      if (task.trigger_type === "cron") {
        return config.cron || "0 2 * * *"
      } else if (task.trigger_type === "interval") {
        const minutes = config.minutes || 0
        const hours = config.hours || 0
        if (hours > 0) {
          return `每 ${hours} 小时 ${minutes} 分钟`
        }
        return `每 ${minutes} 分钟`
      } else if (task.trigger_type === "date") {
        return config.run_date || "-"
      }
    } catch {
      return task.trigger_config
    }
    return "-"
  }

  const handleSaveTask = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) {
      toast.error("请先登录")
      return
    }

    if (!taskForm.name || !taskForm.collection_id) {
      toast.error("请填写任务名称和测试集合 ID")
      return
    }

    setIsLoading(true)
    try {
      const url = editingTask
        ? `${API_BASE}/api/v1/scheduled-tasks/${editingTask.id}`
        : `${API_BASE}/api/v1/scheduled-tasks/`
      
      const body = {
        name: taskForm.name,
        description: taskForm.description || null,
        project_id: taskForm.project_id === "__none__" ? null : taskForm.project_id || null,
        collection_id: taskForm.collection_id,
        collection_type: taskForm.collection_type,
        environment: taskForm.environment || null,
        trigger_type: taskForm.trigger_type,
        trigger_config: buildTriggerConfig(),
        notification_rule_id: taskForm.notification_rule_id === "__none__" ? null : taskForm.notification_rule_id || null,
        max_retries: taskForm.max_retries,
        retry_interval: taskForm.retry_interval,
        timeout_seconds: taskForm.timeout_seconds,
      }

      const response = await fetch(url, {
        method: editingTask ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })

      if (response.ok) {
        toast.success(editingTask ? "更新成功" : "创建成功")
        setTaskDialogOpen(false)
        setEditingTask(null)
        resetForm()
        fetchTasks()
      } else {
        const error = await response.json()
        toast.error(error.detail || "操作失败")
      }
    } catch (error) {
      toast.error("网络错误")
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm("确定要删除此任务吗？")) return
    
    const token = localStorage.getItem("access_token")
    if (!token) return

    try {
      const response = await fetch(`${API_BASE}/api/v1/scheduled-tasks/${taskId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        toast.success("删除成功")
        fetchTasks()
      }
    } catch (error) {
      toast.error("删除失败")
    }
  }

  const handleToggleTask = async (taskId: string, enable: boolean) => {
    const token = localStorage.getItem("access_token")
    if (!token) return

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/scheduled-tasks/${taskId}/${enable ? "enable" : "disable"}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      )

      if (response.ok) {
        toast.success(enable ? "已启用" : "已禁用")
        fetchTasks()
      }
    } catch (error) {
      toast.error("操作失败")
    }
  }

  const handleTriggerTask = async (taskId: string) => {
    const token = localStorage.getItem("access_token")
    if (!token) return

    try {
      const response = await fetch(`${API_BASE}/api/v1/scheduled-tasks/${taskId}/trigger`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        toast.success("已触发执行")
        fetchTasks()
        fetchLogs()
      }
    } catch (error) {
      toast.error("触发失败")
    }
  }

  const resetForm = () => {
    setTaskForm({
      name: "",
      description: "",
      project_id: "__none__",
      collection_id: "",
      collection_type: "test-suite",
      environment: "",
      trigger_type: "cron",
      trigger_config_cron: "0 2 * * *",
      trigger_config_interval_minutes: 60,
      trigger_config_interval_hours: 0,
      trigger_config_date: "",
      notification_rule_id: "__none__",
      max_retries: 3,
      retry_interval: 60,
      timeout_seconds: 300,
    })
  }

  const openTaskDialog = (task?: ScheduledTask) => {
    if (task) {
      setEditingTask(task)
      try {
        const config = JSON.parse(task.trigger_config)
        setTaskForm({
          name: task.name,
          description: task.description || "",
          project_id: task.project_id || "__none__",
          collection_id: task.collection_id,
          collection_type: task.collection_type,
          environment: task.environment || "",
          trigger_type: task.trigger_type as "cron" | "interval" | "date",
          trigger_config_cron: config.cron || "0 2 * * *",
          trigger_config_interval_minutes: config.minutes || 60,
          trigger_config_interval_hours: config.hours || 0,
          trigger_config_date: config.run_date || "",
          notification_rule_id: task.notification_rule_id || "__none__",
          max_retries: task.max_retries ?? 3,
          retry_interval: task.retry_interval ?? 60,
          timeout_seconds: task.timeout_seconds ?? 300,
        })
      } catch {
        setTaskForm({
          name: task.name,
          description: task.description || "",
          project_id: task.project_id || "__none__",
          collection_id: task.collection_id,
          collection_type: task.collection_type,
          environment: task.environment || "",
          trigger_type: task.trigger_type as "cron" | "interval" | "date",
          trigger_config_cron: "0 2 * * *",
          trigger_config_interval_minutes: 60,
          trigger_config_interval_hours: 0,
          trigger_config_date: "",
          notification_rule_id: task.notification_rule_id || "__none__",
          max_retries: task.max_retries ?? 3,
          retry_interval: task.retry_interval ?? 60,
          timeout_seconds: task.timeout_seconds ?? 300,
        })
      }
    } else {
      setEditingTask(null)
      resetForm()
    }
    setTaskDialogOpen(true)
  }

  const getTriggerTypeName = (type: string) => {
    switch (type) {
      case "cron":
        return "Cron 表达式"
      case "interval":
        return "固定间隔"
      case "date":
        return "单次执行"
      default:
        return type
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge className="bg-green-50 text-green-700">成功</Badge>
      case "failed":
        return <Badge className="bg-red-50 text-red-700">失败</Badge>
      case "timeout":
        return <Badge className="bg-orange-50 text-orange-700">超时</Badge>
      case "running":
        return <Badge className="bg-primary/10 text-primary">运行中</Badge>
      case "pending":
        return <Badge className="bg-yellow-50 text-yellow-700">等待中</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">定时任务</h1>
          <p className="text-muted-foreground">配置定时执行测试任务，支持 Cron 表达式和固定间隔</p>
        </div>
        <Button variant="outline" onClick={() => { fetchTasks(); fetchLogs(); }}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      <Tabs defaultValue="tasks" className="space-y-4">
        <TabsList>
          <TabsTrigger value="tasks">任务列表</TabsTrigger>
          <TabsTrigger value="logs">执行历史</TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">定时任务配置</h2>
            <Button onClick={() => openTaskDialog()}>
              <Plus className="mr-2 h-4 w-4" />
              新增任务
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>任务名称</TableHead>
                    <TableHead>触发类型</TableHead>
                    <TableHead>触发配置</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>上次执行</TableHead>
                    <TableHead>下次执行</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tasks.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        暂无定时任务，点击"新增任务"添加
                      </TableCell>
                    </TableRow>
                  ) : (
                    tasks.map((task) => (
                      <TableRow key={task.id}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                            {task.name}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{getTriggerTypeName(task.trigger_type)}</Badge>
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {parseTriggerConfig(task)}
                        </TableCell>
                        <TableCell>
                          {task.is_enabled ? (
                            <Badge className="bg-green-50 text-green-700">已启用</Badge>
                          ) : (
                            <Badge className="bg-muted text-foreground">已禁用</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {task.last_run_at ? new Date(task.last_run_at).toLocaleString() : "-"}
                        </TableCell>
                        <TableCell>
                          {task.next_run_at ? new Date(task.next_run_at).toLocaleString() : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleTriggerTask(task.id)}
                              title="立即执行"
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleTask(task.id, !task.is_enabled)}
                              title={task.is_enabled ? "禁用" : "启用"}
                            >
                              {task.is_enabled ? (
                                <Pause className="h-4 w-4" />
                              ) : (
                                <Play className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openTaskDialog(task)}
                              title="编辑"
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteTask(task.id)}
                              title="删除"
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <h2 className="text-lg font-semibold">执行历史</h2>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>任务 ID</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>尝试次数</TableHead>
                    <TableHead>开始时间</TableHead>
                    <TableHead>结束时间</TableHead>
                    <TableHead>错误信息</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                        暂无执行记录
                      </TableCell>
                    </TableRow>
                  ) : (
                    logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="font-mono text-sm">
                          {log.task_id.slice(0, 8)}...
                        </TableCell>
                        <TableCell>{getStatusBadge(log.status)}</TableCell>
                        <TableCell>
                          {log.attempt_number > 1 ? (
                            <span className="text-orange-600">{log.attempt_number}次</span>
                          ) : (
                            <span>1次</span>
                          )}
                        </TableCell>
                        <TableCell>{new Date(log.started_at).toLocaleString()}</TableCell>
                        <TableCell>
                          {log.finished_at ? new Date(log.finished_at).toLocaleString() : "-"}
                        </TableCell>
                        <TableCell className="max-w-xs truncate text-red-500">
                          {log.error_message || "-"}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={taskDialogOpen} onOpenChange={setTaskDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingTask ? "编辑任务" : "新增任务"}</DialogTitle>
            <DialogDescription>
              配置定时任务，支持 Cron 表达式、固定间隔和单次执行
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>任务名称 *</Label>
                <Input
                  value={taskForm.name}
                  onChange={(e) => setTaskForm({ ...taskForm, name: e.target.value })}
                  placeholder="例如：每日回归测试"
                />
              </div>
              <div className="space-y-2">
                <Label>关联项目</Label>
                <Select
                  value={taskForm.project_id}
                  onValueChange={(v) => setTaskForm({ ...taskForm, project_id: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择项目" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">无</SelectItem>
                    {projects.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>任务描述</Label>
              <Textarea
                value={taskForm.description}
                onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
                placeholder="任务描述（可选）"
                rows={2}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>测试集合 ID *</Label>
                <Input
                  value={taskForm.collection_id}
                  onChange={(e) => setTaskForm({ ...taskForm, collection_id: e.target.value })}
                  placeholder="Apifox 测试集合 ID"
                />
              </div>
              <div className="space-y-2">
                <Label>集合类型</Label>
                <Select
                  value={taskForm.collection_type}
                  onValueChange={(v) => setTaskForm({ ...taskForm, collection_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="test-suite">测试套件</SelectItem>
                    <SelectItem value="test-scenario">测试场景</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>执行环境 ID</Label>
              <Input
                value={taskForm.environment}
                onChange={(e) => setTaskForm({ ...taskForm, environment: e.target.value })}
                placeholder="Apifox 环境ID（可选）"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>触发类型</Label>
                <Select
                  value={taskForm.trigger_type}
                  onValueChange={(v) => setTaskForm({ ...taskForm, trigger_type: v as "cron" | "interval" | "date" })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cron">Cron 表达式</SelectItem>
                    <SelectItem value="interval">固定间隔</SelectItem>
                    <SelectItem value="date">单次执行</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>通知规则</Label>
                <Select
                  value={taskForm.notification_rule_id}
                  onValueChange={(v) => setTaskForm({ ...taskForm, notification_rule_id: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择通知规则" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">无</SelectItem>
                    {rules.map((r) => (
                      <SelectItem key={r.id} value={r.id}>
                        {r.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {taskForm.trigger_type === "cron" && (
              <div className="space-y-2">
                <Label>Cron 表达式</Label>
                <Input
                  value={taskForm.trigger_config_cron}
                  onChange={(e) => setTaskForm({ ...taskForm, trigger_config_cron: e.target.value })}
                  placeholder="分 时 日 月 周，例如：0 2 * * *"
                />
                <p className="text-xs text-muted-foreground">
                  示例：0 2 * * *（每天凌晨2点）、0 */2 * * *（每2小时）、30 9 * * 1-5（工作日9:30）
                </p>
              </div>
            )}

            {taskForm.trigger_type === "interval" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>间隔小时数</Label>
                  <Input
                    type="number"
                    min={0}
                    value={taskForm.trigger_config_interval_hours}
                    onChange={(e) =>
                      setTaskForm({
                        ...taskForm,
                        trigger_config_interval_hours: parseInt(e.target.value) || 0,
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>间隔分钟数</Label>
                  <Input
                    type="number"
                    min={0}
                    value={taskForm.trigger_config_interval_minutes}
                    onChange={(e) =>
                      setTaskForm({
                        ...taskForm,
                        trigger_config_interval_minutes: parseInt(e.target.value) || 0,
                      })
                    }
                  />
                </div>
              </div>
            )}

            {taskForm.trigger_type === "date" && (
              <div className="space-y-2">
                <Label>执行时间</Label>
                <Input
                  type="datetime-local"
                  value={taskForm.trigger_config_date}
                  onChange={(e) => setTaskForm({ ...taskForm, trigger_config_date: e.target.value })}
                />
              </div>
            )}

            <div className="border-t pt-4 mt-4">
              <h4 className="font-medium mb-3">执行控制</h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>最大重试次数</Label>
                  <Input
                    type="number"
                    min={0}
                    max={10}
                    value={taskForm.max_retries}
                    onChange={(e) =>
                      setTaskForm({
                        ...taskForm,
                        max_retries: parseInt(e.target.value) || 0,
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">失败后重试次数，0表示不重试</p>
                </div>
                <div className="space-y-2">
                  <Label>重试间隔（秒）</Label>
                  <Input
                    type="number"
                    min={10}
                    value={taskForm.retry_interval}
                    onChange={(e) =>
                      setTaskForm({
                        ...taskForm,
                        retry_interval: parseInt(e.target.value) || 60,
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">重试间隔，采用指数退避</p>
                </div>
                <div className="space-y-2">
                  <Label>超时时间（秒）</Label>
                  <Input
                    type="number"
                    min={30}
                    value={taskForm.timeout_seconds}
                    onChange={(e) =>
                      setTaskForm({
                        ...taskForm,
                        timeout_seconds: parseInt(e.target.value) || 300,
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">任务执行超时时间</p>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTaskDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSaveTask} disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {editingTask ? "更新" : "创建"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
