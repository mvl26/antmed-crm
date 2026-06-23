<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-lot-trace-title">
    <!-- Header + breadcrumb: Trang chủ › Tồn kho › Truy vết lot -->
    <header
      class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4"
    >
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-6">{{ __('Tồn kho') }}</span>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{
          __('Truy vết lot')
        }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-lot-trace-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          {{ __('Truy vết lot') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Tra cứu một lô vật tư: số lượng nhập/xuất/còn, chứng từ CO/CQ và trạng thái thu hồi.',
            )
          }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5">
      <div class="mx-auto flex max-w-5xl flex-col gap-4">
        <!-- Card tìm kiếm: input Mã Lot + nút Truy vết -->
        <form
          class="flex flex-col gap-3 rounded-lg border border-outline-gray-modals bg-surface-white p-4 sm:flex-row sm:items-end"
          @submit.prevent="submitTrace"
        >
          <div class="flex flex-1 flex-col gap-1">
            <label
              for="lot-trace-input"
              class="text-p-xs font-medium text-ink-gray-6"
            >
              {{ __('Mã Lot') }}
            </label>
            <FormControl
              id="lot-trace-input"
              v-model="lotInput"
              type="text"
              :placeholder="__('Nhập số lô cần tra cứu')"
              :aria-label="__('Mã Lot cần truy vết')"
            />
          </div>
          <Button
            variant="solid"
            type="submit"
            :label="__('Truy vết')"
            :loading="lot.loading"
            :disabled="!lotInput.trim()"
            :aria-label="__('Truy vết lô')"
          />
        </form>

        <!-- Tri-branch: empty (chưa truy vết) / loading / error / not-found / data -->

        <!-- Empty: chưa truy vết lần nào -->
        <div
          v-if="!hasSubmitted"
          class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-outline-gray-2 py-16 text-center text-ink-gray-6"
        >
          <p class="text-p-base">{{ __('Chưa truy vết lô nào') }}</p>
          <p class="text-p-sm">
            {{ __('Nhập mã lô rồi bấm "Truy vết" để xem thông tin lô.') }}
          </p>
        </div>

        <!-- Loading -->
        <div
          v-else-if="lot.loading"
          class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
          aria-live="polite"
        >
          <LoadingIndicator class="h-4 w-4" />
          <span class="text-p-base">{{ __('Đang truy vết lô…') }}</span>
        </div>

        <!-- Not-found: lô không tồn tại (BE raise DoesNotExistError) -->
        <div
          v-else-if="isNotFound"
          class="flex flex-col items-center gap-3 py-16 text-center"
          role="alert"
        >
          <Badge
            variant="subtle"
            theme="gray"
            size="lg"
            :label="__('Không tìm thấy')"
          />
          <p class="max-w-md text-p-sm text-ink-gray-6">
            {{ __('Không tìm thấy lot') }}
            <span class="font-medium text-ink-gray-8">{{ lastTraced }}</span
            >.
          </p>
        </div>

        <!-- Error khác: banner + nút Thử lại -->
        <div
          v-else-if="lot.error"
          class="flex flex-col items-center gap-3 py-16 text-center"
          role="alert"
        >
          <Badge
            variant="subtle"
            theme="red"
            size="lg"
            :label="__('Không truy vết được')"
          />
          <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
          <Button
            variant="outline"
            :label="__('Thử lại')"
            @click="lot.reload()"
          />
        </div>

        <!-- Data: cardrow cols-2 (mockup D3): trái 'Thông tin lot' + phải 'Cây truy vết' -->
        <div
          v-else-if="data"
          class="grid grid-cols-1 items-start gap-4 lg:grid-cols-2"
        >
          <!-- Card TRÁI: "Thông tin lot" (đã có M03-2) -->
          <div
            class="rounded-lg border border-outline-gray-modals bg-surface-white p-4"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <h2 class="text-base font-semibold text-ink-gray-9">
                {{ __('Thông tin lot') }}
              </h2>
              <!-- Chip trạng thái thu hồi: KÈM CHỮ (không chỉ màu — WCAG AA) -->
              <span
                :class="[
                  'inline-flex items-center rounded-full px-2.5 py-0.5 text-p-xs font-medium',
                  recallChipClass(data.recall_status),
                ]"
                :aria-label="
                  __('Trạng thái thu hồi') + ': ' + (data.recall_status || '—')
                "
              >
                {{ data.recall_status || '—' }}
              </span>
            </div>

            <table class="w-full border-separate border-spacing-0 text-left">
              <caption class="sr-only">
                {{
                  __('Bảng thông tin lô')
                }}
              </caption>
              <thead>
                <tr class="text-p-xs text-ink-gray-5">
                  <th
                    class="w-32 border-b border-outline-gray-modals py-2 pr-4 font-medium"
                  >
                    {{ __('Trường') }}
                  </th>
                  <th
                    class="border-b border-outline-gray-modals py-2 font-medium"
                  >
                    {{ __('Giá trị') }}
                  </th>
                </tr>
              </thead>
              <tbody class="text-p-base">
                <!-- SKU: item_code · item_name (KHÔNG lộ mã thô đứng riêng) -->
                <tr>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-6"
                  >
                    {{ __('SKU') }}
                  </td>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 text-ink-gray-8"
                  >
                    <span class="font-medium text-ink-gray-9">{{
                      data.item_name || '—'
                    }}</span>
                    <span v-if="data.item" class="text-ink-gray-5">
                      · {{ data.item }}</span
                    >
                  </td>
                </tr>
                <!-- NCC: supplier_name (tên), KHÔNG mã -->
                <tr>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-6"
                  >
                    {{ __('NCC') }}
                  </td>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 text-ink-gray-8"
                  >
                    {{ data.supplier_name || data.supplier || '—' }}
                  </td>
                </tr>
                <!-- NSX (mfg_date dd/MM/yyyy) -->
                <tr>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-6"
                  >
                    {{ __('NSX') }}
                  </td>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 tabular-nums text-ink-gray-8"
                  >
                    {{ fmtDate(data.mfg_date) }}
                  </td>
                </tr>
                <!-- HSD (expiry_date dd/MM/yyyy) -->
                <tr>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-6"
                  >
                    {{ __('HSD') }}
                  </td>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 tabular-nums text-ink-gray-8"
                  >
                    {{ fmtDate(data.expiry_date) }}
                  </td>
                </tr>
                <!-- SL nhập / SL đã xuất / SL còn (khớp sổ tồn) -->
                <tr>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-6"
                  >
                    {{ __('SL nhập') }}
                  </td>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 tabular-nums text-ink-gray-8"
                  >
                    {{ fmtQty(data.qty_in) }}
                  </td>
                </tr>
                <tr>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-6"
                  >
                    {{ __('SL đã xuất') }}
                  </td>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 tabular-nums text-ink-gray-8"
                  >
                    {{ fmtQty(data.qty_out) }}
                  </td>
                </tr>
                <tr>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-6"
                  >
                    {{ __('SL còn') }}
                  </td>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 tabular-nums font-medium text-ink-gray-9"
                  >
                    {{ fmtQty(data.qty_remaining) }}
                    <!-- Tách theo loại kho (mockup D3 "153 = Tổng 80 · Ký gửi BV 73") -->
                    <span
                      v-if="balanceBreakdown"
                      class="ml-1 text-p-xs font-normal text-ink-gray-5"
                    >
                      ({{ balanceBreakdown }})
                    </span>
                  </td>
                </tr>
                <!-- CO / CQ: link tải PDF nếu có file_url; fallback mã chứng từ; '—' nếu trống -->
                <tr>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-6"
                  >
                    {{ __('CO') }}
                  </td>
                  <td
                    class="border-b border-outline-gray-1 py-2.5 text-ink-gray-8"
                  >
                    <a
                      v-if="data.co_file_url"
                      :href="data.co_file_url"
                      target="_blank"
                      rel="noopener"
                      class="rounded text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                    >
                      {{ __('Tải CO')
                      }}<span v-if="data.co_cert" class="text-ink-gray-5">
                        · {{ data.co_cert }}</span
                      >
                    </a>
                    <span v-else>{{ data.co_cert || '—' }}</span>
                  </td>
                </tr>
                <tr>
                  <td class="py-2.5 pr-4 text-ink-gray-6">{{ __('CQ') }}</td>
                  <td class="py-2.5 text-ink-gray-8">
                    <a
                      v-if="data.cq_file_url"
                      :href="data.cq_file_url"
                      target="_blank"
                      rel="noopener"
                      class="rounded text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                    >
                      {{ __('Tải CQ')
                      }}<span v-if="data.cq_cert" class="text-ink-gray-5">
                        · {{ data.cq_cert }}</span
                      >
                    </a>
                    <span v-else>{{ data.cq_cert || '—' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Card PHẢI: "Cây truy vết" (MỚI M03-6) — dòng thời gian di chuyển của lô -->
          <div
            class="rounded-lg border border-outline-gray-modals bg-surface-white p-4"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <h2 class="text-base font-semibold text-ink-gray-9">
                {{ __('Cây truy vết') }}
              </h2>
              <span class="text-p-xs text-ink-gray-5">
                {{ __('Nhập NCC → Xuất NV → Chuyển kho / Ký gửi BV') }}
              </span>
            </div>

            <!-- Tri-branch RIÊNG cho trace: loading / error / empty / data -->

            <!-- Loading -->
            <div
              v-if="trace.loading"
              class="flex items-center justify-center gap-2 py-12 text-ink-gray-6"
              aria-live="polite"
            >
              <LoadingIndicator class="h-4 w-4" />
              <span class="text-p-sm">{{ __('Đang tải lịch sử…') }}</span>
            </div>

            <!-- Error -->
            <div
              v-else-if="trace.error"
              class="flex flex-col items-center gap-3 py-12 text-center"
              role="alert"
            >
              <Badge
                variant="subtle"
                theme="red"
                size="lg"
                :label="__('Không tải được lịch sử')"
              />
              <p class="max-w-md text-p-sm text-ink-gray-6">
                {{ traceErrorMessage }}
              </p>
              <Button
                variant="outline"
                :label="__('Thử lại')"
                @click="trace.reload()"
              />
            </div>

            <!-- Empty: lô tồn tại nhưng chưa có ledger -->
            <div
              v-else-if="!events.length"
              class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-outline-gray-2 py-12 text-center text-ink-gray-6"
            >
              <p class="text-p-sm">{{ __('Chưa có lịch sử di chuyển') }}</p>
            </div>

            <!-- Data: timeline các event (BE đã sort posting_datetime ASC) -->
            <ol
              v-else
              class="flex flex-col gap-0"
              aria-label="Dòng thời gian di chuyển lô"
            >
              <li
                v-for="(ev, idx) in events"
                :key="idx"
                class="relative flex gap-3 pb-4 pl-1 last:pb-0"
              >
                <!-- Trục dọc + chấm mốc -->
                <div class="flex flex-col items-center">
                  <span
                    :class="[
                      'mt-1 h-2.5 w-2.5 shrink-0 rounded-full',
                      ev.direction === 'in' ? 'bg-green-600' : 'bg-amber-500',
                    ]"
                    aria-hidden="true"
                  />
                  <span
                    v-if="idx < events.length - 1"
                    class="mt-1 w-px flex-1 bg-outline-gray-2"
                    aria-hidden="true"
                  />
                </div>

                <!-- Nội dung 1 event -->
                <div class="flex flex-1 flex-col gap-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="text-p-xs tabular-nums text-ink-gray-5">{{
                      fmtDate(ev.posting_datetime)
                    }}</span>
                    <!-- Chip chiều: KÈM CHỮ (Nhập/Xuất) — không chỉ màu (WCAG AA) -->
                    <span
                      :class="[
                        'inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium',
                        traceDirectionChipClass(ev.direction),
                      ]"
                      :aria-label="
                        __('Chiều') + ': ' + traceDirectionLabel(ev.direction)
                      "
                    >
                      {{ traceDirectionLabel(ev.direction) }}
                    </span>
                    <span class="text-p-sm font-medium text-ink-gray-9">{{
                      entryDirectionLabel(ev.entry_type)
                    }}</span>
                  </div>
                  <div
                    class="flex flex-wrap items-center gap-2 text-p-sm text-ink-gray-7"
                  >
                    <span>{{ ev.warehouse_name || ev.warehouse || '—' }}</span>
                    <!-- Chip loại kho -->
                    <span
                      v-if="ev.warehouse_type"
                      class="inline-flex items-center rounded-full bg-ink-gray-2 px-2 py-0.5 text-p-xs text-ink-gray-7"
                    >
                      {{ ev.warehouse_type }}
                    </span>
                    <span class="tabular-nums text-ink-gray-8"
                      >{{ __('SL') }}: {{ fmtQty(ev.qty) }}</span
                    >
                  </div>
                  <div
                    class="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-p-xs text-ink-gray-5"
                  >
                    <span v-if="ev.voucher_no"
                      >{{ __('Phiếu') }}: {{ ev.voucher_no }}</span
                    >
                    <span v-if="ev.hospital"
                      >{{ __('BV') }}: {{ ev.hospital }}</span
                    >
                    <span v-if="ev.nv_employee"
                      >{{ __('NV') }}: {{ ev.nv_employee }}</span
                    >
                  </div>
                </div>
              </li>
            </ol>

            <!-- CHÂN card "Cây truy vết" (mockup D3): action Khởi tạo Recall theo lô (Thủ kho) -->
            <div
              class="mt-4 flex flex-col gap-2 border-t border-outline-gray-modals pt-4"
            >
              <Button
                variant="solid"
                theme="red"
                :label="__('⚠ Khởi tạo Recall theo lot này')"
                :disabled="!data || data.recall_status === 'Đã thu hồi'"
                :loading="initiateRecall.loading"
                :aria-label="
                  __('Khởi tạo recall theo lô') + ' ' + (data?.lot_no || '')
                "
                @click="openRecallModal"
              />
              <!-- Lô đã thu hồi: hint vì sao nút disabled (UX — không để user kẹt im lặng) -->
              <p
                v-if="data && data.recall_status === 'Đã thu hồi'"
                class="text-p-xs text-ink-gray-5"
              >
                {{
                  __('Lô này đã được thu hồi — không thể khởi tạo recall lại.')
                }}
              </p>
            </div>
          </div>

          <!-- Card "Sử dụng tại ca mổ" (phả hệ lô → giao phòng mổ → hóa đơn) — col-span 2 -->
          <div
            class="rounded-lg border border-outline-gray-modals bg-surface-white p-4 lg:col-span-2"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <h2 class="text-base font-semibold text-ink-gray-9">
                {{ __('Sử dụng tại ca mổ') }}
              </h2>
              <div class="flex items-center gap-2">
                <Button
                  variant="subtle"
                  :label="__('Lưu vết')"
                  :loading="saveTrace.loading"
                  :aria-label="__('Lưu bản truy vết lô này')"
                  @click="doSaveTrace"
                />
                <Button
                  v-if="savedTraceName"
                  variant="outline"
                  :label="__('Tải PDF')"
                  :loading="exportPdf.loading"
                  :aria-label="__('Xuất PDF bản truy vết')"
                  @click="doExportPdf"
                />
              </div>
            </div>

            <!-- loading / error / empty / data -->
            <div
              v-if="genealogy.loading"
              class="flex items-center justify-center gap-2 py-10 text-ink-gray-6"
              aria-live="polite"
            >
              <LoadingIndicator class="h-4 w-4" />
              <span class="text-p-sm">{{ __('Đang tải phả hệ…') }}</span>
            </div>
            <div
              v-else-if="genealogy.error"
              class="flex flex-col items-center gap-2 py-10 text-center"
              role="alert"
            >
              <Badge
                variant="subtle"
                theme="red"
                size="lg"
                :label="__('Không tải được phả hệ')"
              />
              <Button
                variant="outline"
                :label="__('Thử lại')"
                @click="genealogy.reload()"
              />
            </div>
            <div
              v-else-if="!deliveries.length"
              class="rounded-lg border border-dashed border-outline-gray-2 py-10 text-center text-p-sm text-ink-gray-6"
            >
              {{ __('Chưa có ca mổ nào dùng lô này') }}
            </div>
            <ul v-else class="flex flex-col gap-3">
              <li
                v-for="d in deliveries"
                :key="d.delivery"
                class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 p-3"
              >
                <div
                  class="flex flex-wrap items-center gap-x-4 gap-y-1 text-p-sm"
                >
                  <span class="font-medium text-ink-gray-9">{{
                    d.hospital_name || d.hospital || '—'
                  }}</span>
                  <span class="text-ink-gray-7"
                    >{{ __('Bác sỹ') }}:
                    {{ d.doctor_name || d.doctor || '—' }}</span
                  >
                  <span class="text-ink-gray-7"
                    >{{ __('Ca mổ') }}: {{ formatStockTime(d.surgery_datetime)
                    }}<span v-if="d.surgery_room">
                      · {{ d.surgery_room }}</span
                    ></span
                  >
                  <span class="tabular-nums text-ink-gray-8"
                    >{{ __('SL dùng') }}: {{ fmtQty(d.used_qty) }}</span
                  >
                </div>
                <div
                  class="mt-1.5 flex flex-wrap items-center gap-2 text-p-xs text-ink-gray-5"
                >
                  <span>{{ __('Phiếu giao') }}: {{ d.delivery }}</span>
                  <template v-if="d.einvoice">
                    <span class="text-ink-gray-4" aria-hidden="true">·</span>
                    <span>{{ __('Hóa đơn') }}: {{ d.einvoice }}</span>
                    <span
                      v-if="d.einvoice_status"
                      class="inline-flex items-center rounded-full bg-ink-gray-2 px-2 py-0.5 text-ink-gray-7"
                    >
                      {{ d.einvoice_status }}
                    </span>
                    <a
                      v-if="d.einvoice_pdf"
                      :href="d.einvoice_pdf"
                      target="_blank"
                      rel="noopener"
                      class="rounded text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                    >
                      {{ __('Tải HĐ') }}
                    </a>
                  </template>
                  <span v-else>{{ __('Chưa xuất hóa đơn') }}</span>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Confirm-modal Khởi tạo Recall (mockup D3): mã lô + SKU + lý do (bắt buộc) + mức recall -->
    <Dialog
      v-model="showRecallModal"
      :options="{ title: __('Khởi tạo Recall theo lô') }"
    >
      <template #body-content>
        <div class="flex flex-col gap-4">
          <!-- Mã lô + SKU (KHÔNG lộ mã thô đứng riêng — item_name là chính) -->
          <div class="rounded-md bg-surface-gray-1 px-3 py-2.5 text-p-sm">
            <div class="flex items-center justify-between gap-2">
              <span class="text-ink-gray-6">{{ __('Mã lô') }}</span>
              <span class="font-medium text-ink-gray-9">{{
                data?.lot_no || '—'
              }}</span>
            </div>
            <div class="mt-1 flex items-center justify-between gap-2">
              <span class="text-ink-gray-6">{{ __('SKU') }}</span>
              <span class="text-right font-medium text-ink-gray-9">
                {{ data?.item_name || '—' }}
                <span v-if="data?.item" class="font-normal text-ink-gray-5">
                  · {{ data.item }}</span
                >
              </span>
            </div>
          </div>

          <!-- Lý do recall (bắt buộc, Long Text) -->
          <FormControl
            v-model="recallReason"
            type="textarea"
            :rows="3"
            :label="__('Lý do recall')"
            :required="true"
            :placeholder="__('Nhập lý do khởi tạo recall (bắt buộc)')"
            :aria-label="__('Lý do recall')"
            aria-describedby="recall-reason-hint"
          />
          <p
            v-if="recallSubmitted && !recallReason.trim()"
            id="recall-reason-hint"
            class="-mt-2 text-p-xs text-red-600"
            role="alert"
          >
            {{ __('Vui lòng nhập lý do recall.') }}
          </p>

          <!-- Mức recall (Theo dõi / Đã thu hồi) — default 'Đã thu hồi' -->
          <FormControl
            v-model="recallStatus"
            type="select"
            :label="__('Mức recall')"
            :options="recallStatusOptions"
            :aria-label="__('Mức recall')"
          />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button
            variant="subtle"
            :label="__('Hủy')"
            :disabled="initiateRecall.loading"
            @click="closeRecallModal"
          />
          <Button
            variant="solid"
            theme="red"
            :label="__('Xác nhận khởi tạo')"
            :loading="initiateRecall.loading"
            :disabled="!recallReason.trim() || initiateRecall.loading"
            @click="submitRecall"
          />
        </div>
      </template>
    </Dialog>
  </main>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Badge, Button, Dialog, FormControl, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  getLot,
  getLotTrace,
  getLotGenealogy,
  saveLotTrace as createSaveLotTrace,
  exportLotTracePdf as createExportLotTracePdf,
  initiateRecall as createInitiateRecall,
} from '@/data/antmed'
import {
  fmtDate,
  fmtQty,
  formatStockTime,
  recallChipClass,
  entryDirectionLabel,
  traceDirectionChipClass,
  traceDirectionLabel,
  RECALL_INITIATE_STATUSES,
  RECALL_INITIATE_DEFAULT,
} from '@/utils/antmedUi'

