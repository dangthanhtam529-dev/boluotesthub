import { createFileRoute } from "@tanstack/react-router"
import {
  Bell,
  CheckCircle,
  Plus,
  RefreshCw,
  Settings,
  Trash2,
  XCircle,
  Send,
  MessageSquare,
  Mail,
  Clock,
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
import { Separator } from "@/components/ui/separator"
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

interface NotificationChannel {
  id: string
  name: string
  channel_type: "dingtalk" | "wework" | "email"
  config: string
  description: string | null
  is_enabled: boolean
  created_at: string
  updated_at: string
}

interface NotificationRule {
  id: string
  name: string
  trigger_type: string
  trigger_config: string | null
  channel_ids: string
  template: string | null
  project_id: string | null
  is_enabled: boolean
  description: string | null
  created_at: string
  updated_at: string
}

interface NotificationLog {
  id: string
  rule_id: string | null
  channel_id: string | null
  channel_type: string
  channel_name: string
  title: string
  content: string
  status: "pending" | "sent" | "failed"
  error_message: string | null
  execution_id: string | null
  created_at: string
  sent_at: string | null
}

export const Route = createFileRoute("/_layout/notifications")({
  component: NotificationsPage,
  head: () => ({
    meta: [
      {
        title: "通知管理 - 测试管理平台",
      },
    ],
  }),
})

function NotificationsPage() {
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [rules, setRules] = useState<NotificationRule[]>([])
  const [logs, setLogs] = useState<NotificationLog[]>([])
  const [isLoading, setIsLoading] = useState(false)
  
  const [channelDialogOpen, setChannelDialogOpen] = useState(false)
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false)
  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null)
  const [editingRule, setEditingRule] = useState<NotificationRule | null>(null)
  
  const [channelForm, setChannelForm] = useState({
    name: "",
    channel_type: "dingtalk" as "dingtalk" | "wework" | "email",
    config: "",
    description: "",
  })
  
  const [ruleForm, setRuleForm] = useState({
    name: "",
    trigger_type: "execution_done",
    channel_ids: [] as string[],
    description: "",
  })

  const fetchChannels = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) return
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/notifications/channels`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        const data = await response.json()
        setChannels(data.data || [])
      }
    } catch (error) {
      console.error("获取渠道失败:", error)
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

  const fetchLogs = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) return
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/notifications/logs?limit=50`, {
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

  useEffect(() => {
    fetchChannels()
    fetchRules()
    fetchLogs()
  }, [])

  const handleSaveChannel = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) {
      toast.error("请先登录")
      return
    }

    if (!channelForm.name || !channelForm.config) {
      toast.error("请填写渠道名称和配置")
      return
    }

    setIsLoading(true)
    try {
      const url = editingChannel
        ? `${API_BASE}/api/v1/notifications/channels/${editingChannel.id}`
        : `${API_BASE}/api/v1/notifications/channels`
      
      const response = await fetch(url, {
        method: editingChannel ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(channelForm),
      })

      if (response.ok) {
        toast.success(editingChannel ? "更新成功" : "创建成功")
        setChannelDialogOpen(false)
        setEditingChannel(null)
        setChannelForm({ name: "", channel_type: "dingtalk", config: "", description: "" })
        fetchChannels()
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

  const handleDeleteChannel = async (channelId: string) => {
    if (!confirm("确定要删除此渠道吗？")) return
    
    const token = localStorage.getItem("access_token")
    if (!token) return

    try {
      const response = await fetch(`${API_BASE}/api/v1/notifications/channels/${channelId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        toast.success("删除成功")
        fetchChannels()
      }
    } catch (error) {
      toast.error("删除失败")
    }
  }

  const handleTestChannel = async (channelId: string) => {
    const token = localStorage.getItem("access_token")
    if (!token) return

    try {
      const response = await fetch(`${API_BASE}/api/v1/notifications/channels/test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ channel_id: channelId }),
      })

      const result = await response.json()
      if (result.success) {
        toast.success("测试消息发送成功")
      } else {
        toast.error(`发送失败: ${result.error || result.message}`)
      }
    } catch (error) {
      toast.error("测试失败")
    }
  }

  const handleSaveRule = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) {
      toast.error("请先登录")
      return
    }

    if (!ruleForm.name || ruleForm.channel_ids.length === 0) {
      toast.error("请填写规则名称并选择通知渠道")
      return
    }

    setIsLoading(true)
    try {
      const url = editingRule
        ? `${API_BASE}/api/v1/notifications/rules/${editingRule.id}`
        : `${API_BASE}/api/v1/notifications/rules`
      
      const response = await fetch(url, {
        method: editingRule ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...ruleForm,
          channel_ids: JSON.stringify(ruleForm.channel_ids),
        }),
      })

      if (response.ok) {
        toast.success(editingRule ? "更新成功" : "创建成功")
        setRuleDialogOpen(false)
        setEditingRule(null)
        setRuleForm({ name: "", trigger_type: "execution_done", channel_ids: [], description: "" })
        fetchRules()
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

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm("确定要删除此规则吗？")) return
    
    const token = localStorage.getItem("access_token")
    if (!token) return

    try {
      const response = await fetch(`${API_BASE}/api/v1/notifications/rules/${ruleId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        toast.success("删除成功")
        fetchRules()
      }
    } catch (error) {
      toast.error("删除失败")
    }
  }

  const getChannelTypeIcon = (type: string) => {
    switch (type) {
      case "dingtalk":
        return <MessageSquare className="h-4 w-4" />
      case "wework":
        <MessageSquare className="h-4 w-4" />
      case "email":
        return <Mail className="h-4 w-4" />
      default:
        return <Bell className="h-4 w-4" />
    }
  }

  const getChannelTypeName = (type: string) => {
    switch (type) {
      case "dingtalk":
        return "钉钉"
      case "wework":
        return "企业微信"
      case "email":
        return "邮件"
      default:
        return type
    }
  }

  const getTriggerTypeName = (type: string) => {
    switch (type) {
      case "execution_done":
        return "执行完成"
      case "execution_failed":
        return "执行失败"
      case "threshold_alert":
        return "阈值告警"
      case "daily_report":
        return "每日报告"
      case "weekly_report":
        return "每周报告"
      default:
        return type
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "sent":
        return <Badge className="bg-green-50 text-green-700">已发送</Badge>
      case "failed":
        return <Badge className="bg-red-50 text-red-700">发送失败</Badge>
      case "pending":
        return <Badge className="bg-yellow-50 text-yellow-700">待发送</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const openChannelDialog = (channel?: NotificationChannel) => {
    if (channel) {
      setEditingChannel(channel)
      setChannelForm({
        name: channel.name,
        channel_type: channel.channel_type,
        config: channel.config,
        description: channel.description || "",
      })
    } else {
      setEditingChannel(null)
      setChannelForm({ name: "", channel_type: "dingtalk", config: "", description: "" })
    }
    setChannelDialogOpen(true)
  }

  const openRuleDialog = (rule?: NotificationRule) => {
    if (rule) {
      setEditingRule(rule)
      let channelIds: string[] = []
      try {
        channelIds = JSON.parse(rule.channel_ids)
      } catch {
        channelIds = []
      }
      setRuleForm({
        name: rule.name,
        trigger_type: rule.trigger_type,
        channel_ids: channelIds,
        description: rule.description || "",
      })
    } else {
      setEditingRule(null)
      setRuleForm({ name: "", trigger_type: "execution_done", channel_ids: [], description: "" })
    }
    setRuleDialogOpen(true)
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">通知管理</h1>
          <p className="text-muted-foreground">配置通知渠道和规则，实现执行结果自动通知</p>
        </div>
        <Button variant="outline" onClick={() => { fetchChannels(); fetchRules(); fetchLogs(); }}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      <Tabs defaultValue="channels" className="space-y-4">
        <TabsList>
          <TabsTrigger value="channels">通知渠道</TabsTrigger>
          <TabsTrigger value="rules">通知规则</TabsTrigger>
          <TabsTrigger value="logs">发送记录</TabsTrigger>
        </TabsList>

        <TabsContent value="channels" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">通知渠道配置</h2>
            <Button onClick={() => openChannelDialog()}>
              <Plus className="mr-2 h-4 w-4" />
              新增渠道
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>渠道名称</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {channels.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                        暂无通知渠道，点击"新增渠道"添加
                      </TableCell>
                    </TableRow>
                  ) : (
                    channels.map((channel) => (
                      <TableRow key={channel.id}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            {getChannelTypeIcon(channel.channel_type)}
                            {channel.name}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{getChannelTypeName(channel.channel_type)}</Badge>
                        </TableCell>
                        <TableCell>
                          {channel.is_enabled ? (
                            <Badge className="bg-green-50 text-green-700">已启用</Badge>
                          ) : (
                            <Badge className="bg-muted text-foreground">已禁用</Badge>
                          )}
                        </TableCell>
                        <TableCell className="max-w-xs truncate">{channel.description || "-"}</TableCell>
                        <TableCell>{new Date(channel.created_at).toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleTestChannel(channel.id)}>
                              <Send className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => openChannelDialog(channel)}>
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteChannel(channel.id)}>
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

        <TabsContent value="rules" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">通知规则配置</h2>
            <Button onClick={() => openRuleDialog()}>
              <Plus className="mr-2 h-4 w-4" />
              新增规则
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>规则名称</TableHead>
                    <TableHead>触发条件</TableHead>
                    <TableHead>通知渠道</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rules.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                        暂无通知规则，点击"新增规则"添加
                      </TableCell>
                    </TableRow>
                  ) : (
                    rules.map((rule) => (
                      <TableRow key={rule.id}>
                        <TableCell className="font-medium">{rule.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{getTriggerTypeName(rule.trigger_type)}</Badge>
                        </TableCell>
                        <TableCell>
                          {(() => {
                            try {
                              const ids = JSON.parse(rule.channel_ids)
                              return ids.length + " 个渠道"
                            } catch {
                              return "-"
                            }
                          })()}
                        </TableCell>
                        <TableCell>
                          {rule.is_enabled ? (
                            <Badge className="bg-green-50 text-green-700">已启用</Badge>
                          ) : (
                            <Badge className="bg-muted text-foreground">已禁用</Badge>
                          )}
                        </TableCell>
                        <TableCell>{new Date(rule.created_at).toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" size="sm" onClick={() => openRuleDialog(rule)}>
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteRule(rule.id)}>
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
          <h2 className="text-lg font-semibold">发送记录</h2>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>标题</TableHead>
                    <TableHead>渠道</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>发送时间</TableHead>
                    <TableHead>错误信息</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                        暂无发送记录
                      </TableCell>
                    </TableRow>
                  ) : (
                    logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="font-medium">{log.title}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getChannelTypeIcon(log.channel_type)}
                            {log.channel_name}
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(log.status)}</TableCell>
                        <TableCell>
                          {log.sent_at ? new Date(log.sent_at).toLocaleString() : "-"}
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

      <Dialog open={channelDialogOpen} onOpenChange={setChannelDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingChannel ? "编辑渠道" : "新增渠道"}</DialogTitle>
            <DialogDescription>
              配置通知渠道信息
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>渠道名称</Label>
              <Input
                value={channelForm.name}
                onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })}
                placeholder="例如：测试群机器人"
              />
            </div>
            <div className="space-y-2">
              <Label>渠道类型</Label>
              <Select
                value={channelForm.channel_type}
                onValueChange={(value: "dingtalk" | "wework" | "email") =>
                  setChannelForm({ ...channelForm, channel_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dingtalk">钉钉</SelectItem>
                  <SelectItem value="wework">企业微信</SelectItem>
                  <SelectItem value="email">邮件</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>配置 (JSON 格式)</Label>
              <Textarea
                value={channelForm.config}
                onChange={(e) => setChannelForm({ ...channelForm, config: e.target.value })}
                placeholder={channelForm.channel_type === "dingtalk" 
                  ? '{"webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx", "secret": "SECxxx"}'
                  : '{"webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"}'
                }
                className="font-mono text-sm"
                rows={4}
              />
              <p className="text-xs text-muted-foreground">
                {channelForm.channel_type === "dingtalk" && "钉钉配置：webhook（必填）、secret（加签密钥，可选）"}
                {channelForm.channel_type === "wework" && "企业微信配置：webhook（必填）"}
                {channelForm.channel_type === "email" && "邮件配置：smtp_host、smtp_port、smtp_user、smtp_password、to_addrs"}
              </p>
            </div>
            <div className="space-y-2">
              <Label>描述</Label>
              <Input
                value={channelForm.description}
                onChange={(e) => setChannelForm({ ...channelForm, description: e.target.value })}
                placeholder="渠道用途说明"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setChannelDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveChannel} disabled={isLoading}>
              {isLoading ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingRule ? "编辑规则" : "新增规则"}</DialogTitle>
            <DialogDescription>
              配置通知规则
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>规则名称</Label>
              <Input
                value={ruleForm.name}
                onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                placeholder="例如：执行失败告警"
              />
            </div>
            <div className="space-y-2">
              <Label>触发条件</Label>
              <Select
                value={ruleForm.trigger_type}
                onValueChange={(value) => setRuleForm({ ...ruleForm, trigger_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="execution_done">执行完成</SelectItem>
                  <SelectItem value="execution_failed">执行失败</SelectItem>
                  <SelectItem value="threshold_alert">阈值告警</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>通知渠道</Label>
              <div className="flex flex-wrap gap-2">
                {channels.map((channel) => (
                  <Badge
                    key={channel.id}
                    variant={ruleForm.channel_ids.includes(channel.id) ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => {
                      if (ruleForm.channel_ids.includes(channel.id)) {
                        setRuleForm({
                          ...ruleForm,
                          channel_ids: ruleForm.channel_ids.filter((id) => id !== channel.id),
                        })
                      } else {
                        setRuleForm({
                          ...ruleForm,
                          channel_ids: [...ruleForm.channel_ids, channel.id],
                        })
                      }
                    }}
                  >
                    {channel.name}
                  </Badge>
                ))}
              </div>
              {channels.length === 0 && (
                <p className="text-sm text-muted-foreground">请先创建通知渠道</p>
              )}
            </div>
            <div className="space-y-2">
              <Label>描述</Label>
              <Input
                value={ruleForm.description}
                onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
                placeholder="规则用途说明"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRuleDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveRule} disabled={isLoading}>
              {isLoading ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
