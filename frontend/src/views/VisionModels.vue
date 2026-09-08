<template>
  <div class="page">
    <div class="page-header">
      <h2>多模态视觉模型</h2>
      <el-button type="primary" @click="openCreate">添加模型</el-button>
    </div>
    <el-alert type="warning" :closable="false" style="margin-bottom:12px"
      title="必须是支持图片输入的视觉模型（如 gpt-4o、qwen-vl-max、glm-4v、doubao-vision 等）。保存时系统会发送一张测试图片验证模型是否真的能“看图”，不通过不允许保存。" />

    <el-table :data="rows" v-loading="loading" stripe>
      <el-table-column label="名称" prop="name" width="160" />
      <el-table-column label="服务商" prop="provider" width="110" />
      <el-table-column label="模型" prop="model" width="200" />
      <el-table-column label="Base URL" prop="base_url" min-width="220" show-overflow-tooltip />
      <el-table-column label="API Key" prop="api_key_masked" width="140" />
      <el-table-column label="视觉验证" width="110">
        <template #default="{ row }">
          <el-tooltip :content="row.verify_message || '未验证'">
            <el-tag :type="row.vision_verified ? 'success' : 'danger'">{{ row.vision_verified ? '通过' : '未通过' }}</el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="默认" width="80">
        <template #default="{ row }"><el-tag v-if="row.is_default" type="primary">默认</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="verify(row)">重新验证</el-button>
          <el-button size="small" link type="primary" :disabled="row.is_default" @click="setDefault(row)">设为默认</el-button>
          <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="remove(row)">
            <template #reference><el-button size="small" link type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="editing ? '编辑模型' : '添加模型'" width="560px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="名称" required><el-input v-model="form.name" placeholder="给这个配置起个名字" /></el-form-item>
        <el-form-item label="服务商">
          <el-select v-model="form.provider" @change="applyPreset">
            <el-option v-for="p in presets" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL" required><el-input v-model="form.base_url" /></el-form-item>
        <el-form-item label="API Key" required><el-input v-model="form.api_key" type="password" show-password :placeholder="editing ? '留空则不修改' : ''" /></el-form-item>
        <el-form-item label="模型名" required>
          <el-input v-model="form.model" placeholder="如 gpt-4o / qwen-vl-max" />
        </el-form-item>
        <el-row>
          <el-col :span="12"><el-form-item label="max_tokens"><el-input-number v-model="form.max_tokens" :min="200" :max="8000" :step="100" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="temperature"><el-input-number v-model="form.temperature" :min="0" :max="1" :step="0.1" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="设为默认"><el-switch v-model="form.is_default" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ saving ? '验证视觉能力中…' : '验证并保存' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type VisionModel } from '@/api'

const presets = [
  { value: 'openai', label: 'OpenAI', base_url: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { value: 'qwen', label: '阿里通义千问', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-vl-max' },
  { value: 'zhipu', label: '智谱 GLM', base_url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4v-plus' },
  { value: 'doubao', label: '火山引擎 豆包', base_url: 'https://ark.cn-beijing.volces.com/api/v3', model: 'doubao-1.5-vision-pro-32k' },
  { value: 'moonshot', label: 'Moonshot Kimi', base_url: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k-vision-preview' },
  { value: 'openrouter', label: 'OpenRouter', base_url: 'https://openrouter.ai/api/v1', model: 'openai/gpt-4o' },
  { value: 'custom', label: '自定义（OpenAI 兼容）', base_url: '', model: '' },
]

const rows = ref<VisionModel[]>([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const editing = ref<VisionModel | null>(null)
const form = reactive({ name: '', provider: 'openai', base_url: presets[0].base_url, api_key: '', model: presets[0].model, max_tokens: 1500, temperature: 0, is_default: false })

function applyPreset(v: string) {
  const p = presets.find((x) => x.value === v)
  if (p && p.base_url) { form.base_url = p.base_url; form.model = p.model }
}
async function load() {
  loading.value = true
  try { rows.value = await api.models() } finally { loading.value = false }
}
function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', provider: 'openai', base_url: presets[0].base_url, api_key: '', model: presets[0].model, max_tokens: 1500, temperature: 0, is_default: rows.value.length === 0 })
  visible.value = true
}
function openEdit(row: VisionModel) {
  editing.value = row
  Object.assign(form, { name: row.name, provider: row.provider, base_url: row.base_url, api_key: '', model: row.model, max_tokens: row.max_tokens, temperature: row.temperature, is_default: row.is_default })
  visible.value = true
}
async function save() {
  saving.value = true
  try {
    const data = { ...form, api_key: form.api_key || (editing.value ? editing.value.api_key_masked : '') }
    if (editing.value) await api.updateModel(editing.value.id, data)
    else await api.createModel(data)
    ElMessage.success('视觉能力验证通过，已保存')
    visible.value = false
    load()
  } finally { saving.value = false }
}
async function verify(row: VisionModel) {
  const r = await api.verifyModel(row.id)
  r.vision_verified ? ElMessage.success(r.verify_message) : ElMessage.error(r.verify_message)
  load()
}
async function setDefault(row: VisionModel) { await api.defaultModel(row.id); load() }
async function remove(row: VisionModel) { await api.deleteModel(row.id); load() }
onMounted(load)
</script>
