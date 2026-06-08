<template>
  <div class="app-container">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="navbar-left">
        <div class="navbar-title">开源水质与地理信息系统</div>
        <div class="navbar-nav">
          <router-link to="/place-management" class="nav-item" active-class="active">地名信息管理</router-link>
          <router-link to="/existing-placenames" class="nav-item" active-class="active">存量地名处理</router-link>
          <router-link to="/place-stats" class="nav-item" active-class="active">地名信息统计</router-link>
        </div>
      </div>
      <div class="navbar-right">
        <div class="admin-info">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span>admin</span>
        </div>
      </div>
    </nav>

    <!-- 页面内容 -->
    <div class="page-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
</script>

<style>
/* --- 全局基础样式 --- */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #0b1a2f;
  color: #e0e6ed;
  min-height: 100vh;
}

.app-container {
  min-height: 100vh;
}

/* --- 导航栏 --- */
.navbar {
  background: linear-gradient(90deg, #0a3d62, #1e3799);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 30px;
}

.navbar-title {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
}

.navbar-nav {
  display: flex;
  gap: 4px;
}

.nav-item {
  padding: 8px 20px;
  color: #cbd5e0;
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.3s;
  font-size: 14px;
}

.nav-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.nav-item.active {
  background-color: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e0e6ed;
  font-size: 14px;
}

/* --- 页面内容区 --- */
.page-content {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
