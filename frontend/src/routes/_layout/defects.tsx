import { createFileRoute } from "@tanstack/react-router"
import {
  Bug,
  Plus,
  RefreshCw,
  Trash2,
  Eye,
  Edit,
  Search,
  AlertCircle,
  AlertTriangle,
  AlertOctagon,
  Info,
  Lightbulb,
  Loader2,
  Code,
  Merge,
  TrendingUp,
  BarChart3,
  Upload,
  Download,
  FileJson,
  FileSpreadsheet,
} from "lucide-react"
import { useEffect, useState, useRef } from "react"
import { toast } from "sonner"

import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"

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

interface Defect {
  id: string
  project_id: string
  title: string
  description: string | null
  source: string
  source_id: string | null
  api_path: string | null
  api_method: string | null
  module: string | null
  error_type: string | null
  request_data: string | null
  response_data: string | null
  error_detail: string | null
  severity: string
  tags: string[] | null
  fingerprint: string | null
  occurrence_count: number
  ai_analysis: string | null
  ai_suggestion: string | null
  created_at: string
  updated_at: string
}

interface DefectStats {
  total: number
  by_source: Record<string, number>
  by_severity: Record<string, number>
  by_error_type: Record<string, number>
  by_module: Record<string, number>
  recent_count: number
  duplicate_count: number
}

interface DefectTrend {
  date: string
  count: number
  by_severity: Record<string, number>
}

interface Project {
  id: string
  name: string
}

interface Enums {
  source: Record<string, string>
  severity: Record<string, string>
  error_type: Record<string, string>
}

interface DefectsPublic {
  data: Defect[]
  count: number
}

interface ImportPreview {
  record_id: string | null
  total_count: number
  new_count: number
  duplicate_count: number
  error_count: number
  preview_data: Record<string, unknown>[]
  field_mapping: Record<string, string>
  errors: Record<string, unknown>[]
}

interface ImportResult {
  record_id: string
  status: string
  total_count: number
  new_count: number
  duplicate_count: number
  error_count: number
  details: Record<string, unknown>[]
}

interface ImportPlatform {
  value: string
  label: string
}

export const Route = createFileRoute("/_layout/defects")({
  component: DefectsPage,
  head: () => ({
    meta: [
      {
        title: "缺陷管理 - 测试管理平台",
      },
    ],
  }),
})

