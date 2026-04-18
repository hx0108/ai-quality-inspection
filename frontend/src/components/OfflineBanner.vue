<template>
  <div class="offline-banner" :class="bannerClass">
    <div class="banner-content">
      <!-- 离线图标 -->
      <van-icon v-if="!isOnline" name="wap-nav-o" class="banner-icon" />
      <van-icon v-else-if="syncing" name="replay" class="banner-icon spinning" />
      <van-icon v-else-if="conflictCount > 0" name="warning-o" class="banner-icon" />
      <van-icon v-else name="passed" class="banner-icon" />

      <!-- 文字 -->
      <span class="banner-text">
        <template v-if="!isOnline && pendingCount === 0">当前无网络连接</template>
        <template v-else-if="!isOnline">离线模式 | {{ pendingCount }}条待同步</template>
        <template v-else-if="syncing">{{ syncProgress || '正在同步...' }}</template>
        <template v-else-if="conflictCount > 0">已同步，{{ pendingCount }}条冲突</template>
        <template v-else-if="pendingCount > 0">{{ pendingCount }}条待同步</template>
        <template v-else>所有记录已同步</template>
      </span>

      <!-- 手动同步按钮 -->
      <van-button
        v-if="isOnline && pendingCount > 0 && !syncing"
        size="small"
        type="primary"
        plain
        class="sync-btn"
        @click="$emit('retry-sync')"
      >
        立即同步
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isOnline: { type: Boolean, default: true },
  pendingCount: { type: Number, default: 0 },
  syncing: { type: Boolean, default: false },
  syncProgress: { type: String, default: '' },
  conflictCount: { type: Number, default: 0 }
})

const emit = defineEmits(['retry-sync'])

const bannerClass = computed(() => {
  if (!props.isOnline) return 'banner-offline'
  if (props.syncing) return 'banner-syncing'
  if (props.conflictCount > 0) return 'banner-conflict'
  if (props.pendingCount > 0) return 'banner-pending'
  return 'banner-ok'
})
</script>

<style scoped>
.offline-banner {
  padding: 8px 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.3s;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.banner-icon {
  flex-shrink: 0;
  font-size: 16px;
}

.banner-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.banner-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sync-btn {
  flex-shrink: 0;
  font-size: 12px;
  padding: 0 8px;
  height: 24px;
}

/* 状态颜色 */
.banner-offline {
  background: #fef3c7;
  color: #92400e;
}

.banner-syncing {
  background: #dbeafe;
  color: #1e40af;
}

.banner-conflict {
  background: #fef3c7;
  color: #92400e;
}

.banner-pending {
  background: #fef3c7;
  color: #92400e;
}

.banner-ok {
  background: #d1fae5;
  color: #065f46;
}
</style>
