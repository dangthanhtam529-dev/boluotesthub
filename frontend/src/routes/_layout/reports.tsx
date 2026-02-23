import { createFileRoute, redirect } from "@tanstack/react-router"
import { useMemo, useState, useEffect } from "react"
import { toast } from "sonner"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { isLoggedIn } from "@/hooks/useAuth"

type TrendRow = {
  _id: string
  count: number
  avg_response_time?: number | null
  avg_failed?: number | null
}

type FailedApiRow = {
  _id: any
  fail_count: number
  last_fail?: string
  error_messages?: string[]
  status_codes?: any[]
}

type PerformanceRow = {
  avg_response_time?: number | null
  max_response_time?: number | null
  min_response_time?: number | null
  total_executions?: number | null
}

type CompareResult = {
  left: any
  right: any
  left_profile?: any
  right_profile?: any
  diff: {
    new_failures_count: number
    resolved_failures_count: number
    new_failures: any[]
    resolved_failures: any[]
    metrics: Record<string, any>
    request_stats?: {
      left?: any
      right?: any
    }
    slow_compare?: any
  }
}

type OverviewData = {
  totals: {
    executions: number
    tests_total: number
    tests_passed: number
    tests_failed: number
    tests_pending: number
  }
  pass_rate?: number | null
  avg_response_time?: number | null
  status_buckets?: Record<string, number>
  validation?: Record<string, number>
  slow_apis?: any[]
  top_signatures?: any[]
}

type SlowApisResult = {
  mode: "window" | "compare"
  data: any[]
}

function decodeBody(body: any): string | null {
  if (body == null) return null
  if (typeof body === "string") return body
  if (Array.isArray(body) && body.length > 0 && typeof body[0] === "number") {
    const slice = body.slice(0, 2000)
    try {
      return new TextDecoder().decode(Uint8Array.from(slice))
    } catch {
      return String.fromCharCode(...slice.map((n) => Number(n) & 0xff))
    }
  }
  if (typeof body === "object") {
    try {
      return JSON.stringify(body)
    } catch {
      return String(body)
    }
  }
  return String(body)
}

type ExecutionListResponse = {
  data: Array<{
    apifox_collection_id: string
    project_name?: string | null
  }>
  count: number
}