// Ô nhập mã lô + lô vừa truy vết (hiển thị ở nhánh not-found).
const lotInput = ref('')
const lastTraced = ref('')
const hasSubmitted = ref(false)

// auto:false — chỉ fetch khi bấm 'Truy vết'. Endpoint trả dict THƯỜNG → đọc r.data TRỰC TIẾP.
const lot = getLot({ auto: false })
// Cây truy vết (mockup D3 right-card): fetch CÙNG LÚC với getLot (cùng mã lô). Dict THƯỜNG →
// đọc r.data.events TRỰC TIẾP (KHÔNG .data.data — cùng idiom getLot).
const trace = getLotTrace({ auto: false })

const data = computed(() => lot.data || null)
// events đã sort posting_datetime ASC ở BE → FE KHÔNG sort lại. r.data.events (dict THƯỜNG).
const events = computed(() => trace.data?.events || [])

// ── M03 D3: phả hệ ca mổ (lô → Delivery → hóa đơn) + lưu vết + route query ──
const route = useRoute()
const genealogy = getLotGenealogy({ auto: false })
const deliveries = computed(() => genealogy.data?.deliveries || [])
const saveTrace = createSaveLotTrace({ auto: false })
const exportPdf = createExportLotTracePdf({ auto: false })
// Tên bản truy vết vừa lưu → mở nút "Tải PDF".
const savedTraceName = ref('')

