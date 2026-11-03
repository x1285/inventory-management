<template>
  <div class="app-shell" :class="{ 'drawer-open': drawerOpen, 'sidebar-collapsed': collapsed }">
    <!-- Sidebar: full or icon rail above 700px, off-canvas drawer at 700px and below -->
    <aside class="sidebar" id="app-sidebar" aria-label="Main navigation">
      <div class="sidebar-brand">
        <div class="sidebar-brand-text">
          <h1>{{ t('nav.companyName') }}</h1>
          <span class="sidebar-subtitle">{{ t('nav.subtitle') }}</span>
        </div>
        <!-- Collapse toggle: hidden on phones, where the drawer is always expanded -->
        <button
          class="sidebar-toggle"
          type="button"
          aria-controls="app-sidebar"
          :aria-expanded="!collapsed"
          :aria-label="collapseLabel"
          :title="collapseLabel"
          @click="toggleCollapsed"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
        </button>
      </div>

      <nav class="sidebar-nav" aria-label="Pages">
        <!-- title and aria-label keep the label discoverable when the rail hides the text -->
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :title="item.label"
          :aria-label="item.label"
          :aria-current="$route.path === item.to ? 'page' : undefined"
          @click="drawerOpen = false"
        >
          <!-- v-html is safe here: icon strings are static literals in this file -->
          <svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true" v-html="item.icon"></svg>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </aside>

    <div class="sidebar-backdrop" @click="drawerOpen = false"></div>

    <!-- Content column -->
    <div class="content-column">
      <header class="content-header">
        <button
          class="menu-toggle"
          type="button"
          aria-controls="app-sidebar"
          :aria-expanded="drawerOpen"
          aria-label="Open navigation"
          @click="drawerOpen = true"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
        <FilterBar />
      </header>

      <main class="content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    // Mobile drawer state. Only has a visual effect at 700px and below.
    const drawerOpen = ref(false)

    // Collapsed (icon rail) state for the sidebar above 700px.
    // Breakpoint default when the user has no saved choice: rail up to 1200px, full sidebar
    // above. Phones (700px and below) ignore this and always show the expanded drawer.
    const COLLAPSE_KEY = 'sidebar-collapsed'
    const defaultCollapsed = () => {
      try {
        return window.matchMedia('(max-width: 1200px)').matches
      } catch (e) {
        return false
      }
    }
    // localStorage can throw (private windows, blocked storage), so reads and writes are
    // wrapped. A missing or unreadable value falls back to the breakpoint default.
    const readCollapsed = () => {
      try {
        const saved = localStorage.getItem(COLLAPSE_KEY)
        if (saved === '1') return true
        if (saved === '0') return false
      } catch (e) {
        // fall through to the breakpoint default
      }
      return defaultCollapsed()
    }
    const collapsed = ref(readCollapsed())
    const collapseLabel = computed(() => (collapsed.value ? 'Expand sidebar' : 'Collapse sidebar'))
    // Only an explicit user toggle is persisted, so the responsive default is not frozen in.
    const toggleCollapsed = () => {
      collapsed.value = !collapsed.value
      try {
        localStorage.setItem(COLLAPSE_KEY, collapsed.value ? '1' : '0')
      } catch (e) {
        // ignore: the state still works for this session
      }
    }

    // Nav kept in one place so routes and labels are not duplicated.
    // Icons are plain 24x24 stroke paths (no icon library).
    const navItems = [
      { to: '/', label: t('nav.overview'), icon: '<path d="M3 12l9-9 9 9M5 10v10h14V10" />' },
      { to: '/inventory', label: t('nav.inventory'), icon: '<path d="M3 7l9-4 9 4v10l-9 4-9-4z" />' },
      { to: '/orders', label: t('nav.orders'), icon: '<path d="M6 3h12v18H6zM9 8h6M9 12h6M9 16h4" />' },
      { to: '/spending', label: t('nav.finance'), icon: '<path d="M12 2v20M17 6H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />' },
      { to: '/demand', label: t('nav.demandForecast'), icon: '<path d="M3 17l6-6 4 4 8-8" />' },
      { to: '/reports', label: t('nav.reports'), icon: '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2" />' }
    ]

    // Escape closes the drawer. The listener is removed on unmount so it does not leak.
    const onKeydown = (e) => { if (e.key === 'Escape') drawerOpen.value = false }
    onMounted(() => document.addEventListener('keydown', onKeydown))
    onUnmounted(() => document.removeEventListener('keydown', onKeydown))

    // Focus moves into the drawer on open and returns to the toggle on close.
    // Without this, keyboard users are left behind on the page content.
    watch(drawerOpen, async (open) => {
      await nextTick()
      if (open) {
        document.querySelector('#app-sidebar .nav-item')?.focus()
      } else {
        document.querySelector('.menu-toggle')?.focus()
      }
    })

    return {
      t,
      drawerOpen,
      collapsed,
      collapseLabel,
      toggleCollapsed,
      navItems,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/*
 * Design tokens. Single source for color, spacing, radius, shadow, and type.
 * Spacing uses a 4px base grid so every gap is a multiple of 4.
 * Change values here, not in individual components.
 * Light theme only: the dark-mode token blocks from the spec are intentionally left out.
 */
:root {
  /* Surfaces */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-surface-muted: #f8fafc;
  --color-sidebar: #0f172a;
  --color-sidebar-text: #cbd5e1;
  --color-sidebar-hover: #1e293b;

  /* Text */
  --color-text: #1e293b;
  --color-text-strong: #0f172a;
  --color-text-muted: #64748b;
  --color-text-subtle: #475569;

  /* Borders */
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;
  --color-divider: #f1f5f9;

  /* Accent (interactive) */
  --color-accent: #2563eb;
  --color-accent-soft: #eff6ff;
  --color-accent-text: #1d4ed8;

  /* Status */
  --color-success: #059669;
  --color-success-soft: #d1fae5;
  --color-success-text: #065f46;
  --color-warning: #ea580c;
  --color-warning-soft: #fed7aa;
  --color-warning-text: #92400e;
  --color-danger: #dc2626;
  --color-danger-soft: #fecaca;
  --color-danger-text: #991b1b;
  --color-danger-bg: #fef2f2;
  --color-info-soft: #dbeafe;
  --color-info-text: #1e40af;
  --color-stable-soft: #e0e7ff;
  --color-stable-text: #3730a3;

  /* Spacing (4px grid) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;

  /* Layout */
  --sidebar-width: 248px;
  --sidebar-rail-width: 72px;
  --content-max-width: 1600px;
  --gutter: var(--space-8);
  --gutter-mobile: var(--space-6);

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 10px;

  /* Elevation */
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.06);

  /* Type scale */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 0.938rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.5rem;
  --font-size-2xl: 1.875rem;
  --font-size-3xl: 2.25rem;

  /* Motion */
  --transition-fast: 0.15s ease;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ---------- App shell ---------- */
.app-shell {
  /* The grid column reads this variable so the content column stays aligned
     with the sidebar in both the full and the rail state. */
  --sidebar-current: var(--sidebar-width);
  display: grid;
  grid-template-columns: var(--sidebar-current) minmax(0, 1fr);
  min-height: 100vh;
  background: var(--color-bg);
  transition: grid-template-columns 0.2s ease;
}

/* Sidebar: sticky with height 100vh so it stays pinned while only the content column
   scrolls. Overflow stays visible so the footer dropdowns can open past its edge; the nav
   list scrolls on its own if the viewport is short. z-index keeps dropdowns above the
   sticky content header. */
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 60;
  display: flex;
  flex-direction: column;
  background: var(--color-sidebar);
  color: var(--color-sidebar-text);
  padding: var(--space-6) var(--space-4);
}

