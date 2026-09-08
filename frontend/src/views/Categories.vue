<template>
  <div class="page">
    <div class="page-header">
      <h2>名片分类（金山表格 tab）</h2>
      <div>
        <el-button @click="loadSheets" :loading="sheetsLoading">查看金山现有工作表</el-button>
        <el-button type="primary" @click="openCreate">新建分类</el-button>
      </div>
    </div>
    <el-alert type="info" :closable="false" style="margin-bottom:12px"
      title="每个分类对应金山表格中的一个工作表（tab）。新建分类时会自动在金山表格中新建同名工作表并写好表头。" />

    <el-table :data="rows" v-loading="loading" stripe>
      <el-table-column label="排序" prop="sort_order" width="70" />
      <el-table-column label="标识" prop="key" width="120" />
      <el-table-column label="分类名（大类列）" prop="label" width="150" />
      <el-table-column label="金山工作表名" prop="sheet_name" width="180">
        <template #default="{ row }">
          {{ row.sheet_name }}
          <el-tag v-if="sheets.length" size="small" :type="sheets.includes(row.sheet_name) ? 'success' : 'warning'" style="margin-left:6px">
            {{ sheets.includes(row.sheet_name) ? '已存在' : '金山中不存在' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="说明" prop="description" min-width="160" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }"><el-switch v-model="row.is_active" @change="(v: boolean) => api.updateCategory(row.id, { is_active: v })" /></template>
      </el-table-column>
      <el-table-column label="操作" width="230">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" link type="primary" @click="ensure(row)">在金山中创建/校验 tab</el-button>
          <el-popconfirm title="确定删除该分类？（不会删除金山工作表）" @confirm="remove(row)">
            <template #reference><el-button size="small" link type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="editing ? '编辑分类' : '新建分类'" width="480px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="标识（英文）" required>
          <el-input v-model="form.key" :disabled="!!editing" placeholder="如 finance，小写字母/数字/下划线" />
        </el-form-item>
        <el-form-item label="分类名" required><el-input v-model="form.label" placeholder="写入“大类”列，如 金融" /></el-form-item>
        <el-form-item label="金山工作表名" required><el-input v-model="form.sheet_name" placeholder="如 7 金融" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" /></el-form-item>
        <el-form-item v-if="!editing" label="同步新建 tab">
          <el-switch v-model="form.create_sheet" />
          <span class="tip" style="margin-left:8px">在金山表格中自动新建该工作表并写入表头</span>
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
import { api, type Category } from '@/api'

const rows = ref<Category[]>([])
const sheets = ref<string[]>([])
const loading = ref(false)
const sheetsLoading = ref(false)
const visible = ref(false)
const saving = ref(false)
const editing = ref<Category | null>(null)
const form = reactive({ key: '', label: '', sheet_name: '', description: '', sort_order: 0, create_sheet: true })

async function load() {
  loading.value = true
  try { rows.value = await api.categories(true) } finally { loading.value = false }
}
async function loadSheets() {
  sheetsLoading.value = true
  try {
    sheets.value = (await api.testKdocs()).sheets
    ElMessage.success(`金山表格现有工作表：${sheets.value.join('、')}`)
  } finally { sheetsLoading.value = false }
}
function openCreate() {
  editing.value = null
  Object.assign(form, { key: '', label: '', sheet_name: '', description: '', sort_order: rows.value.length, create_sheet: true })
  visible.value = true
}
function openEdit(row: Category) {
  editing.value = row
  Object.assign(form, { key: row.key, label: row.label, sheet_name: row.sheet_name, description: row.description, sort_order: row.sort_order })
  visible.value = true
}
async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await api.updateCategory(editing.value.id, { label: form.label, sheet_name: form.sheet_name, description: form.description, sort_order: form.sort_order })
    } else {
      await api.createCategory({ ...form })
    }
    ElMessage.success('已保存')
    visible.value = false
    load()
  } finally { saving.value = false }
}
async function ensure(row: Category) {
  const r: any = await api.ensureSheet(row.id)
  ElMessage.success(r.created ? `已在金山表格中新建工作表「${row.sheet_name}」` : `工作表「${row.sheet_name}」已存在`)
  sheets.value = r.sheets || sheets.value
}
async function remove(row: Category) {
  await api.deleteCategory(row.id)
  load()
}
onMounted(load)
</script>