function DefectsPage() {
  const [defects, setDefects] = useState<Defect[]>([])
  const [stats, setStats] = useState<DefectStats | null>(null)
  const [trends, setTrends] = useState<DefectTrend[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [enums, setEnums] = useState<Enums | null>(null)
  const [modules, setModules] = useState<string[]>([])
  const [apiPaths, setApiPaths] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProject, setSelectedProject] = useState<string>("")
  const [searchKeyword, setSearchKeyword] = useState("")
  const [filterSource, setFilterSource] = useState<string>("")
  const [filterSeverity, setFilterSeverity] = useState<string>("")
  const [filterErrorType, setFilterErrorType] = useState<string>("")
  const [filterModule, setFilterModule] = useState<string>("")

  const [dialogOpen, setDialogOpen] = useState(false)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [editingDefect, setEditingDefect] = useState<Defect | null>(null)
  const [viewingDefect, setViewingDefect] = useState<Defect | null>(null)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState("list")

  const [importDialogOpen, setImportDialogOpen] = useState(false)
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null)
  const [importRecordId, setImportRecordId] = useState<string>("")
  const [importing, setImporting] = useState(false)
  const [importPlatforms, setImportPlatforms] = useState<ImportPlatform[]>([])
  const [selectedPlatform, setSelectedPlatform] = useState<string>("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [defectForm, setDefectForm] = useState({
    title: "",
    description: "",
    source: "manual",
    api_path: "",
    api_method: "",
    module: "",
    error_type: "",
    request_data: "",
    response_data: "",
    error_detail: "",
    severity: "normal",
    tags: "",
  })

  useEffect(() => {
    fetchProjects()
    fetchEnums()
    fetchImportPlatforms()
  }, [])

  useEffect(() => {
    if (selectedProject) {
      fetchDefects()
      fetchStats()
      fetchTrends()
      fetchModules()
      fetchApiPaths()
    }
  }, [selectedProject, filterSource, filterSeverity, filterErrorType, filterModule, searchKeyword])

  const fetchProjects = async () => {
    try {
      const data = await apiGet<{ data: Project[] }>("/api/v1/projects/")
      setProjects(data.data || [])
      if (data.data && data.data.length > 0 && !selectedProject) {
        setSelectedProject(data.data[0].id)
      } else {
        setLoading(false)
      }
    } catch (error) {
      console.error("Failed to fetch projects:", error)
      setLoading(false)
    }
  }

  const fetchEnums = async () => {
    try {
      const data = await apiGet<Enums>("/api/v1/defects/enums")
      setEnums(data)
    } catch (error) {
      console.error("Failed to fetch enums:", error)
    }
  }

  const fetchDefects = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append("project_id", selectedProject)
      if (filterSource) params.append("source", filterSource)
      if (filterSeverity) params.append("severity", filterSeverity)
      if (filterErrorType) params.append("error_type", filterErrorType)
      if (filterModule) params.append("module", filterModule)
      if (searchKeyword) params.append("keyword", searchKeyword)

      const data = await apiGet<DefectsPublic>(`/api/v1/defects/?${params.toString()}`)
      setDefects(data.data || [])
    } catch (error) {
      console.error("Failed to fetch defects:", error)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const data = await apiGet<DefectStats>(`/api/v1/defects/stats?project_id=${selectedProject}`)
      setStats(data)
    } catch (error) {
      console.error("Failed to fetch stats:", error)
    }
  }

  const fetchTrends = async () => {
    try {
      const data = await apiGet<DefectTrend[]>(`/api/v1/defects/trend?project_id=${selectedProject}&days=14`)
      setTrends(data || [])
    } catch (error) {
      console.error("Failed to fetch trends:", error)
    }
  }

  const fetchModules = async () => {
    try {
      const data = await apiGet<string[]>(`/api/v1/defects/modules?project_id=${selectedProject}`)
      setModules(data || [])
    } catch (error) {
      console.error("Failed to fetch modules:", error)
    }
  }

  const fetchApiPaths = async () => {
    try {
      const data = await apiGet<string[]>(`/api/v1/defects/api-paths?project_id=${selectedProject}`)
      setApiPaths(data || [])
    } catch (error) {
      console.error("Failed to fetch api paths:", error)
    }
  }

  const fetchImportPlatforms = async () => {
    try {
      const data = await apiGet<ImportPlatform[]>("/api/v1/defects/import/platforms")
      setImportPlatforms(data || [])
    } catch (error) {
      console.error("Failed to fetch import platforms:", error)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !selectedProject) return

    const allowedTypes = ["application/json", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel", "text/csv"]
    const fileExt = file.name.toLowerCase().split(".").pop()
    
    if (!["json", "xlsx", "xls", "csv"].includes(fileExt || "")) {
      toast.error("不支持的文件格式，请上传 JSON 或 Excel 文件")
      return
    }

    setImporting(true)
    try {
      const formData = new FormData()
      formData.append("file", file)
      
      const params = new URLSearchParams()
      params.append("project_id", selectedProject)
      if (selectedPlatform) {
        params.append("platform", selectedPlatform)
      }

      const response = await fetch(`/api/v1/defects/import/upload?${params.toString()}`, {
        method: "POST",
        body: formData,
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "上传失败")
      }

      const data: ImportPreview = await response.json()
      setImportPreview(data)
      setImportRecordId(data.record_id || "")
      setImportDialogOpen(true)
      toast.success(`解析成功，共 ${data.total_count} 条记录`)
    } catch (error) {
      console.error("Failed to upload file:", error)
      toast.error(error instanceof Error ? error.message : "上传失败")
    } finally {
      setImporting(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  const handleConfirmImport = async () => {
    if (!importRecordId) return

    setImporting(true)
    try {
      const result = await apiPost<ImportResult>(
        `/api/v1/defects/import/confirm/${importRecordId}`,
        importPreview?.field_mapping || {}
      )

      toast.success(`导入完成：新增 ${result.new_count} 条，重复 ${result.duplicate_count} 条`)
      setImportDialogOpen(false)
      setImportPreview(null)
      setImportRecordId("")
      fetchDefects()
      fetchStats()
    } catch (error) {
      console.error("Failed to confirm import:", error)
      toast.error("导入失败")
    } finally {
      setImporting(false)
    }
  }

  const handleDownloadTemplate = async (platform: string) => {
    try {
      const response = await fetch(`/api/v1/defects/import/template/${platform}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      })
      
      const data = await response.json()
      const blob = new Blob([JSON.stringify(data.sample_data, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `defect_template_${platform}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success("模板已下载")
    } catch (error) {
      console.error("Failed to download template:", error)
      toast.error("下载模板失败")
    }
  }

  const handleCreateDefect = () => {
    setEditingDefect(null)
    setDefectForm({
      title: "",
      description: "",
      source: "manual",
      api_path: "",
      api_method: "",
      module: "",
      error_type: "",
      request_data: "",
      response_data: "",
      error_detail: "",
      severity: "normal",
      tags: "",
    })
    setDialogOpen(true)
  }

  const handleEditDefect = (defect: Defect) => {
    setEditingDefect(defect)
    setDefectForm({
      title: defect.title,
      description: defect.description || "",
      source: defect.source,
      api_path: defect.api_path || "",
      api_method: defect.api_method || "",
      module: defect.module || "",
      error_type: defect.error_type || "",
      request_data: defect.request_data || "",
      response_data: defect.response_data || "",
      error_detail: defect.error_detail || "",
      severity: defect.severity,
      tags: defect.tags?.join(", ") || "",
    })
    setDialogOpen(true)
  }

  const handleViewDefect = (defect: Defect) => {
    setViewingDefect(defect)
    setDetailDialogOpen(true)
  }

  const handleSaveDefect = async () => {
    if (!defectForm.title.trim()) {
      toast.error("请输入缺陷标题")
      return
    }

    setSaving(true)
    try {
      const tags = defectForm.tags
        ? defectForm.tags.split(",").map((t) => t.trim()).filter((t) => t)
        : null

      const body: Record<string, unknown> = {
        title: defectForm.title,
        description: defectForm.description || null,
        source: defectForm.source,
        api_path: defectForm.api_path || null,
        api_method: defectForm.api_method || null,
        module: defectForm.module || null,
        error_type: defectForm.error_type || null,
        request_data: defectForm.request_data || null,
        response_data: defectForm.response_data || null,
        error_detail: defectForm.error_detail || null,
        severity: defectForm.severity,
        tags: tags,
      }

      if (editingDefect) {
        await apiPut(`/api/v1/defects/${editingDefect.id}?project_id=${selectedProject}`, body)
      } else {
        await apiPost(`/api/v1/defects/?project_id=${selectedProject}`, body)
      }

      toast.success(editingDefect ? "缺陷已更新" : "缺陷已创建")
      setDialogOpen(false)
      fetchDefects()
      fetchStats()
    } catch (error) {
      console.error("Failed to save defect:", error)
      toast.error("操作失败")
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteDefect = async (defectId: string) => {
    if (!confirm("确定要删除这个缺陷吗？")) return

    try {
      await apiDelete(`/api/v1/defects/${defectId}?project_id=${selectedProject}`)
      toast.success("缺陷已删除")
      fetchDefects()
      fetchStats()
    } catch (error) {
      console.error("Failed to delete defect:", error)
      toast.error("删除失败")
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "critical":
        return <AlertOctagon className="h-4 w-4 text-red-600" />
      case "major":
        return <AlertTriangle className="h-4 w-4 text-amber-500 dark:text-amber-400" />
      case "normal":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />
      case "minor":
        return <Info className="h-4 w-4 text-primary" />
      case "suggestion":
        return <Lightbulb className="h-4 w-4 text-muted-foreground" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-50 text-red-700 border-red-200/60"
      case "major":
        return "bg-orange-50 text-orange-700 border-orange-200"
      case "normal":
        return "bg-yellow-50 text-yellow-700 border-yellow-200"
      case "minor":
        return "bg-primary/10 text-primary border-primary/20"
      case "suggestion":
        return "bg-muted text-foreground/80 border-border"
      default:
        return "bg-muted text-foreground/80 border-border"
    }
  }

  const getSourceColor = (source: string) => {
    switch (source) {
      case "manual":
        return "bg-primary/10 text-primary"
      case "execution":
        return "bg-red-50 text-red-700"
      case "import":
        return "bg-green-50 text-green-700"
      default:
        return "bg-muted text-foreground"
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  const formatJson = (jsonStr: string | null) => {
    if (!jsonStr) return ""
    try {
      return JSON.stringify(JSON.parse(jsonStr), null, 2)
    } catch {
      return jsonStr
    }
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bug className="h-6 w-6" />
            缺陷管理
          </h1>
          <p className="text-muted-foreground mt-1">收集和分析测试缺陷</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedProject} onValueChange={setSelectedProject}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="选择项目" />
            </SelectTrigger>
            <SelectContent>
              {projects.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleCreateDefect} disabled={!selectedProject}>
            <Plus className="h-4 w-4 mr-2" />
            新增缺陷
          </Button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".json,.xlsx,.xls,.csv"
            className="hidden"
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={!selectedProject || importing}
          >
            {importing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Upload className="h-4 w-4 mr-2" />
            )}
            导入
          </Button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">总计</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">近7天新增</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">{stats.recent_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">重复缺陷</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">{stats.duplicate_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">执行失败</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{stats.by_source?.execution || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">致命/严重</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-700">
                {(stats.by_severity?.critical || 0) + (stats.by_severity?.major || 0)}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="list">缺陷列表</TabsTrigger>
          <TabsTrigger value="analysis">统计分析</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4 mb-4 flex-wrap">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="搜索缺陷..."
                    value={searchKeyword}
                    onChange={(e) => setSearchKeyword(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <Select value={filterSource} onValueChange={setFilterSource}>
                  <SelectTrigger className="w-[120px]">
                    <SelectValue placeholder="来源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">全部来源</SelectItem>
                    {enums &&
                      Object.entries(enums.source).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <Select value={filterSeverity} onValueChange={setFilterSeverity}>
                  <SelectTrigger className="w-[120px]">
                    <SelectValue placeholder="严重程度" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">全部程度</SelectItem>
                    {enums &&
                      Object.entries(enums.severity).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <Select value={filterErrorType} onValueChange={setFilterErrorType}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="错误类型" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">全部类型</SelectItem>
                    {enums &&
                      Object.entries(enums.error_type).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <Select value={filterModule} onValueChange={setFilterModule}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="模块" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">全部模块</SelectItem>
                    {modules.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="outline" size="icon" onClick={fetchDefects}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : defects.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {selectedProject ? "暂无缺陷数据" : "请先选择项目"}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[120px]">Bug编号</TableHead>
                      <TableHead className="w-[250px]">标题</TableHead>
                      <TableHead>严重程度</TableHead>
                      <TableHead>错误类型</TableHead>
                      <TableHead>模块</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {defects.map((defect) => (
                      <TableRow key={defect.id}>
                        <TableCell className="font-mono text-sm text-muted-foreground">
                          {defect.source_id || "-"}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getSeverityIcon(defect.severity)}
                            <span className="font-medium truncate max-w-[200px]" title={defect.title}>{defect.title}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={getSeverityColor(defect.severity)}>
                            {enums?.severity[defect.severity] || defect.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {defect.error_type ? (
                            <Badge variant="secondary">
                              {enums?.error_type[defect.error_type] || defect.error_type}
                            </Badge>
                          ) : (
                            "-"
                          )}
                        </TableCell>
                        <TableCell>{defect.module || "-"}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="icon" onClick={() => handleViewDefect(defect)}>
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => handleEditDefect(defect)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive"
                              onClick={() => handleDeleteDefect(defect.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analysis">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  按严重程度分布
                </CardTitle>
              </CardHeader>
              <CardContent>
                {stats && enums ? (
                  <div className="space-y-3">
                    {Object.entries(stats.by_severity).map(([severity, count]) => (
                      <div key={severity} className="flex items-center gap-3">
                        <div className="w-20 text-sm">{enums.severity[severity] || severity}</div>
                        <div className="flex-1 bg-muted rounded-full h-4 overflow-hidden">
                          <div
                            className={`h-full ${getSeverityColor(severity)}`}
                            style={{ width: `${(count / stats.total) * 100}%` }}
                          />
                        </div>
                        <div className="w-10 text-sm text-right">{count}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted-foreground">暂无数据</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-5 w-5" />
                  按错误类型分布
                </CardTitle>
              </CardHeader>
              <CardContent>
                {stats && enums && Object.keys(stats.by_error_type).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(stats.by_error_type).map(([errorType, count]) => (
                      <div key={errorType} className="flex items-center gap-3">
                        <div className="w-28 text-sm">{enums.error_type[errorType] || errorType}</div>
                        <div className="flex-1 bg-muted rounded-full h-4 overflow-hidden">
                          <div
                            className="h-full bg-primary"
                            style={{ width: `${(count / stats.total) * 100}%` }}
                          />
                        </div>
                        <div className="w-10 text-sm text-right">{count}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted-foreground">暂无数据</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  近14天趋势
                </CardTitle>
              </CardHeader>
              <CardContent>
                {trends.length > 0 ? (
                  <div className="space-y-2">
                    {trends.slice(-7).map((trend) => (
                      <div key={trend.date} className="flex items-center gap-3">
                        <div className="w-20 text-sm">{trend.date}</div>
                        <div className="flex-1 bg-muted rounded-full h-4 overflow-hidden">
                          <div
                            className="h-full bg-emerald-500"
                            style={{
                              width: `${Math.max((trend.count / Math.max(...trends.map((t) => t.count), 1)) * 100, trend.count > 0 ? 5 : 0)}%`,
                            }}
                          />
                        </div>
                        <div className="w-10 text-sm text-right">{trend.count}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted-foreground">暂无数据</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Merge className="h-5 w-5" />
                  按来源分布
                </CardTitle>
              </CardHeader>
              <CardContent>
                {stats && enums ? (
                  <div className="space-y-3">
                    {Object.entries(stats.by_source).map(([source, count]) => (
                      <div key={source} className="flex items-center gap-3">
                        <div className="w-20 text-sm">{enums.source[source] || source}</div>
                        <div className="flex-1 bg-muted rounded-full h-4 overflow-hidden">
                          <div
                            className={`h-full ${getSourceColor(source)}`}
                            style={{ width: `${(count / stats.total) * 100}%` }}
                          />
                        </div>
                        <div className="w-10 text-sm text-right">{count}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted-foreground">暂无数据</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingDefect ? "编辑缺陷" : "新增缺陷"}</DialogTitle>
            <DialogDescription>
              {editingDefect ? "修改缺陷信息" : "填写缺陷详细信息"}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="title">标题 *</Label>
              <Input
                id="title"
                value={defectForm.title}
                onChange={(e) => setDefectForm({ ...defectForm, title: e.target.value })}
                placeholder="缺陷标题"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="severity">严重程度</Label>
                <Select
                  value={defectForm.severity}
                  onValueChange={(v) => setDefectForm({ ...defectForm, severity: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择严重程度" />
                  </SelectTrigger>
                  <SelectContent>
                    {enums &&
                      Object.entries(enums.severity).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="source">来源</Label>
                <Select
                  value={defectForm.source}
                  onValueChange={(v) => setDefectForm({ ...defectForm, source: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择来源" />
                  </SelectTrigger>
                  <SelectContent>
                    {enums &&
                      Object.entries(enums.source).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="api_method">HTTP方法</Label>
                <Select
                  value={defectForm.api_method}
                  onValueChange={(v) => setDefectForm({ ...defectForm, api_method: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择方法" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GET">GET</SelectItem>
                    <SelectItem value="POST">POST</SelectItem>
                    <SelectItem value="PUT">PUT</SelectItem>
                    <SelectItem value="DELETE">DELETE</SelectItem>
                    <SelectItem value="PATCH">PATCH</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="api_path">API路径</Label>
                <Input
                  id="api_path"
                  value={defectForm.api_path}
                  onChange={(e) => setDefectForm({ ...defectForm, api_path: e.target.value })}
                  placeholder="/api/v1/example"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="module">模块</Label>
                <Input
                  id="module"
                  value={defectForm.module}
                  onChange={(e) => setDefectForm({ ...defectForm, module: e.target.value })}
                  placeholder="所属模块"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="error_type">错误类型</Label>
                <Select
                  value={defectForm.error_type}
                  onValueChange={(v) => setDefectForm({ ...defectForm, error_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择错误类型" />
                  </SelectTrigger>
                  <SelectContent>
                    {enums &&
                      Object.entries(enums.error_type).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                value={defectForm.description}
                onChange={(e) => setDefectForm({ ...defectForm, description: e.target.value })}
                placeholder="缺陷描述"
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="error_detail">错误详情</Label>
              <Textarea
                id="error_detail"
                value={defectForm.error_detail}
                onChange={(e) => setDefectForm({ ...defectForm, error_detail: e.target.value })}
                placeholder="错误详细信息"
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="request_data">请求数据 (JSON)</Label>
              <Textarea
                id="request_data"
                value={defectForm.request_data}
                onChange={(e) => setDefectForm({ ...defectForm, request_data: e.target.value })}
                placeholder='{"key": "value"}'
                rows={3}
                className="font-mono text-sm"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="response_data">响应数据 (JSON)</Label>
              <Textarea
                id="response_data"
                value={defectForm.response_data}
                onChange={(e) => setDefectForm({ ...defectForm, response_data: e.target.value })}
                placeholder='{"code": 500, "message": "error"}'
                rows={3}
                className="font-mono text-sm"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tags">标签 (逗号分隔)</Label>
              <Input
                id="tags"
                value={defectForm.tags}
                onChange={(e) => setDefectForm({ ...defectForm, tags: e.target.value })}
                placeholder="标签1, 标签2, 标签3"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSaveDefect} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editingDefect ? "更新" : "创建"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>缺陷详情</DialogTitle>
          </DialogHeader>
          {viewingDefect && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">标题</Label>
                  <div className="font-medium">{viewingDefect.title}</div>
                </div>
                <div>
                  <Label className="text-muted-foreground">严重程度</Label>
                  <div>
                    <Badge variant="outline" className={getSeverityColor(viewingDefect.severity)}>
                      {enums?.severity[viewingDefect.severity] || viewingDefect.severity}
                    </Badge>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label className="text-muted-foreground">来源</Label>
                  <div>
                    <Badge className={getSourceColor(viewingDefect.source)}>
                      {enums?.source[viewingDefect.source] || viewingDefect.source}
                    </Badge>
                  </div>
                </div>
                <div>
                  <Label className="text-muted-foreground">错误类型</Label>
                  <div>
                    {viewingDefect.error_type ? (
                      <Badge variant="secondary">
                        {enums?.error_type[viewingDefect.error_type] || viewingDefect.error_type}
                      </Badge>
                    ) : (
                      "-"
                    )}
                  </div>
                </div>
                <div>
                  <Label className="text-muted-foreground">重复次数</Label>
                  <div>{viewingDefect.occurrence_count} 次</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">API</Label>
                  <div>
                    {viewingDefect.api_path ? (
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {viewingDefect.api_method} {viewingDefect.api_path}
                      </code>
                    ) : (
                      "-"
                    )}
                  </div>
                </div>
                <div>
                  <Label className="text-muted-foreground">模块</Label>
                  <div>{viewingDefect.module || "-"}</div>
                </div>
              </div>
              {viewingDefect.description && (
                <div>
                  <Label className="text-muted-foreground">描述</Label>
                  <div className="whitespace-pre-wrap bg-muted p-3 rounded mt-1">
                    {viewingDefect.description}
                  </div>
                </div>
              )}
              {viewingDefect.error_detail && (
                <div>
                  <Label className="text-muted-foreground">错误详情</Label>
                  <div className="whitespace-pre-wrap bg-destructive/10 text-destructive p-3 rounded mt-1">
                    {viewingDefect.error_detail}
                  </div>
                </div>
              )}
              {viewingDefect.request_data && (
                <div>
                  <Label className="text-muted-foreground">请求数据</Label>
                  <pre className="bg-muted p-3 rounded mt-1 text-sm overflow-x-auto">
                    {formatJson(viewingDefect.request_data)}
                  </pre>
                </div>
              )}
              {viewingDefect.response_data && (
                <div>
                  <Label className="text-muted-foreground">响应数据</Label>
                  <pre className="bg-muted p-3 rounded mt-1 text-sm overflow-x-auto">
                    {formatJson(viewingDefect.response_data)}
                  </pre>
                </div>
              )}
              {viewingDefect.tags && viewingDefect.tags.length > 0 && (
                <div>
                  <Label className="text-muted-foreground">标签</Label>
                  <div className="flex gap-1 mt-1">
                    {viewingDefect.tags.map((tag, i) => (
                      <Badge key={i} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
                <div>创建时间: {formatDate(viewingDefect.created_at)}</div>
                <div>更新时间: {formatDate(viewingDefect.updated_at)}</div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailDialogOpen(false)}>
              关闭
            </Button>
            {viewingDefect && (
              <Button onClick={() => {
                setDetailDialogOpen(false)
                handleEditDefect(viewingDefect)
              }}>
                编辑
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              导入预览
            </DialogTitle>
            <DialogDescription>
              确认导入数据，系统将自动去重
            </DialogDescription>
          </DialogHeader>
          
          {importPreview && (
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{importPreview.total_count}</div>
                    <div className="text-sm text-muted-foreground">总记录数</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-green-600">{importPreview.new_count}</div>
                    <div className="text-sm text-muted-foreground">新增</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-orange-600">{importPreview.duplicate_count}</div>
                    <div className="text-sm text-muted-foreground">重复</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-red-600">{importPreview.error_count}</div>
                    <div className="text-sm text-muted-foreground">错误</div>
                  </CardContent>
                </Card>
              </div>

              {importPreview.errors && importPreview.errors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded p-3">
                  <div className="font-medium text-red-700 mb-2">解析错误</div>
                  <div className="text-sm text-red-700 space-y-1">
                    {importPreview.errors.slice(0, 5).map((err, i) => (
                      <div key={i}>
                        第 {(err as Record<string, unknown>).index as number + 1} 条: {(err as Record<string, unknown>).error as string}
                      </div>
                    ))}
                    {importPreview.errors.length > 5 && (
                      <div>...还有 {importPreview.errors.length - 5} 条错误</div>
                    )}
                  </div>
                </div>
              )}

              <div>
                <div className="font-medium mb-2">预览数据（前20条）</div>
                <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                    <TableHead className="w-[120px]">Bug编号</TableHead>
                    <TableHead className="w-[250px]">标题</TableHead>
                    <TableHead>严重程度</TableHead>
                    <TableHead>Bug类型</TableHead>
                    <TableHead>模块</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {importPreview.preview_data.map((item, i) => {
                      const d = item as Record<string, unknown>
                      return (
                        <TableRow key={i}>
                          <TableCell className="font-mono text-sm text-muted-foreground">{d.external_id as string || "-"}</TableCell>
                          <TableCell className="font-medium truncate max-w-[230px]" title={d.title as string}>{d.title as string || "-"}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className={getSeverityColor(d.severity as string)}>
                              {enums?.severity[d.severity as string] || d.severity as string}
                            </Badge>
                          </TableCell>
                          <TableCell>{d.error_type as string || "-"}</TableCell>
                          <TableCell>{d.module as string || "-"}</TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleConfirmImport} disabled={importing}>
              {importing ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              确认导入
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
