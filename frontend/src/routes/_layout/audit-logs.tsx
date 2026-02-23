import { createFileRoute, redirect } from "@tanstack/react-router"
import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import { UsersService } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"

type AuditLogRow = {
  id: string
  created_at?: string
  request_id?: string | null
  actor_user_id?: string | null
  actor_email?: string | null
  actor_ip?: string | null
  user_agent?: string | null
  action: string
  resource_type: string
  resource_id?: string | null
  resource_name?: string | null
  status: string
  error_message?: string | null
}

type AuditLogsResponse = {
  data: AuditLogRow[]
  count: number
}

async function apiGet<T>(path: string): Promise<T> {
  const token = localStorage.getItem("access_token")
  if (!token) throw new Error("未登录")
  const base = import.meta.env.VITE_API_URL
  const res = await fetch(`${base}${path}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  if (res.status === 401) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
    throw new Error("登录已过期")
  }
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}))
    throw new Error(payload.detail || `请求失败: ${res.status}`)
  }
  return res.json()
}

function CopyText({ text }: { text: string }) {
  const [copiedText, copy] = useCopyToClipboard()
  const isCopied = copiedText === text
  return (
    <button
      type="button"
      className="font-mono text-xs text-muted-foreground hover:text-foreground"
      onClick={() => copy(text)}
      title={isCopied ? "已复制" : "点击复制"}
    >
      {text}
    </button>
  )
}

export const Route = createFileRoute("/_layout/audit-logs")({
  component: AuditLogsPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "操作日志 - 测试管理平台" }],
  }),
})

function AuditLogsPage() {
  const [rows, setRows] = useState<AuditLogRow[]>([])
  const [count, setCount] = useState<number>(0)
  const [isLoading, setIsLoading] = useState(false)

  const [q, setQ] = useState("")
  const [actorUserId, setActorUserId] = useState("")
  const [action, setAction] = useState("")
  const [resourceType, setResourceType] = useState("")
  const [resourceId, setResourceId] = useState("")
  const [status, setStatus] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set("skip", "0")
    params.set("limit", "200")
    if (q.trim()) params.set("q", q.trim())
    if (actorUserId.trim()) params.set("actor_user_id", actorUserId.trim())
    if (action.trim()) params.set("action", action.trim())
    if (resourceType.trim()) params.set("resource_type", resourceType.trim())
    if (resourceId.trim()) params.set("resource_id", resourceId.trim())
    if (status.trim()) params.set("status", status.trim())
    if (startDate.trim()) params.set("start_date", startDate.trim())
    if (endDate.trim()) params.set("end_date", endDate.trim())
    return params.toString()
  }, [q, actorUserId, action, resourceType, resourceId, status, startDate, endDate])

  const load = async () => {
    setIsLoading(true)
    try {
      const res = await apiGet<AuditLogsResponse>(`/api/v1/audit-logs/?${query}`)
      setRows(res.data || [])
      setCount(res.count || 0)
    } catch (e: any) {
      toast.error(e.message || "加载失败")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="p-6 space-y-6">
      <Card className="border border-border shadow-sm">
      <CardHeader className="border-b border-border bg-muted/30">
        <CardTitle className="text-base">筛选条件</CardTitle>
      </CardHeader>
        <CardContent className="p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">关键词</div>
              <Input value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">操作者ID</div>
              <Input
                value={actorUserId}
                onChange={(e) => setActorUserId(e.target.value)}
                placeholder="UUID"
              />
            </div>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">动作</div>
              <Input value={action} onChange={(e) => setAction(e.target.value)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">资源类型</div>
              <Input
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value)}
                placeholder="user/item/execution/..."
              />
            </div>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">资源ID</div>
              <Input value={resourceId} onChange={(e) => setResourceId(e.target.value)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">结果</div>
              <Input value={status} onChange={(e) => setStatus(e.target.value)} placeholder="success/failure" />
            </div>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">开始时间</div>
              <Input value={startDate} onChange={(e) => setStartDate(e.target.value)} placeholder="2026-02-13T00:00:00" />
            </div>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">结束时间</div>
              <Input value={endDate} onChange={(e) => setEndDate(e.target.value)} placeholder="2026-02-13T23:59:59" />
            </div>
            <div className="flex items-end gap-3">
              <Button onClick={load} disabled={isLoading} className="h-10 px-6">
                {isLoading ? "加载中..." : "刷新"}
              </Button>
              <div className="text-sm text-muted-foreground">共 {count} 条</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border border-border shadow-sm">
        <CardHeader className="border-b border-border bg-muted/30">
          <CardTitle className="text-lg font-semibold text-foreground">
            列表（最多展示 200 条）
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead>时间</TableHead>
                  <TableHead>操作者</TableHead>
                  <TableHead>动作</TableHead>
                  <TableHead>资源</TableHead>
                  <TableHead>结果</TableHead>
                  <TableHead>Request ID</TableHead>
                  <TableHead>错误</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-10">
                      暂无数据
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="text-sm text-foreground/80">
                        {r.created_at ?? "-"}
                      </TableCell>
                      <TableCell className="text-sm text-foreground/80">
                        {r.actor_email || r.actor_user_id || "-"}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {r.action}
                      </TableCell>
                      <TableCell className="text-sm text-foreground/80">
                        <div className="font-mono text-xs text-foreground/80">
                          {r.resource_type}:{r.resource_id || "-"}
                        </div>
                        {r.resource_name && (
                          <div className="text-xs text-muted-foreground">
                            {r.resource_name}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        <span
                          className={
                            r.status === "success"
                              ? "text-primary"
                              : r.status === "failure"
                                ? "text-destructive"
                                : "text-muted-foreground"
                          }
                        >
                          {r.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        {r.request_id ? <CopyText text={r.request_id} /> : "-"}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[360px] truncate">
                        {r.error_message || "-"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