function BarRow({
  label,
  value,
  max,
  colorClass,
}: {
  label: string
  value: number
  max: number
  colorClass: string
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <div className="w-12 text-xs text-muted-foreground">{label}</div>
      <div className="flex-1 h-2 bg-muted rounded">
        <div
          className={`h-2 rounded ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="w-10 text-right text-xs text-muted-foreground">{value}</div>
    </div>
  )
}

async function apiGet<T>(path: string): Promise<T> {
  const token = localStorage.getItem("access_token")
  if (!token) {
    throw new Error("未登录")
  }
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

async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const token = localStorage.getItem("access_token")
  if (!token) {
    throw new Error("未登录")
  }
  const base = import.meta.env.VITE_API_URL
  const res = await fetch(`${base}${path}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
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

export const Route = createFileRoute("/_layout/reports")({
  component: ReportsPage,
  validateSearch: (search: Record<string, unknown>) => ({
    execution_id: search.execution_id ? String(search.execution_id) : undefined,
  }),
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
  head: () => ({
    meta: [{ title: "报告分析 - 测试管理平台" }],
  }),
})

function ReportsPage() {
  const search = Route.useSearch()
  const [collectionId, setCollectionId] = useState("")
  const [days, setDays] = useState("30")

  const [collections, setCollections] = useState<any[] | null>(null)
  const [overviewData, setOverviewData] = useState<OverviewData | null>(null)
  const [trend, setTrend] = useState<TrendRow[] | null>(null)
  const [failedApis, setFailedApis] = useState<FailedApiRow[] | null>(null)
  const [performance, setPerformance] = useState<PerformanceRow | null>(null)
  const [failureSignatures, setFailureSignatures] = useState<any[] | null>(null)
  const [flaky, setFlaky] = useState<any[] | null>(null)
  const [slowWindow, setSlowWindow] = useState<any[] | null>(null)
  const [slowCompare, setSlowCompare] = useState<any[] | null>(null)
  const [selectedSignature, setSelectedSignature] = useState<string>("")
  const [signatureNote, setSignatureNote] = useState<string>("")
  const [signatureTags, setSignatureTags] = useState<string>("")
  const [detailExecutionId, setDetailExecutionId] = useState<string>("")
  const [detailRows, setDetailRows] = useState<any[] | null>(null)
  const [detailHint, setDetailHint] = useState<string>("")

  const [leftExec, setLeftExec] = useState("")
  const [rightExec, setRightExec] = useState("")
  const [compare, setCompare] = useState<CompareResult | null>(null)
  const [baselineExec, setBaselineExec] = useState("")
  const [targetExec, setTargetExec] = useState("")

  const query = useMemo(() => {
    const params = new URLSearchParams()
    const d = Number(days)
    if (!Number.isNaN(d) && d > 0) params.set("days", String(d))
    const raw = collectionId.trim()
    let normalized = raw
    if (normalized.startsWith("suite-")) normalized = normalized.slice(6)
    if (normalized.startsWith("ts-") || normalized.startsWith("tf-"))
      normalized = normalized.slice(3)
    if (normalized) params.set("collection_id", normalized)
    const qs = params.toString()
    return qs ? `?${qs}` : ""
  }, [collectionId, days])

  useEffect(() => {
    if (search.execution_id) {
      setDetailExecutionId(String(search.execution_id))
    }
  }, [search.execution_id])

  const loadAll = async () => {
    try {
      const [
        overviewRes,
        trendRes,
        failedRes,
        perfRes,
        sigRes,
        flakyRes,
        slowRes,
        executionsRes,
      ] = await Promise.all([
        apiGet<{ data: OverviewData }>(`/api/v1/executions/analytics/overview${query}`),
        apiGet<{ data: TrendRow[] }>(`/api/v1/executions/analytics/trend${query}`),
        apiGet<{ data: FailedApiRow[] }>(
          `/api/v1/executions/analytics/failed-apis${query}&limit=10`.replace("?&", "?"),
        ),
        apiGet<{ data: PerformanceRow }>(`/api/v1/executions/analytics/performance${query}`),
        apiGet<{ data: any[] }>(
          `/api/v1/executions/analytics/failure-signatures${query}&limit=10`.replace("?&", "?"),
        ),
        apiGet<{ data: any[] }>(`/api/v1/executions/analytics/flaky${query}&limit=10`.replace("?&", "?")),
        apiGet<{ data: SlowApisResult }>(
          `/api/v1/executions/analytics/slow-apis${query}&limit=10`.replace("?&", "?"),
        ),
        apiGet<ExecutionListResponse>(`/api/v1/executions?skip=0&limit=50`),
      ])
      setOverviewData(overviewRes.data || null)
      setTrend(trendRes.data || [])
      setFailedApis(failedRes.data || [])
      setPerformance(perfRes.data || {})
      setFailureSignatures(sigRes.data || [])
      setFlaky(flakyRes.data || [])
      setSlowWindow(slowRes.data?.data || [])
      const counter = new Map<string, { count: number; projectNames: Set<string> }>()
      for (const e of executionsRes.data || []) {
        const id = String(e.apifox_collection_id || "").trim()
        if (!id) continue
        const row = counter.get(id) || { count: 0, projectNames: new Set<string>() }
        row.count += 1
        if (e.project_name) row.projectNames.add(String(e.project_name))
        counter.set(id, row)
      }
      const list = Array.from(counter.entries())
        .map(([id, v]) => ({
          _id: id,
          count: v.count,
          project_names: Array.from(v.projectNames),
        }))
        .sort((a, b) => b.count - a.count)
      setCollections(list)
      toast.success("数据已刷新")
    } catch (e: any) {
      toast.error(e.message || "加载失败")
    }
  }

  const loadSlowCompare = async () => {
    if (!baselineExec.trim() || !targetExec.trim()) {
      toast.error("请输入基线执行ID与目标执行ID")
      return
    }
    try {
      const params = new URLSearchParams()
      const raw = collectionId.trim()
      let normalized = raw
      if (normalized.startsWith("suite-")) normalized = normalized.slice(6)
      if (normalized.startsWith("ts-") || normalized.startsWith("tf-"))
        normalized = normalized.slice(3)
      if (normalized) params.set("collection_id", normalized)
      params.set("days", days.trim() || "30")
      params.set("limit", "20")
      params.set("baseline_execution_id", baselineExec.trim())
      params.set("target_execution_id", targetExec.trim())
      const res = await apiGet<{ data: SlowApisResult }>(
        `/api/v1/executions/analytics/slow-apis?${params.toString()}`,
      )
      setSlowCompare(res.data?.data || [])
      toast.success("慢接口对比完成")
    } catch (e: any) {
      toast.error(e.message || "对比失败")
    }
  }

  const loadSignatureNote = async (signature: string) => {
    setSelectedSignature(signature)
    try {
      const params = new URLSearchParams({
        note_type: "signature",
        note_key: signature,
      })
      const res = await apiGet<{ data: any }>(
        `/api/v1/executions/analytics/note?${params.toString()}`,
      )
      const note = res.data
      setSignatureNote(note?.content || "")
      setSignatureTags((note?.tags || []).join(","))
    } catch (e: any) {
      setSignatureNote("")
      setSignatureTags("")
      toast.error(e.message || "读取备注失败")
    }
  }

  const loadExecutionDetail = async () => {
    const raw = detailExecutionId.trim()
    if (!raw) {
      toast.error("请输入执行ID或集合ID")
      return
    }
    let executionId = raw
    if (/^\d+$/.test(raw)) {
      const res = await apiGet<ExecutionListResponse>(
        `/api/v1/executions?skip=0&limit=1&collection_id=${encodeURIComponent(raw)}`,
      )
      const first = res.data?.[0]
      if (!first?.id) {
        toast.error("这个集合ID下找不到执行记录")
        return
      }
      executionId = String(first.id)
      setDetailExecutionId(executionId)
      setDetailHint(`已自动定位到最新执行：${executionId}`)
    }
    try {
      const payload = await apiGet<any>(`/api/v1/executions/${executionId}/report`)
      const report = payload?.report ?? payload
      const result = report?.result ?? report?.run ?? {}
      const executions = (result?.executions || []) as any[]
      if (!Array.isArray(executions) || executions.length === 0) {
        setDetailRows([])
        setDetailHint("这份报告未包含请求明细（可能是 Apifox 输出模式限制）")
        return
      }

      const failures = (result?.failures || []) as any[]
      const failureMap = new Map<string, any>()
      for (const f of failures) {
        const src = f?.source || {}
        const key = String(src?.name || "")
        if (key) failureMap.set(key, f)
      }

      const rows = executions.slice(0, 200).map((ex: any) => {
        const item = ex?.item || {}
        const req = item?.request || {}
        const url = req?.url || {}
        const pathParts = url?.path
        const apiPath = Array.isArray(pathParts)
          ? `/${pathParts.filter((p: any) => p != null).join("/")}`
          : url?.path || ""
        const method = req?.method

        const resp = ex?.response
        let statusCode: any = null
        let body: any = null
        if (resp && typeof resp === "object" && !Array.isArray(resp)) {
          statusCode = (resp as any).code ?? null
          body = (resp as any).body ?? null
        } else if (Array.isArray(resp) && resp.length > 0) {
          statusCode = resp?.[0]?.code ?? null
          body = resp?.[0]?.body ?? null
        }

        const ok = ex?.passed === true
        const bodyText = decodeBody(body)
        const bodyPreview = bodyText ? bodyText.slice(0, 400) : ""

        let err = ""
        const rv = ex?.responseValidation || {}
        if (rv?.schema?.valid === false && rv?.schema?.message) err = String(rv.schema.message)
        if (!err && rv?.responseCode?.valid === false) err = "返回码校验未通过"
        if (!err) {
          const f = failureMap.get(String(item?.name || "")) || null
          const msg = f?.error?.message
          if (msg) err = String(msg)
        }

        return {
          name: item?.name || "",
          api_path: apiPath,
          method,
          status_code: statusCode,
          latency_ms: ex?.responseTime ?? null,
          ok,
          body_preview: bodyPreview,
          body_full: bodyText || "",
          error: err,
        }
      })
      setDetailHint("")
      setDetailRows(rows)
      toast.success("已加载执行明细")
    } catch (e: any) {
      setDetailRows(null)
      setDetailHint("")
      toast.error(e.message || "加载失败")
    }
  }

  const saveSignatureNote = async () => {
    if (!selectedSignature) {
      toast.error("请先选择一个失败归类")
      return
    }
    try {
      const tags = signatureTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean)
      const res = await apiPut<{ data: any }>(`/api/v1/executions/analytics/note`, {
        note_type: "signature",
        note_key: selectedSignature,
        content: signatureNote,
        tags,
      })
      setSignatureNote(res.data?.content || signatureNote)
      setSignatureTags((res.data?.tags || tags).join(","))
      toast.success("已保存")
    } catch (e: any) {
      toast.error(e.message || "保存失败")
    }
  }

  const loadCompare = async () => {
    if (!leftExec.trim() || !rightExec.trim()) {
      toast.error("请输入左右执行ID")
      return
    }
    try {
      const params = new URLSearchParams({
        left: leftExec.trim(),
        right: rightExec.trim(),
      })
      const res = await apiGet<CompareResult>(
        `/api/v1/executions/analytics/compare?${params.toString()}`,
      )
      setCompare(res)
      toast.success("对比完成")
    } catch (e: any) {
      toast.error(e.message || "对比失败")
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">报告分析</h1>
          <p className="text-sm text-muted-foreground">
            Apifox 负责执行，本模块聚焦报告沉淀与趋势/失败/性能洞察
          </p>
        </div>

        <Card className="border border-border shadow-sm">
          <CardHeader className="border-b border-border bg-muted/50">
            <CardTitle className="text-lg font-semibold text-foreground">
              过滤条件
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row gap-4 items-end">
              <div className="flex-1 space-y-2">
                <label className="text-sm font-medium text-muted-foreground">
                  集合ID（可选）
                </label>
                <Input
                  value={collectionId}
                  onChange={(e) => setCollectionId(e.target.value)}
                  placeholder="例如：8145（测试套件/场景ID，不用加ts-/suite-）"
                  className="h-10"
                />
                {(collections || []).length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    最近有数据的集合ID：
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(collections || []).slice(0, 8).map((c) => (
                        <button
                          key={String(c._id)}
                          type="button"
                          onClick={() => setCollectionId(String(c._id))}
                          className="px-2 py-1 rounded border border-border bg-background hover:bg-muted/50 text-foreground"
                        >
                          {String(c._id)} ({c.count})
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="w-full md:w-40 space-y-2">
                <label className="text-sm font-medium text-muted-foreground">
                  天数
                </label>
                <Input
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                  placeholder="30"
                  className="h-10"
                />
              </div>
              <Button onClick={loadAll} className="h-10 px-6">
                刷新
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="summary">
        <TabsList>
          <TabsTrigger value="summary">概览</TabsTrigger>
          <TabsTrigger value="slow">慢接口</TabsTrigger>
          <TabsTrigger value="signatures">失败归类</TabsTrigger>
          <TabsTrigger value="failedApis">失败API</TabsTrigger>
          <TabsTrigger value="detail">执行明细</TabsTrigger>
          <TabsTrigger value="flaky">不稳定</TabsTrigger>
          <TabsTrigger value="trend">趋势</TabsTrigger>
          <TabsTrigger value="performance">性能</TabsTrigger>
          <TabsTrigger value="compare">对比</TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                本次窗口概览
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="border border-border shadow-sm">
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">执行次数</div>
                    <div className="text-2xl font-bold text-foreground">
                      {overviewData?.totals?.executions ?? "-"}
                    </div>
                  </CardContent>
                </Card>
                <Card className="border border-border shadow-sm">
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">通过率</div>
                    <div className="text-2xl font-bold text-foreground">
                      {overviewData?.pass_rate ?? "-"}%
                    </div>
                  </CardContent>
                </Card>
                <Card className="border border-border shadow-sm">
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">失败用例数</div>
                    <div className="text-2xl font-bold text-foreground">
                      {overviewData?.totals?.tests_failed ?? "-"}
                    </div>
                  </CardContent>
                </Card>
                <Card className="border border-border shadow-sm">
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">平均响应</div>
                    <div className="text-2xl font-bold text-foreground">
                      {overviewData?.avg_response_time ?? "-"}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="border border-border shadow-sm">
                  <CardHeader className="border-b border-border bg-muted/50">
                    <CardTitle className="text-base font-semibold text-foreground">
                      状态码分布
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {(() => {
                      const b = overviewData?.status_buckets || {}
                      const v2xx = Number(b["2xx"] || 0)
                      const v4xx = Number(b["4xx"] || 0)
                      const v5xx = Number(b["5xx"] || 0)
                      const vUnknown = Number(b["unknown"] || 0)
                      const vOther = Number(b["other"] || 0)
                      const max = Math.max(v2xx, v4xx, v5xx, vUnknown, vOther)
                      return (
                        <div className="space-y-2">
                          <BarRow label="2xx" value={v2xx} max={max} colorClass="bg-green-500" />
                          <BarRow label="4xx" value={v4xx} max={max} colorClass="bg-yellow-500" />
                          <BarRow label="5xx" value={v5xx} max={max} colorClass="bg-red-500" />
                          <BarRow label="未知" value={vUnknown} max={max} colorClass="bg-muted-foreground" />
                          <BarRow label="其它" value={vOther} max={max} colorClass="bg-muted-foreground" />
                          {vUnknown > 0 && (
                            <div className="text-xs text-muted-foreground pt-1">
                              说明：当前报告未输出“每条请求明细”，因此状态码只能统计为“未知”
                            </div>
                          )}
                        </div>
                      )
                    })()}
                  </CardContent>
                </Card>
                <Card className="border border-border shadow-sm">
                  <CardHeader className="border-b border-border bg-muted/50">
                    <CardTitle className="text-base font-semibold text-foreground">
                      校验问题
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {(() => {
                      const schemaInvalid = overviewData?.validation?.schema_invalid ?? 0
                      const codeInvalid = overviewData?.validation?.code_invalid ?? 0
                      const unknown = overviewData?.status_buckets?.unknown ?? 0
                      return (
                        <div className="space-y-2">
                          <div className="text-sm text-muted-foreground">
                            结构不通过: {schemaInvalid}，返回码不通过: {codeInvalid}
                          </div>
                          {unknown > 0 && schemaInvalid === 0 && codeInvalid === 0 && (
                            <div className="text-xs text-muted-foreground">
                              说明：当前报告未输出校验明细，暂无法统计更细的校验失败原因
                            </div>
                          )}
                        </div>
                      )
                    })()}
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                慢接口 Top 10（窗口内）
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableHead>API</TableHead>
                      <TableHead>方法</TableHead>
                      <TableHead>平均耗时</TableHead>
                      <TableHead>最大耗时</TableHead>
                      <TableHead>次数</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(overviewData?.slow_apis || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-10">
                          暂无慢接口数据（报告可能未输出请求明细），请点击“刷新”
                        </TableCell>
                      </TableRow>
                    ) : (
                      (overviewData?.slow_apis || []).map((row, idx) => (
                        <TableRow key={`${idx}-${row._id?.api_path}-${row._id?.method}`}>
                          <TableCell className="font-mono text-sm">
                            {row._id?.api_path ?? "-"}
                          </TableCell>
                          <TableCell>{row._id?.method ?? "-"}</TableCell>
                          <TableCell>
                            {row.avg_latency ? Math.round(row.avg_latency) : "-"}
                          </TableCell>
                          <TableCell>
                            {row.max_latency ? Math.round(row.max_latency) : "-"}
                          </TableCell>
                          <TableCell>{row.count ?? "-"}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="slow" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                慢接口（基线对比）
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="flex flex-col md:flex-row gap-4 items-end">
                <div className="flex-1 space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">
                    基线执行ID（通常选上一次成功）
                  </label>
                  <Input
                    value={baselineExec}
                    onChange={(e) => setBaselineExec(e.target.value)}
                    placeholder="UUID"
                    className="h-10"
                  />
                </div>
                <div className="flex-1 space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">
                    目标执行ID（你要对比的这次）
                  </label>
                  <Input
                    value={targetExec}
                    onChange={(e) => setTargetExec(e.target.value)}
                    placeholder="UUID"
                    className="h-10"
                  />
                </div>
                <Button onClick={loadSlowCompare} className="h-10 px-6">
                  对比
                </Button>
              </div>

              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableHead>API</TableHead>
                      <TableHead>方法</TableHead>
                      <TableHead>基线平均</TableHead>
                      <TableHead>目标平均</TableHead>
                      <TableHead>变慢(+) / 变快(-)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(slowCompare || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-10">
                          输入两个执行ID后点击“对比”
                        </TableCell>
                      </TableRow>
                    ) : (
                      (slowCompare || []).map((row) => (
                        <TableRow key={`${row.api_path}-${row.method}`}>
                          <TableCell className="font-mono text-sm">
                            {row.api_path ?? "-"}
                          </TableCell>
                          <TableCell>{row.method ?? "-"}</TableCell>
                          <TableCell>
                            {row.baseline_avg_latency
                              ? Math.round(row.baseline_avg_latency)
                              : "-"}
                          </TableCell>
                          <TableCell>
                            {row.target_avg_latency
                              ? Math.round(row.target_avg_latency)
                              : "-"}
                          </TableCell>
                          <TableCell>
                            {typeof row.delta === "number"
                              ? Math.round(row.delta)
                              : "-"}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                慢接口 Top 10（窗口内）
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableHead>API</TableHead>
                      <TableHead>方法</TableHead>
                      <TableHead>平均耗时</TableHead>
                      <TableHead>最大耗时</TableHead>
                      <TableHead>次数</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(slowWindow || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-10">
                          暂无慢接口数据（报告可能未输出请求明细），请点击“刷新”
                        </TableCell>
                      </TableRow>
                    ) : (
                      (slowWindow || []).map((row, idx) => (
                        <TableRow key={`${idx}-${row._id?.api_path}-${row._id?.method}`}>
                          <TableCell className="font-mono text-sm">
                            {row._id?.api_path ?? "-"}
                          </TableCell>
                          <TableCell>{row._id?.method ?? "-"}</TableCell>
                          <TableCell>
                            {row.avg_latency ? Math.round(row.avg_latency) : "-"}
                          </TableCell>
                          <TableCell>
                            {row.max_latency ? Math.round(row.max_latency) : "-"}
                          </TableCell>
                          <TableCell>{row.count ?? "-"}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="signatures" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                失败归类 Top 10
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableHead>API</TableHead>
                      <TableHead>方法</TableHead>
                      <TableHead>状态码</TableHead>
                      <TableHead>次数</TableHead>
                      <TableHead>示例错误</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(failureSignatures || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-10">
                          暂无失败归类数据（本次窗口内没有失败），请点击“刷新”
                        </TableCell>
                      </TableRow>
                    ) : (
                      (failureSignatures || []).map((row) => (
                        <TableRow
                          key={row._id}
                          onClick={() => loadSignatureNote(String(row._id))}
                          className={
                            selectedSignature === String(row._id)
                              ? "bg-primary/5"
                              : undefined
                          }
                        >
                          <TableCell className="font-mono text-sm">
                            {row.api_path ?? "-"}
                          </TableCell>
                          <TableCell>{row.api_method ?? "-"}</TableCell>
                          <TableCell>{row.response_status ?? "-"}</TableCell>
                          <TableCell>{row.count ?? "-"}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {row.sample_error ?? "-"}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                经验备注（用于下次直接复用）
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="text-sm text-muted-foreground">
                当前选择：{selectedSignature || "未选择（点击上面的某一行）"}
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-muted-foreground">
                  标签（逗号分隔）
                </label>
                <Input
                  value={signatureTags}
                  onChange={(e) => setSignatureTags(e.target.value)}
                  placeholder="例如：鉴权,超时,回归"
                  className="h-10"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-muted-foreground">
                  备注内容（根因/解决方案/链接）
                </label>
                <textarea
                  value={signatureNote}
                  onChange={(e) => setSignatureNote(e.target.value)}
                  placeholder="写清楚：问题是什么、怎么定位、怎么解决、以后怎么避免"
                  className="min-h-32 w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex justify-end">
                <Button onClick={saveSignatureNote} className="h-10 px-6">
                  保存备注
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="flaky" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                不稳定接口 Top 10（有时成功有时失败）
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableHead>API</TableHead>
                      <TableHead>方法</TableHead>
                      <TableHead>总次数</TableHead>
                      <TableHead>失败次数</TableHead>
                      <TableHead>失败率</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(flaky || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-10">
                          暂无不稳定数据（需要多次执行对比才会出现），请点击“刷新”
                        </TableCell>
                      </TableRow>
                    ) : (
                      (flaky || []).map((row) => (
                        <TableRow key={`${row._id?.api_path}-${row._id?.method}`}>
                          <TableCell className="font-mono text-sm">
                            {row._id?.api_path ?? "-"}
                          </TableCell>
                          <TableCell>{row._id?.method ?? "-"}</TableCell>
                          <TableCell>{row.total ?? "-"}</TableCell>
                          <TableCell>{row.failed ?? "-"}</TableCell>
                          <TableCell>
                            {typeof row.failure_rate === "number" ? (
                              <div className="space-y-1">
                                <div className="text-xs text-foreground">
                                  {Math.round(row.failure_rate * 100)}%
                                </div>
                                <div className="h-2 bg-muted rounded">
                                  <div
                                    className="h-2 bg-red-500 rounded"
                                    style={{
                                      width: `${Math.min(
                                        100,
                                        Math.max(0, row.failure_rate * 100),
                                      )}%`,
                                    }}
                                  />
                                </div>
                              </div>
                            ) : (
                              "-"
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trend" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                趋势（按天）
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableHead>日期</TableHead>
                      <TableHead>执行数</TableHead>
                      <TableHead>平均响应</TableHead>
                      <TableHead>平均失败</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(trend || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center py-10">
                          暂无趋势数据，请点击“刷新”
                        </TableCell>
                      </TableRow>
                    ) : (
                      (trend || []).map((row) => (
                        <TableRow key={row._id}>
                          <TableCell>{row._id}</TableCell>
                          <TableCell>{row.count}</TableCell>
                          <TableCell>
                            {row.avg_response_time ?? "-"}
                          </TableCell>
                          <TableCell>{row.avg_failed ?? "-"}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="failedApis" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                高频失败 API（Top 10）
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableHead>API</TableHead>
                      <TableHead>方法</TableHead>
                      <TableHead>状态码</TableHead>
                      <TableHead>失败次数</TableHead>
                      <TableHead>错误示例</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(failedApis || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-10">
                          暂无失败 API 数据（本次窗口内没有失败），请点击“刷新”
                        </TableCell>
                      </TableRow>
                    ) : (
                      (failedApis || []).map((row, idx) => {
                        const apiPath =
                          row._id?.api_path ?? row._id ?? "Unknown"
                        const method = row._id?.api_method ?? "-"
                        const statusCodes = (row.status_codes || []).filter(
                          (x: any) => x != null,
                        )
                        const statusPreview =
                          statusCodes.length > 0
                            ? statusCodes.slice(0, 3).join(",")
                            : "-"
                        const errPreview =
                          row.error_messages && row.error_messages.length > 0
                            ? String(row.error_messages[0]).slice(0, 120)
                            : "-"
                        return (
                          <TableRow key={`${idx}-${apiPath}-${method}`}>
                            <TableCell className="font-mono text-sm">
                              {apiPath}
                            </TableCell>
                            <TableCell>{method}</TableCell>
                            <TableCell>{statusPreview}</TableCell>
                            <TableCell>{row.fail_count}</TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {errPreview}
                            </TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="detail" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                执行明细（状态码/成功返回/失败错误）
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="flex flex-col md:flex-row gap-4 items-end">
                <div className="flex-1 space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">
                    执行ID
                  </label>
                  <Input
                    value={detailExecutionId}
                    onChange={(e) => setDetailExecutionId(e.target.value)}
                    placeholder="执行ID(UUID) 或 集合ID(纯数字)"
                    className="h-10"
                  />
                </div>
                <Button onClick={loadExecutionDetail} className="h-10 px-6">
                  加载
                </Button>
              </div>

              {detailHint && (
                <div className="text-sm text-muted-foreground">{detailHint}</div>
              )}

              {detailRows && (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50 hover:bg-muted/50">
                        <TableHead>API</TableHead>
                        <TableHead>方法</TableHead>
                        <TableHead>状态码</TableHead>
                        <TableHead>耗时</TableHead>
                        <TableHead>成功返回（预览）</TableHead>
                        <TableHead>失败提示</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detailRows.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-10">
                            暂无明细
                          </TableCell>
                        </TableRow>
                      ) : (
                        detailRows.map((r, idx) => (
                          <TableRow key={`${idx}-${r.api_path}-${r.method}`}>
                            <TableCell className="font-mono text-sm">
                              {r.api_path || "-"}
                            </TableCell>
                            <TableCell>{r.method || "-"}</TableCell>
                            <TableCell>{r.status_code ?? "-"}</TableCell>
                            <TableCell>{r.latency_ms ?? "-"}</TableCell>
                            <TableCell className="text-sm text-foreground">
                              {r.ok ? (
                                r.body_preview ? (
                                  <details>
                                    <summary className="cursor-pointer">
                                      {r.body_preview}
                                    </summary>
                                    <pre className="whitespace-pre-wrap break-words text-xs mt-2">
                                      {r.body_full}
                                    </pre>
                                  </details>
                                ) : (
                                  "未记录返回内容"
                                )
                              ) : (
                                "-"
                              )}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {r.ok ? "-" : r.error || "失败但未提供错误信息"}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                性能统计
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="border border-border shadow-sm">
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">平均响应</div>
                    <div className="text-2xl font-bold text-foreground">
                      {performance?.avg_response_time ?? "-"}
                    </div>
                  </CardContent>
                </Card>
                <Card className="border border-border shadow-sm">
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">最大响应</div>
                    <div className="text-2xl font-bold text-foreground">
                      {performance?.max_response_time ?? "-"}
                    </div>
                  </CardContent>
                </Card>
                <Card className="border border-border shadow-sm">
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">最小响应</div>
                    <div className="text-2xl font-bold text-foreground">
                      {performance?.min_response_time ?? "-"}
                    </div>
                  </CardContent>
                </Card>
                <Card className="border border-border shadow-sm">
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">执行次数</div>
                    <div className="text-2xl font-bold text-foreground">
                      {performance?.total_executions ?? "-"}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="compare" className="space-y-4">
          <Card className="border border-border shadow-sm">
            <CardHeader className="border-b border-border bg-muted/50">
              <CardTitle className="text-lg font-semibold text-foreground">
                执行对比
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="flex flex-col md:flex-row gap-4 items-end">
                <div className="flex-1 space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">
                    Left 执行ID
                  </label>
                  <Input
                    value={leftExec}
                    onChange={(e) => setLeftExec(e.target.value)}
                    placeholder="UUID"
                    className="h-10"
                  />
                </div>
                <div className="flex-1 space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">
                    Right 执行ID
                  </label>
                  <Input
                    value={rightExec}
                    onChange={(e) => setRightExec(e.target.value)}
                    placeholder="UUID"
                    className="h-10"
                  />
                </div>
                <Button onClick={loadCompare} className="h-10 px-6">
                  对比
                </Button>
              </div>

              {compare && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card className="border border-border shadow-sm">
                      <CardContent className="p-5">
                        <div className="text-sm text-muted-foreground">新增失败</div>
                        <div className="text-2xl font-bold text-foreground">
                          {compare.diff.new_failures_count}
                        </div>
                      </CardContent>
                    </Card>
                    <Card className="border border-border shadow-sm">
                      <CardContent className="p-5">
                        <div className="text-sm text-muted-foreground">修复失败</div>
                        <div className="text-2xl font-bold text-foreground">
                          {compare.diff.resolved_failures_count}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <Card className="border border-border shadow-sm">
                    <CardHeader className="border-b border-border bg-muted/50">
                      <CardTitle className="text-lg font-semibold text-foreground">
                        新增失败（最多 50）
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/50 hover:bg-muted/50">
                              <TableHead>API</TableHead>
                              <TableHead>方法</TableHead>
                              <TableHead>状态码</TableHead>
                              <TableHead>错误</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {compare.diff.new_failures.length === 0 ? (
                              <TableRow>
                                <TableCell
                                  colSpan={4}
                                  className="text-center py-10"
                                >
                                  无
                                </TableCell>
                              </TableRow>
                            ) : (
                              compare.diff.new_failures.map((f) => (
                                <TableRow key={f.fingerprint}>
                                  <TableCell className="font-mono text-sm">
                                    {f.api_path || "-"}
                                  </TableCell>
                                  <TableCell>{f.api_method || "-"}</TableCell>
                                  <TableCell>{f.response_status ?? "-"}</TableCell>
                                  <TableCell className="text-sm text-muted-foreground">
                                    {f.error || "-"}
                                  </TableCell>
                                </TableRow>
                              ))
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>

                  {compare.diff.slow_compare?.data?.length > 0 && (
                    <Card className="border border-border shadow-sm">
                      <CardHeader className="border-b border-border bg-muted/50">
                        <CardTitle className="text-lg font-semibold text-foreground">
                          变慢接口（Top 20）
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="p-0">
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-muted/50 hover:bg-muted/50">
                                <TableHead>API</TableHead>
                                <TableHead>方法</TableHead>
                                <TableHead>基线平均</TableHead>
                                <TableHead>目标平均</TableHead>
                                <TableHead>差值</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {compare.diff.slow_compare.data.map((row: any) => (
                                <TableRow key={`${row.api_path}-${row.method}`}>
                                  <TableCell className="font-mono text-sm">
                                    {row.api_path ?? "-"}
                                  </TableCell>
                                  <TableCell>{row.method ?? "-"}</TableCell>
                                  <TableCell>
                                    {row.baseline_avg_latency
                                      ? Math.round(row.baseline_avg_latency)
                                      : "-"}
                                  </TableCell>
                                  <TableCell>
                                    {row.target_avg_latency
                                      ? Math.round(row.target_avg_latency)
                                      : "-"}
                                  </TableCell>
                                  <TableCell>
                                    {typeof row.delta === "number"
                                      ? Math.round(row.delta)
                                      : "-"}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
