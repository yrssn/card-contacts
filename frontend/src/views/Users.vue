<template>
  <div class="page">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="openCreate">发放账号</el-button>
    </div>
    <el-alert type="info" :closable="false" style="margin-bottom:12px"
      title="管理员在这里给需要使用系统的人创建账号。用户录入名片时，“导入人”列会自动填写其显示名。停用后该用户立即无法登录。" />

    <el-table :data="rows" v-loading="loading" stripe>
      <el-table-column label="ID" prop="id" width="60" />
      <el-table-column label="用户名" prop="username" width="160" />
      <el-table-column label="显示名（导入人）" prop="display_name" width="180" />
      <el-table-column label="角色" width="100">
        <template #default="{ row }"><el-tag :type="row.role === 'admin' ? 'danger' : 'info'">{{ row.role === 'admin' ? '管理员' : '用户' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-switch v-model="row.is_active" :disabled="row.id === store.user?.id" @change="(v: boolean) => toggle(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="创建时间" min-width="160">
        <template #default="{ row }">{{ new Date(row.created_at + 'Z').toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除该用户？" @confirm="remove(row)">
            <template #reference><el-button size="small" link type="danger" :disabled="row.id === store.user?.id">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="editing ? '编辑用户' : '发放账号'" width="440px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="用户名" required><el-input v-model="form.username" :disabled="!!editing" /></el-form-item>
        <el-form-item label="显示名" required><el-input v-model="form.display_name" placeholder="录入时作为“导入人”" /></el-form-item>
        <el-form-item label="密码" :required="!editing"><el-input v-model="form.password" type="password" show-password :placeholder="editing ? '留空则不修改' : '至少 6 位'" /></el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio value="user">普通用户</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type User } from '@/api'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const rows = ref<User[]>([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const editing = ref<User | null>(null)
const form = reactive({ username: '', display_name: '', password: '', role: 'user' as 'user' | 'admin' })

async function load() {
  loading.value = true
  try { rows.value = await api.users() } finally { loading.value = false }
}
function openCreate() {
  editing.value = null
  Object.assign(form, { username: '', display_name: '', password: '', role: 'user' })
  visible.value = true
}
function openEdit(row: User) {
  editing.value = row
  Object.assign(form, { username: row.username, display_name: row.display_name, password: '', role: row.role })
  visible.value = true
}
async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await api.updateUser(editing.value.id, { display_name: form.display_name, role: form.role, password: form.password || undefined })
    } else {
      if (form.password.length < 6) return ElMessage.warning('密码至少 6 位')
      await api.createUser({ ...form })
    }
    ElMessage.success('已保存')
    visible.value = false
    load()
  } finally { saving.value = false }
}
async function toggle(row: User, v: boolean) {
  try { await api.updateUser(row.id, { is_active: v }) } catch { row.is_active = !v }
}
async function remove(row: User) { await api.deleteUser(row.id); load() }
onMounted(load)
</script>
