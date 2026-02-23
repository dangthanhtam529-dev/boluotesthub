import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { Body_register_register as RegisterData } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

const formSchema = z
  .object({
    email: z.email({ message: "请输入有效的邮箱地址" }),
    full_name: z.string().min(1, { message: "姓名不能为空" }),
    password: z
      .string()
      .min(1, { message: "密码不能为空" })
      .min(8, { message: "密码至少需要8个字符" }),
    confirm_password: z
      .string()
      .min(1, { message: "请确认密码" }),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "两次输入的密码不一致",
    path: ["confirm_password"],
  })

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "注册 - 测试管理平台",
      },
    ],
  }),
})

function SignUp() {
  const { signUpMutation } = useAuth()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (signUpMutation.isPending) return
    const registerData: RegisterData = {
      email: data.email,
      full_name: data.full_name,
      password: data.password,
    }
    signUpMutation.mutate(registerData)
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="space-y-5"
        >
          {/* 标题 */}
          <div className="text-center">
            <h2 className="text-lg font-medium text-foreground">
              创建账号
            </h2>
            <p className="text-muted-foreground mt-1 text-xs">
              填写以下信息完成注册
            </p>
          </div>

          {/* 表单 */}
          <div className="space-y-4">
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm">姓名</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="请输入姓名"
                      className="h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm">邮箱</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="请输入邮箱"
                      type="email"
                      className="h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm">密码</FormLabel>
                  <FormControl>
                    <PasswordInput
                      placeholder="请输入密码"
                      className="h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="confirm_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm">确认密码</FormLabel>
                  <FormControl>
                    <PasswordInput
                      placeholder="请再次输入密码"
                      className="h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <LoadingButton
            type="submit"
            loading={signUpMutation.isPending}
            className="w-full h-10"
          >
            注册
          </LoadingButton>

          <p className="text-center text-xs text-muted-foreground">
            已有账号？{" "}
            <RouterLink
              to="/login"
              className="text-primary hover:underline"
            >
              登录
            </RouterLink>
          </p>
        </form>
      </Form>
    </AuthLayout>
  )
}

export default SignUp