// SL còn tách theo loại kho (mockup D3 "153 = Tổng 80 · Ký gửi BV 73"). BE đã GROUP BY → FE chỉ nối.
const balanceByType = computed(
  () => data.value?.balance_by_warehouse_type || [],
)
const balanceBreakdown = computed(() =>
  balanceByType.value
    .map((b) => `${b.warehouse_type} ${fmtQty(b.qty)}`)
    .join(' · '),
)

function doSaveTrace() {
  if (!data.value) return
  saveTrace.submit(
    { lot: data.value.name },
    {
      onSuccess(res) {
        savedTraceName.value = res?.name || ''
        toast.success(__('Đã lưu bản truy vết {0}', [savedTraceName.value]))
      },
      onError(err) {
        toast.error(err?.messages?.[0] || __('Không lưu được bản truy vết'))
      },
    },
  )
}

// Xuất PDF bản vừa lưu → mở file để tải.
function doExportPdf() {
  if (!savedTraceName.value) return
  exportPdf.submit(
    { name: savedTraceName.value },
    {
      onSuccess(res) {
        if (res?.exported_pdf) window.open(res.exported_pdf, '_blank')
        toast.success(__('Đã xuất PDF truy vết'))
      },
      onError(err) {
        toast.error(err?.messages?.[0] || __('Không xuất được PDF'))
      },
    },
  )
}

