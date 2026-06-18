<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-admin-title">
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink to="/antmed" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Trang chủ') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ __('Quản trị · User & Role') }}</span>
      </nav>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h1 id="antmed-admin-title" class="text-xl font-semibold text-ink-gray-9">⚙ {{ __('User & Role — phân quyền') }}</h1>
        <!-- 2FA toàn hệ thống (Frappe không hỗ trợ 2FA từng-user) -->
        <button
          type="button"
          class="flex items-center gap-2 rounded-full border px-3 py-1.5 text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
          :class="global2fa ? 'border-green-300 bg-green-50 text-green-700' : 'border-outline-gray-2 text-ink-gray-6'"
          :aria-pressed="global2fa"
          :disabled="set2fa.loading"
          @click="toggle2fa"
        >
          🔐 {{ __('2FA hệ thống') }}: <strong>{{ global2fa ? __('Bật') : __('Tắt') }}</strong>
        </button>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 pb-8 pt-4">
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-[1.5fr_1fr]">
        <!-- ── Trái: danh sách user ──────────────────────────────────────── -->
        <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
          <div class="mb-3 flex gap-2">
            <input
              v-model="searchText"
              class="flex-1 rounded-md border border-outline-gray-2 px-3 py-1.5 text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
              :placeholder="__('🔍 Tìm theo tên / email')"
              :aria-label="__('Tìm user')"
            />
            <Button variant="solid" theme="teal" :label="__('+ Thêm user')" @click="openCreate" />
          </div>

          <div v-if="users.loading" class="flex items-center justify-center gap-2 py-12 text-ink-gray-6">
            <LoadingIndicator class="h-4 w-4" /><span>{{ __('Đang tải…') }}</span>
          </div>
          <div v-else-if="users.error" class="flex flex-col items-center gap-3 py-12 text-center" role="alert">
            <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
            <p class="text-p-sm text-ink-gray-6">{{ usersError }}</p>
            <Button variant="outline" :label="__('Thử lại')" @click="users.reload()" />
          </div>
          <div v-else-if="!filteredUsers.length" class="py-12 text-center text-p-sm text-ink-gray-6">
            {{ __('Không có user khớp.') }}
          </div>

          <table v-else class="w-full border-separate border-spacing-0 text-left">
            <thead>
              <tr class="text-p-xs uppercase text-ink-gray-5">
                <th class="border-b border-outline-gray-modals py-2 pr-3 font-medium">{{ __('User') }}</th>
                <th class="border-b border-outline-gray-modals py-2 pr-3 font-medium">{{ __('Vai trò') }}</th>
                <th class="border-b border-outline-gray-modals py-2 pr-3 font-medium">{{ __('Phạm vi DL') }}</th>
                <th class="border-b border-outline-gray-modals py-2 pr-3 font-medium">{{ __('2FA') }}</th>
                <th class="border-b border-outline-gray-modals py-2 pr-3 font-medium">{{ __('Trạng thái') }}</th>
                <th class="border-b border-outline-gray-modals py-2 font-medium text-right">{{ __('Thao tác') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="u in filteredUsers"
                :key="u.name"
                class="align-top text-p-sm text-ink-gray-8 transition-colors hover:bg-surface-gray-1"
              >
                <td class="border-b border-outline-gray-1 py-2.5 pr-3">
                  <div class="font-medium text-ink-gray-9">{{ u.full_name }}</div>
                  <div class="text-p-xs text-ink-gray-5">{{ u.email }}</div>
                </td>
                <td class="border-b border-outline-gray-1 py-2.5 pr-3">
                  <div class="flex flex-wrap gap-1">
                    <Badge v-for="r in u.roles" :key="r" variant="subtle" :theme="roleTheme(r)" size="sm" :label="r" />
                    <Badge v-if="u.is_admin" variant="subtle" theme="red" size="sm" :label="__('System Manager')" />
                    <span v-if="!u.roles.length && !u.is_admin" class="text-p-xs text-ink-gray-4">—</span>
                  </div>
                </td>
                <td class="border-b border-outline-gray-1 py-2.5 pr-3 text-ink-gray-7">{{ u.data_scope }}</td>
                <td class="border-b border-outline-gray-1 py-2.5 pr-3">
                  <Badge variant="subtle" :theme="u.two_factor ? 'green' : 'gray'" size="sm" :label="u.two_factor ? __('Bật') : __('Tắt')" />
                </td>
                <td class="border-b border-outline-gray-1 py-2.5 pr-3">
                  <Badge variant="subtle" :theme="u.enabled ? 'green' : 'red'" size="sm" :label="u.enabled ? __('Active') : __('Khoá')" />
                </td>
                <td class="border-b border-outline-gray-1 py-2.5 text-right">
                  <div class="flex justify-end gap-1">
                    <Button variant="ghost" size="sm" :label="__('Vai trò')" :aria-label="__('Sửa vai trò {0}', [u.full_name])" @click="openRoles(u)" />
                    <Button
                      variant="ghost"
                      size="sm"
                      :theme="u.enabled ? 'red' : 'green'"
                      :label="u.enabled ? __('Khoá') : __('Mở')"
                      :aria-label="(u.enabled ? __('Khoá') : __('Mở khoá')) + ' ' + u.full_name"
                      @click="toggleEnabled(u)"
                    />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ── Phải: ma trận quyền ───────────────────────────────────────── -->
        <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
          <div class="mb-3 flex items-center gap-2">
            <label class="text-p-sm font-semibold text-ink-gray-8" for="role-pick">{{ __('Ma trận quyền — vai trò') }}</label>
            <select
              id="role-pick"
              v-model="selectedRole"
              class="rounded-md border border-outline-gray-2 px-2 py-1 text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
            >
              <option v-for="r in roleOptions" :key="r.name" :value="r.name">{{ r.name }}</option>
            </select>
          </div>

          <div v-if="matrix.loading" class="py-8 text-center text-p-sm text-ink-gray-6">{{ __('Đang tải…') }}</div>
          <table v-else class="w-full border-separate border-spacing-0 text-left">
            <thead>
              <tr class="text-p-xs uppercase text-ink-gray-5">
                <th class="border-b border-outline-gray-modals py-2 pr-2 font-medium">{{ __('Module') }}</th>
                <th class="border-b border-outline-gray-modals py-2 px-1 text-center font-medium">{{ __('Đọc') }}</th>
                <th class="border-b border-outline-gray-modals py-2 px-1 text-center font-medium">{{ __('Tạo') }}</th>
                <th class="border-b border-outline-gray-modals py-2 px-1 text-center font-medium">{{ __('Sửa') }}</th>
                <th class="border-b border-outline-gray-modals py-2 px-1 text-center font-medium">{{ __('Xóa') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in matrixRows" :key="row.doctype" class="text-p-sm text-ink-gray-8">
                <td class="border-b border-outline-gray-1 py-2 pr-2">{{ row.module }}</td>
                <td class="border-b border-outline-gray-1 py-2 px-1 text-center" :class="cellClass(row.read)">{{ mark(row.read) }}</td>
                <td class="border-b border-outline-gray-1 py-2 px-1 text-center" :class="cellClass(row.create)">{{ mark(row.create) }}</td>
                <td class="border-b border-outline-gray-1 py-2 px-1 text-center" :class="cellClass(row.write)">{{ mark(row.write) }}</td>
                <td class="border-b border-outline-gray-1 py-2 px-1 text-center" :class="cellClass(row.delete)">{{ mark(row.delete) }}</td>
              </tr>
            </tbody>
          </table>

          <div class="mt-3 rounded-md border-l-2 border-blue-400 bg-blue-50 px-3 py-2 text-p-xs text-blue-800">
            🛈 {{ __('Phạm vi DL: NV chỉ thấy bệnh viện thuộc tuyến phụ trách (cấu hình qua User Permission). Mọi thao tác đều ghi audit log.') }}
          </div>
        </div>
      </div>
    </section>

    <!-- Dialog: thêm user -->
    <Dialog v-model="createDlg" :options="{ title: __('Thêm user mới') }">
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <p class="mb-5 text-p-sm text-ink-gray-6">
            {{ __('Tạo tài khoản hệ thống, gán vai trò và đặt mật khẩu đăng nhập ban đầu để gửi cho người dùng.') }}
          </p>
          <div class="flex flex-col gap-4">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormControl
                type="email"
                :label="__('Email') + ' *'"
                v-model="createForm.email"
                placeholder="ten@antmed.vn"
                required
              />
              <FormControl
                type="text"
                :label="__('Họ và tên')"
                v-model="createForm.full_name"
                :placeholder="__('Nguyễn Văn A')"
              />
            </div>
            <FormControl
              type="select"
              :label="__('Vai trò ban đầu')"
              v-model="createForm.role"
              :options="roleOptions.map((r) => ({ label: r.name, value: r.name }))"
            />
            <div>
              <label class="mb-1.5 block text-p-sm font-medium text-ink-gray-7">
                {{ __('Mật khẩu đăng nhập') }}
              </label>
              <div class="flex items-end gap-2">
                <FormControl
                  class="flex-1"
                  type="text"
                  v-model="createForm.password"
                  :placeholder="__('Tối thiểu 8 ký tự')"
                />
                <Button
                  variant="subtle"
                  :label="__('Tạo ngẫu nhiên')"
                  @click="genPassword"
                />
              </div>
              <p class="mt-1.5 flex items-center gap-1 text-p-xs text-ink-gray-5">
                🔑 {{ __('Admin đặt & gửi mật khẩu này cho người dùng; họ nên đổi sau khi đăng nhập.') }}
              </p>
            </div>
          </div>
          <div class="mt-6 flex justify-end gap-2 border-t border-outline-gray-1 pt-4">
            <Button :label="__('Huỷ')" @click="createDlg = false" />
            <Button
              variant="solid"
              theme="teal"
              :loading="createRes.loading"
              :label="__('Tạo user')"
              @click="onCreate"
            />
          </div>
        </div>
      </template>
    </Dialog>

    <!-- Dialog: sửa vai trò -->
    <Dialog v-model="roleDlg" :options="{ title: __('Vai trò của {0}', [roleForm.full_name]) }">
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <p class="mb-3 text-p-sm text-ink-gray-6">
            {{ __('Chọn các vai trò cho user. Chỉ quản vai trò AntMed/Sales — System Manager không đổi tại đây.') }}
          </p>
          <div class="flex flex-col gap-1.5">
            <label
              v-for="r in roleOptions"
              :key="r.name"
              class="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 hover:bg-surface-gray-2"
            >
              <input type="checkbox" :value="r.name" v-model="roleForm.selected" class="h-4 w-4 rounded" />
              <Badge variant="subtle" :theme="roleTheme(r.name)" size="sm" :label="r.name" />
            </label>
          </div>
          <div class="mt-6 flex justify-end gap-2">
            <Button :label="__('Huỷ')" @click="roleDlg = false" />
            <Button
              variant="solid"
              theme="teal"
              :loading="rolesRes.loading"
              :label="__('Lưu vai trò')"
              @click="onSaveRoles"
            />
          </div>
        </div>
      </template>
    </Dialog>
  </main>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, Dialog, FormControl, createResource, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { getAdminUsers, getAdminRoles, ROLE_PILL_THEME } from '@/data/antmed'

const ADMIN = 'antmed_crm.api.antmed.admin'

const users = getAdminUsers({ auto: true, onError: (err) => toast.error(err?.messages?.[0] || __('Không tải được danh sách user')) })
const rolesRsc = getAdminRoles({ auto: true })

const searchText = ref('')
const filteredUsers = computed(() => {
  const q = searchText.value.trim().toLowerCase()
  const list = users.data?.data || []
  if (!q) return list
  return list.filter((u) => (u.full_name || '').toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q))
})
const global2fa = computed(() => !!users.data?.global_2fa)
const roleOptions = computed(() => rolesRsc.data?.roles || [])

function roleTheme(r) {
  return ROLE_PILL_THEME[r] || 'gray'
}
const usersError = computed(() => users.error?.messages?.[0] || users.error?.message || __('Không tải được danh sách user'))

// ── Ma trận quyền (đổi role → reload) ────────────────────────────────────────
const selectedRole = ref('NV kinh doanh')
const matrix = createResource({
  url: `${ADMIN}.role_permissions`,
  method: 'GET',
  makeParams: () => ({ role: selectedRole.value }),
})
const matrixRows = computed(() => matrix.data?.rows || [])
onMounted(() => matrix.reload())
watch(selectedRole, () => matrix.reload())

function mark(v) {
  return v ? '✓' : '—'
}
function cellClass(v) {
  return v ? 'font-semibold text-green-600' : 'text-ink-gray-4'
}

// ── Actions (POST, admin-gated BE) ───────────────────────────────────────────
const set2fa = createResource({
  url: `${ADMIN}.set_global_2fa`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã cập nhật 2FA hệ thống'))
    users.reload()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không cập nhật được 2FA')),
})
function toggle2fa() {
  set2fa.submit({ enabled: global2fa.value ? 0 : 1 })
}

const setEnabled = createResource({
  url: `${ADMIN}.set_user_enabled`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã cập nhật trạng thái tài khoản'))
    users.reload()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Thao tác thất bại')),
})
function toggleEnabled(u) {
  setEnabled.submit({ user: u.name, enabled: u.enabled ? 0 : 1 })
}

// Thêm user
const createDlg = ref(false)
const createForm = ref({ email: '', full_name: '', role: 'NV kinh doanh', password: '' })
const createRes = createResource({
  url: `${ADMIN}.create_user`,
  method: 'POST',
  onSuccess() {
    // Echo lại email + mật khẩu để admin copy gửi cho người dùng (dialog sắp đóng).
    toast.success(
      __('Đã tạo {0} · mật khẩu: {1}', [createForm.value.email, createForm.value.password]),
      { duration: 12000 },
    )
    createDlg.value = false
    users.reload()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không tạo được user')),
})
function openCreate() {
  createForm.value = {
    email: '',
    full_name: '',
    role: roleOptions.value[0]?.name || 'NV kinh doanh',
    password: '',
  }
  createDlg.value = true
}
// Sinh mật khẩu mạnh (đủ HOA/thường/số/ký tự) bằng crypto — admin thấy & copy được.
function genPassword() {
  const U = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
  const L = 'abcdefghijkmnpqrstuvwxyz'
  const D = '23456789'
  const S = '!@#$%&*'
  const pick = (s, n) =>
    Array.from(crypto.getRandomValues(new Uint32Array(n)))
      .map((x) => s[x % s.length])
      .join('')
  createForm.value.password = pick(U, 2) + pick(L, 5) + pick(D, 3) + pick(S, 2)
}
function onCreate() {
  const f = createForm.value
  if (!f.email || !f.full_name) {
    toast.error(__('Nhập email và họ tên'))
    return
  }
  if ((f.password || '').length < 8) {
    toast.error(__('Mật khẩu tối thiểu 8 ký tự'))
    return
  }
  createRes.submit({ ...f })
}

// Sửa vai trò
const roleDlg = ref(false)
const roleForm = ref({ name: '', full_name: '', selected: [] })
const rolesRes = createResource({
  url: `${ADMIN}.set_user_roles`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã cập nhật vai trò'))
    roleDlg.value = false
    users.reload()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không cập nhật được vai trò')),
})
function openRoles(u) {
  roleForm.value = { name: u.name, full_name: u.full_name, selected: [...u.roles] }
  roleDlg.value = true
}
function onSaveRoles() {
  rolesRes.submit({ user: roleForm.value.name, roles_json: JSON.stringify(roleForm.value.selected) })
}
</script>