.sidebar-brand {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 0 var(--space-3) var(--space-6);
}
.sidebar-brand-text { min-width: 0; }
.sidebar-brand h1 {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: -0.025em;
}
.sidebar-subtitle { font-size: var(--font-size-xs); color: var(--color-text-muted); }

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-sidebar-text);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.sidebar-toggle:hover { background: var(--color-sidebar-hover); }
.sidebar-toggle:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.sidebar-toggle svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.2s ease;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
  min-height: 0;
  /* Small padding so focus outlines are not clipped by the scroll container */
  padding: 2px;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Nav item: 40px touch target, icon + label */
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 40px;
  flex-shrink: 0;
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--color-sidebar-text);
  text-decoration: none;
  font-size: var(--font-size-base);
  font-weight: 500;
  white-space: nowrap;
  position: relative;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.nav-item:hover { background: var(--color-sidebar-hover); color: #f8fafc; }
.nav-item:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }

/* Active state: tinted background plus a left accent bar */
.nav-item[aria-current="page"] {
  background: var(--color-sidebar-hover);
  color: #f8fafc;
}
.nav-item[aria-current="page"]::before {
  content: '';
  position: absolute;
  left: 0;
  top: var(--space-2);
  bottom: var(--space-2);
  width: 3px;
  border-radius: 2px;
  background: var(--color-accent);
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.sidebar-footer {
  border-top: 1px solid rgba(148, 163, 184, 0.15);
  padding-top: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
/* Footer buttons fill the sidebar width */
.sidebar-footer .language-button,
.sidebar-footer .profile-button {
  width: 100%;
}

/* ---------- Content column ---------- */
.content-column { min-width: 0; display: flex; flex-direction: column; }

/* The content header is the sticky element (it holds the global filter bar) */
.content-header {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--gutter);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.content {
  flex: 1;
  width: 100%;
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--space-6) var(--gutter);
}

/* Hamburger is hidden above the phone breakpoint */
.menu-toggle {
  display: none;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  align-items: center;
  justify-content: center;
}
.menu-toggle:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.menu-toggle svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; }

