<template>
  <div class="page">
    <div class="page-header"><h2>金山文档同步配置</h2></div>
    <el-row :gutter="20">
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>连接参数
            <el-tag style="margin-left:8px" :type="cfg.configured ? 'success' : 'info'">{{ cfg.configured ? '已配置' : '未配置' }}</el-tag>
          </template>
          <el-form label-width="120px">
            <el-form-item label="表格链接"><el-input v-model="form.doc_url" placeholder="https://www.kdocs.cn/l/xxxx（仅备注用）" /></el-form-item>
            <el-form-item label="file_id" required><el-input v-model="form.file_id" placeholder="脚本 API 调用地址中 file/ 后面的数字" /></el-form-item>
            <el-form-item label="script_id" required><el-input v-model="form.script_id" placeholder="脚本 API 调用地址中 script/ 后面的 ID" /></el-form-item>
            <el-form-item label="AirScript-Token" required><el-input v-model="form.token" type="password" show-password :placeholder="cfg.token_masked ? `已保存 ${cfg.token_masked}，留空则不修改` : ''" /></el-form-item>
          </el-form>
          <div style="display:flex; gap:10px">
            <el-button type="primary" :loading="saving" @click="save">保存</el-button>
            <el-button :loading="testing" :disabled="!cfg.configured" @click="test">测试连接</el-button>
          </div>
          <el-alert v-if="testResult" style="margin-top:12px" :type="testResult.ok ? 'success' : 'error'" :closable="false"
            :title="testResult.ok ? `连接成功，脚本版本 ${testResult.version}` : testResult.error">
            <div v-if="testResult.ok">现有工作表：{{ testResult.sheets.join('、') }}</div>
          </el-alert>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>配置步骤</template>
          <ol class="steps">
            <li>打开金山文档里的名片表格，确保各分类的工作表（tab）已按 <b>A~P</b> 列表头建好（P 列为「导入人」，新建 tab 时脚本会自动写表头）。</li>
            <li>菜单 <b>效率 → 脚本编辑器（AirScript）</b>，新建脚本，把仓库中 <code>kdocs/kdocs-airscript.js</code> 全部内容粘贴进去并保存。</li>
            <li>点击脚本编辑器右上角 <b>发布 → API 调用</b>，会得到形如
              <code>https://www.kdocs.cn/api/v3/ide/file/<b>{file_id}</b>/script/<b>{script_id}</b>/sync_task</code> 的地址和一个 <b>AirScript-Token</b>。</li>
            <li>把 file_id、script_id、Token 填到左侧并保存，点「测试连接」应看到现有工作表列表。</li>
            <li>后端 <code>.env</code> 里的 <code>PUBLIC_BASE_URL</code> 必须是公网可访问地址，金山文档才能拉取名片照片插入表格。</li>
          </ol>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type KdocsConfig } from '@/api'

const cfg = reactive<KdocsConfig>({ file_id: '', script_id: '', token_masked: '', doc_url: '', configured: false })
const form = reactive({ file_id: '', script_id: '', token: '', doc_url: '' })
const saving = ref(false)
const testing = ref(false)
const testResult = ref<any>(null)

async function load() {
  Object.assign(cfg, await api.kdocsConfig())
  Object.assign(form, { file_id: cfg.file_id, script_id: cfg.script_id, token: '', doc_url: cfg.doc_url })
}
async function save() {
  saving.value = true
  try {
    Object.assign(cfg, await api.saveKdocsConfig({ ...form, token: form.token || cfg.token_masked }))
    form.token = ''
    ElMessage.success('已保存')
  } finally { saving.value = false }
}
async function test() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await api.testKdocs()
  } catch (e: any) {
    testResult.value = { ok: false, error: e.response?.data?.detail || '连接失败' }
  } finally { testing.value = false }
}
onMounted(load)
</script>

<style scoped>
.steps { padding-left: 20px; line-height: 1.9; font-size: 14px; }
code { background: #f4f4f5; padding: 1px 5px; border-radius: 3px; }
</style>