// fmtQty (SL VI có phân tách, maxFractionDigits 2) gom về canon @/utils/antmedUi (identical).

// Phân biệt not-found (BE raise DoesNotExistError → exc_type/HTTP 404) với lỗi khác.
const isNotFound = computed(() => {
  const err = lot.error
  if (!err) return false
  const exc = err.exc_type || err.exception || ''
  const msg = err.messages?.[0] || err.message || ''
  return (
    /DoesNotExist/i.test(exc) ||
    /not found|does not exist|không tìm thấy/i.test(msg)
  )
})

const errorMessage = computed(
  () =>
    lot.error?.messages?.[0] ||
    lot.error?.message ||
    __('Không truy vết được lô'),
)

// Lỗi nhánh "Cây truy vết" (tách khỏi lỗi getLot — widget lỗi KHÔNG vỡ card thông tin lô).
const traceErrorMessage = computed(
  () =>
    trace.error?.messages?.[0] ||
    trace.error?.message ||
    __('Không tải được lịch sử di chuyển'),
)

// Submit truy vết: param phát đi == ô nhập (chống dead-control). name = mã lô (== lot_no).
// Gọi CÙNG LÚC getLot + getLotTrace (cùng mã lô) → render đồng thời 2 card mockup D3.
function submitTrace() {
  const name = lotInput.value.trim()
  if (!name) return
  lastTraced.value = name
  hasSubmitted.value = true
  lot.submit({ name })
  trace.submit({ name })
  genealogy.submit({ name })
}

