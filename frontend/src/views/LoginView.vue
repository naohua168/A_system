<template>
  <div class="login-page">
    <!-- 左侧品牌区 -->
    <div class="login-brand">
      <div class="brand-content">
        <div class="brand-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="12" fill="#0066cc"/>
            <path d="M12 36V16L22 26L28 18L38 30" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="32" cy="14" r="4" fill="white" fill-opacity="0.8"/>
          </svg>
        </div>
        <h1 class="brand-title">StockAI</h1>
        <p class="brand-subtitle">智能金融分析平台</p>
        <div class="brand-features">
          <div class="feature" v-for="f in features" :key="f.text">
            <el-icon color="#2997ff" :size="18"><Check /></el-icon>
            <span>{{ f.text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="login-form-panel">
      <div class="form-container">
        <div class="form-header">
          <h2 class="form-title">{{ isRegister ? '创建账户' : '欢迎回来' }}</h2>
          <p class="form-subtitle">{{ isRegister ? '开始您的智能投资之旅' : '登录您的账户继续' }}</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="login-form"
          @submit.prevent="handleSubmit"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              size="large"
              show-password
            />
          </el-form-item>

          <el-form-item v-if="isRegister" prop="email">
            <el-input
              v-model="form.email"
              placeholder="邮箱（选填）"
              :prefix-icon="Message"
              size="large"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="loading"
              @click="handleSubmit"
            >
              {{ isRegister ? '注册' : '登录' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="form-footer">
          <span>{{ isRegister ? '已有账户？' : '还没有账户？' }}</span>
          <a class="toggle-link" @click="isRegister = !isRegister">
            {{ isRegister ? '立即登录' : '立即注册' }}
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message, Check } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const isRegister = ref(false)

const form = reactive({
  username: '',
  password: '',
  email: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
}

const features = [
  { text: '实时行情与K线技术分析' },
  { text: '缠论智能中枢识别' },
  { text: '多维度量化指标' },
  { text: 'AI智能对话分析' },
]

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    if (isRegister.value) {
      await userStore.register(form.username, form.password)
    } else {
      await userStore.login(form.username, form.password)
    }
    router.push('/home')
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  display: flex;
  height: 100vh;
  background: $canvas;
}

.login-brand {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a1e 0%, #2a2a2e 100%);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -30%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(0,102,204,0.08) 0%, transparent 70%);
    border-radius: 50%;
  }
}

.brand-content {
  text-align: center;
  z-index: 1;
  padding: $spacing-xxl;
}

.brand-icon {
  margin-bottom: $spacing-lg;
}

.brand-title {
  font-family: $font-display;
  font-size: 42px;
  font-weight: 600;
  color: white;
  letter-spacing: -0.28px;
  margin-bottom: $spacing-xs;
}

.brand-subtitle {
  font-size: 18px;
  color: rgba(255,255,255,0.6);
  margin-bottom: $spacing-xxl;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  text-align: left;
  max-width: 240px;
  margin: 0 auto;
}

.feature {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: 15px;
  color: rgba(255,255,255,0.75);
}

.login-form-panel {
  width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $spacing-xxl;
}

.form-container {
  width: 100%;
  max-width: 360px;
}

.form-header {
  margin-bottom: $spacing-xl;

  .form-title {
    font-family: $font-display;
    font-size: 28px;
    font-weight: 600;
    color: $ink;
    letter-spacing: -0.28px;
    margin-bottom: $spacing-xs;
  }

  .form-subtitle {
    font-size: 15px;
    color: $ink-muted-48;
  }
}

.login-form {
  :deep(.el-input__wrapper) {
    border-radius: $rounded-md;
    padding: 4px 16px;
    box-shadow: 0 0 0 1px $hairline;
    transition: box-shadow 0.2s;

    &:hover {
      box-shadow: 0 0 0 1px $ink-muted-48;
    }

    &.is-focus {
      box-shadow: 0 0 0 2px $primary;
    }
  }

  :deep(.el-input__inner) {
    height: 48px;
    font-size: 15px;
  }

  :deep(.el-form-item) {
    margin-bottom: 20px;
  }
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  border-radius: $rounded-pill;
}

.form-footer {
  text-align: center;
  margin-top: $spacing-lg;
  font-size: 14px;
  color: $ink-muted-48;

  .toggle-link {
    color: $primary;
    cursor: pointer;
    margin-left: 4px;
    font-weight: 500;

    &:hover {
      color: $primary-focus;
    }
  }
}
</style>
