<template>
  <div class="page">
    <div class="page-header"><h2>联网检索（公司概述）</h2></div>
    <el-row :gutter="20">
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>Tavily 配置
            <el-tag style="margin-left:8px" :type="cfg.configured ? 'success' : 'info'">{{ cfg.configured ? '已配置' : '未配置' }}</el-tag>
          </template>
          <el-form label-width="120px">
            <el-form-item label="API Key" required>
              <el-input v-model="form.api_key" :placeholder="cfg.api_key_masked || 'tvly-xxxxxxxx'" show-password />
            </el-form-item>
            <el-form-item label="搜索条数">
              <el-input-number v-model="form.max_results" :min="1" :max="10" />
              <span class="tip" style="margin-left:8px">每次检索取前 N 条结果交给模型总结</span>
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="form.enabled" />
              <span class="tip" style="margin-left:8px">关闭后识别时不再联网，只读名片上的信息</span>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card style="margin-top:16px">
          <template #header>总结用文本模型（OpenAI 兼容，不需要视觉能力）
            <el-tag style="margin-left:8px" :type="cfg.llm_configured ? 'success' : 'info'">{{ cfg.llm_configured ? '已配置' : '未配置' }}</el-tag>
          </template>
          <el-form label-width="120px">
            <el-form-item label="接口地址" required><el-input v-model="form.llm_base_url" placeholder="https://api.openai.com/v1" /></el-form-item>
            <el-form-item label="API Key" required><el-input v-model="form.llm_api_key" :placeholder="cfg.llm_api_key_masked || 'sk-...'" show-password /></el-form-item>
            <el-form-item label="模型名" required><el-input v-model="form.llm_model" placeholder="例如 gpt-4o-mini / deepseek-chat / qwen-plus" /></el-form-item>
            <el-form-item label="max_tokens"><el-input-number v-model="form.llm_max_tokens" :min="200" :max="32000" :step="100" /></el-form-item>
          </el-form>
          <el-button type="primary" :loading="saving" @click="save">保存全部配置</el-button>
        </el-card>

        <el-card style="margin-top:16px">
          <template #header>测试一下</template>
          <el-form label-width="120px">
            <el-form-item label="公司名"><el-input v-model="test.company" placeholder="例如：株式会社コメ兵" /></el-form-item>
            <el-form-item label="官网（可选）"><el-input v-model="test.website" placeholder="https://" /></el-form-item>
          </el-form>
          <el-button :loading="testing" :disabled="!cfg.configured || !cfg.llm_configured || !test.company" @click="runTest">检索并总结</el-button>
          <div v-if="result" style="margin-top:12px">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="官网"><a v-if="result.website" :href="result.website" target="_blank">{{ result.website }}</a><span v-else class="tip">未找到</span></el-descriptions-item>
              <el-descriptions-item label="主营业务关键词">{{ result.businessKeywords }}</el-descriptions-item>
              <el-descriptions-item label="主营产品/服务类型">{{ result.productServiceType }}</el-descriptions-item>
              <el-descriptions-item label="公司概述">{{ result.summary }}</el-descriptions-item>
            </el-descriptions>
            <div class="tip" style="margin-top:8px">来源：
              <a v-for="s in result.sources" :key="s.url" :href="s.url" target="_blank" style="margin-right:8px">{{ s.title || s.url }}</a>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>怎么用</template>
          <ol class="steps">
            <li>到 <a href="https://app.tavily.com" target="_blank">app.tavily.com</a> 注册（可用 Google/GitHub 登录），在控制台复制 API Key（以 <code>tvly-</code> 开头）。免费额度每月 1000 次检索。</li>
            <li>配一个<b>文本模型</b>做总结（任何 OpenAI 兼容接口：OpenAI、DeepSeek、通义千问、月之暗面等，便宜的小模型就行），与名片识别用的视觉模型互不影响。</li>
            <li>保存后用「测试一下」填个公司名验证。</li>
            <li>之后每次识别名片：识别出公司名 → Tavily 搜索 → 文本模型总结，自动填好 <b>官网</b>（名片上没印时）、<b>主营业务关键词</b>、<b>主营产品/服务类型</b>，并显示公司概述；结果可手工修改后再录入。</li>
            <li>识别页也有「重新检索」按钮，改了公司名后可以再搜一次。</li>
          </ol>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type EnrichOut, type SearchConfig } from '@/api'

const cfg = reactive<SearchConfig>({
  provider: 'tavily', api_key_masked: '', enabled: true, max_results: 5, configured: false,
  llm_base_url: 'https://api.openai.com/v1', llm_api_key_masked: '', llm_model: '', llm_max_tokens: 1500, llm_configured: false,
})
const form = reactive({ api_key: '', enabled: true, max_results: 5, llm_base_url: 'https://api.openai.com/v1', llm_api_key: '', llm_model: '', llm_max_tokens: 1500 })
const test = reactive({ company: '', website: '' })
const saving = ref(false)
const testing = ref(false)
const result = ref<EnrichOut | null>(null)

async function load() {
  Object.assign(cfg, await api.searchConfig())
  Object.assign(form, {
    api_key: '', enabled: cfg.enabled, max_results: cfg.max_results,
    llm_base_url: cfg.llm_base_url, llm_api_key: '', llm_model: cfg.llm_model, llm_max_tokens: cfg.llm_max_tokens,
  })
}
async function save() {
  saving.value = true
  try {
    Object.assign(cfg, await api.saveSearchConfig(form))
    form.api_key = ''
    form.llm_api_key = ''
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}
async function runTest() {
  testing.value = true
  result.value = null
  try {
    result.value = await api.testSearch({ company: test.company, website: test.website })
  } finally {
    testing.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.steps { padding-left: 18px; line-height: 1.9; }
code { background: #f4f4f5; padding: 1px 4px; border-radius: 3px; }
</style>