// Drill-down từ màn "Quản lý lot": ?lot=<lot_no> → auto điền + truy vết ngay.
onMounted(() => {
  const q = (route.query.lot || '').toString().trim()
  if (q) {
    lotInput.value = q
    submitTrace()
  }
})

// Lỗi quyền (PermissionError) hoặc lỗi khác → toast (ngoài banner tri-branch). Not-found
// đã có nhánh riêng nên KHÔNG toast (tránh nhiễu cho trường hợp gõ sai mã).
lot.onError = (err) => {
  const exc = err?.exc_type || err?.exception || ''
  if (/DoesNotExist/i.test(exc)) return
  toast.error(err?.messages?.[0] || __('Không truy vết được lô'))
}

// Lỗi nhánh trace có banner riêng (card phải) → KHÔNG toast (tránh nhiễu; lỗi lô không tồn tại
// đã hiện ở card trái). Để rỗng giữ lỗi trong trace.error cho tri-branch render.
trace.onError = () => {}

// ── M03-7: Khởi tạo Recall theo lô (mockup D3 chân card "Cây truy vết", Thủ kho) ──
// MUTATION resource (POST). Đọc r.data.recall_status TRỰC TIẾP (dict THƯỜNG, KHÔNG .data.data).
const initiateRecall = createInitiateRecall({ auto: false })

