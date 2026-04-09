<template>
  <aside
    class="summary-panel"
    :class="[
      `summary-panel--${side}`,
      { 'summary-panel--active': active },
    ]"
  >
    <div class="summary-panel-header">
      <div>
        <p class="page-kicker">{{ kicker }}</p>
        <h2>{{ title }}</h2>
      </div>

      <div class="summary-panel-actions">
        <v-btn
          v-if="showReviewAll"
          color="primary"
          size="small"
          variant="tonal"
          @click="$emit('review-all')"
        >
          Review all
        </v-btn>
        <v-btn
          v-if="allowAdd"
          color="secondary"
          icon="mdi-plus"
          size="small"
          variant="tonal"
          @click="$emit('add')"
        />
      </div>
    </div>

    <div class="summary-panel-list">
      <v-card
        v-for="item in items"
        :key="item.key"
        class="summary-panel-card"
        rounded="xl"
        variant="tonal"
      >
        <button
          type="button"
          class="summary-panel-card-button"
          :disabled="disableEmptyReview && Number(item.count || 0) === 0"
          @click="$emit('review-item', item.reviewValue ?? item.value)"
        >
          <div class="summary-panel-card-copy">
            <strong>{{ item.title }}</strong>
            <span>{{ Number(item.count || 0) }} labeled</span>
          </div>
          <v-icon icon="mdi-chevron-right" size="18" />
        </button>

        <v-btn
          v-if="allowDelete"
          class="summary-panel-delete"
          color="error"
          icon="mdi-delete-outline"
          size="x-small"
          variant="text"
          @click="$emit('delete-item', item.deleteValue ?? item.value)"
        />
      </v-card>

      <v-alert
        v-if="!items.length"
        border="start"
        color="surface-variant"
        icon="mdi-information-outline"
        rounded="xl"
        variant="tonal"
      >
        No items to show yet.
      </v-alert>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  kicker: { type: String, required: true },
  items: { type: Array, required: true },
  side: { type: String, required: true },
  showReviewAll: { type: Boolean, default: false },
  allowAdd: { type: Boolean, default: false },
  allowDelete: { type: Boolean, default: false },
  disableEmptyReview: { type: Boolean, default: true },
  active: { type: Boolean, default: false },
});

defineEmits(["review-all", "review-item", "add", "delete-item"]);
</script>