.sidebar-backdrop { display: none; }

/* ---------- Icon rail (701px and up) ----------
   Scoped to a min-width query so phones never see the rail: at 700px and below the
   sidebar is always the full drawer. Labels are hidden visually, but each nav link keeps
   a title (tooltip) and aria-label so it is still announced and discoverable. */
@media (min-width: 701px) {
  .app-shell.sidebar-collapsed { --sidebar-current: var(--sidebar-rail-width); }

  .sidebar-collapsed .sidebar { padding-left: var(--space-3); padding-right: var(--space-3); }
  .sidebar-collapsed .sidebar-brand { flex-direction: column; align-items: center; padding: 0 0 var(--space-6); }
  .sidebar-collapsed .sidebar-brand-text { display: none; }
  .sidebar-collapsed .sidebar-toggle svg { transform: rotate(180deg); }

  .sidebar-collapsed .nav-item { justify-content: center; padding: 0; }
  .sidebar-collapsed .nav-item > span { display: none; }

  /* Footer widgets show only their avatar / globe icon. Selectors are specific enough
     to win over the children's scoped styles regardless of CSS order. */
  .app-shell.sidebar-collapsed .sidebar-footer .language-label,
  .app-shell.sidebar-collapsed .sidebar-footer .profile-name,
  .app-shell.sidebar-collapsed .sidebar-footer .chevron { display: none; }
  .app-shell.sidebar-collapsed .sidebar-footer .language-button,
  .app-shell.sidebar-collapsed .sidebar-footer .profile-button {
    justify-content: center;
    padding: var(--space-2) 0;
  }
}

/* ---------- Phone drawer (700px and below) ---------- */
@media (max-width: 700px) {
  .app-shell { grid-template-columns: minmax(0, 1fr); }

  /* Sidebar slides in from the left, out of the flow */
  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    width: var(--sidebar-width);
    max-width: 85vw;
    z-index: 200;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }
  .drawer-open .sidebar { transform: translateX(0); }
  .sidebar-toggle { display: none; }

  /* Backdrop dims the page while the drawer is open. Click closes it. */
  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    z-index: 150;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
  }
  .drawer-open .sidebar-backdrop { opacity: 1; pointer-events: auto; }

  .menu-toggle { display: inline-flex; }
  .content { padding: var(--space-4) var(--gutter-mobile); }
  .content-header { padding: var(--space-3) var(--gutter-mobile); }
}

/* Respect users who ask for reduced motion */
@media (prefers-reduced-motion: reduce) {
  .app-shell,
  .sidebar,
  .sidebar-backdrop,
  .sidebar-toggle svg { transition: none; }
}

/* ---------- Shared classes ---------- */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-strong);
  margin-bottom: var(--space-1);
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.stat-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-text-strong);
  letter-spacing: -0.025em;
}

/* Stat values keep semantic colors */
.stat-card.warning .stat-value { color: var(--color-warning); }
.stat-card.success .stat-value { color: var(--color-success); }
.stat-card.danger .stat-value { color: var(--color-danger); }
.stat-card.info .stat-value { color: var(--color-accent); }

.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-5);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text-strong);
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-surface-muted);
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

th {
  text-align: left;
  padding: var(--space-2) var(--space-3);
  font-weight: 600;
  color: var(--color-text-subtle);
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: var(--space-2) var(--space-3);
  border-top: 1px solid var(--color-divider);
  color: var(--color-text-subtle);
  font-size: var(--font-size-sm);
}

tbody tr {
  transition: background-color var(--transition-fast);
}

tbody tr:hover {
  background: var(--color-surface-muted);
}

.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success,
.badge.increasing {
  background: var(--color-success-soft);
  color: var(--color-success-text);
}

.badge.warning,
.badge.medium {
  background: var(--color-warning-soft);
  color: var(--color-warning-text);
}

.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
}

.badge.info,
.badge.low {
  background: var(--color-info-soft);
  color: var(--color-info-text);
}

.badge.stable {
  background: var(--color-stable-soft);
  color: var(--color-stable-text);
}

.loading {
  text-align: center;
  padding: var(--space-12);
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
}

.error {
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-soft);
  color: var(--color-danger-text);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
  font-size: var(--font-size-base);
}
</style>