// State confirm-modal: hiện/ẩn, lý do (bắt buộc), mức recall (default 'Đã thu hồi').
const showRecallModal = ref(false)
const recallReason = ref('')
const recallStatus = ref(RECALL_INITIATE_DEFAULT)
const recallSubmitted = ref(false)

// Options dropdown 'Mức recall' — KEY khớp EXACT BE (RECALL_INITIATE_STATUSES = options DocType).
// value = key kỹ thuật gửi đi == lựa chọn UI (chống dead-control); label = nhãn VI (chính key VI).
const recallStatusOptions = RECALL_INITIATE_STATUSES.map((s) => ({
  label: s,
  value: s,
}))

function openRecallModal() {
  if (!data.value || data.value.recall_status === 'Đã thu hồi') return
  recallReason.value = ''
  recallStatus.value = RECALL_INITIATE_DEFAULT
  recallSubmitted.value = false
  showRecallModal.value = true
}

function closeRecallModal() {
  showRecallModal.value = false
}

// Xác nhận khởi tạo recall: param phát đi == lựa chọn UI (lot/reason/status — chống dead-control).
// reason rỗng bị chặn FE (song song BE). Success → toast + đóng modal + reload getLot (chip đổi màu).
function submitRecall() {
  recallSubmitted.value = true
  const reason = recallReason.value.trim()
  if (!reason || !data.value) return
  initiateRecall.submit(
    { lot: data.value.name, reason, status: recallStatus.value },
    {
      onSuccess(res) {
        // BE 'Đã thu hồi' tự sinh Recall Notification + đếm BV ảnh hưởng (res.affected_hospitals).
        if (res?.recall_notification) {
          toast.success(
            __('Đã thu hồi lô {0} — {1} BV ảnh hưởng đã được thông báo', [
              data.value?.lot_no || '',
              res?.affected_hospitals ?? 0,
            ]),
          )
        } else {
          toast.success(
            __('Đã khởi tạo recall cho lô {0}', [data.value?.lot_no || '']),
          )
        }
        showRecallModal.value = false
        recallReason.value = ''
        recallSubmitted.value = false
        // reload getLot → chip recall_status trên card 'Thông tin lot' đổi sang giá trị mới.
        lot.reload()
      },
      onError(err) {
        // BE frappe.throw (PermissionError/ValidationError) → message VI ở err.messages[0]. KHÔNG đổi chip.
        toast.error(err?.messages?.[0] || __('Không khởi tạo được recall'))
      },
    },
  )
}
</script>
