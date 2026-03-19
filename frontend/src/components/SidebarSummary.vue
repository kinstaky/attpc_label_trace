<template>
  <aside :class="['sidebar', side, { active }]">
    <header class="sidebar-header">
      <span class="sidebar-kicker">{{ kicker }}</span>
      <h2>{{ title }}</h2>
    </header>
    <div class="sidebar-list">
      <article
        v-for="item in visibleItems"
        :key="itemKey(item)"
        :class="['summary-card', { 'summary-card--deletable': canDelete }]"
      >
        <div class="summary-title" v-if="type === 'normal'">
          <span class="summary-number">{{ normalNumber(item.title) }}</span>
          <span class="summary-text">{{ normalText(item.title) }}</span>
        </div>
        <div class="summary-title summary-title--plain" v-else>
          {{ item.name }}
        </div>
        <div class="summary-subtitle">
          {{ item.count }} labeled
        </div>
        <div class="summary-shortcut" v-if="type === 'strange'">
          key {{ shortcutLabel(item.shortcutKey) }}
        </div>
        <button
          v-if="canDelete"
          type="button"
          class="summary-delete"
          @click="$emit('request-delete', item)"
        >
          Delete
        </button>
      </article>

      <button
        v-if="showAddCard"
        type="button"
        class="summary-card summary-card--add"
        @click="$emit('add')"
      >
        <span class="summary-add-mark">+</span>
        <strong class="summary-add-text">{{ addLabel }}</strong>
        <span class="summary-add-subtitle">{{ addDescription }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  title: { type: String, required: true },
  kicker: { type: String, required: true },
  type: { type: String, required: true },
  side: { type: String, required: true },
  active: { type: Boolean, default: false },
  items: { type: Array, default: () => [] },
  showAddCard: { type: Boolean, default: false },
  addLabel: { type: String, default: "Add label" },
  addDescription: { type: String, default: "Create a new shortcut" },
  allowDelete: { type: Boolean, default: false },
});

defineEmits(["add", "request-delete"]);

const visibleItems = computed(() =>
  props.type === "normal" ? props.items.filter((item) => !item.hidden) : props.items,
);

const canDelete = computed(() => props.allowDelete && props.type === "strange");

function itemKey(item) {
  return props.type === "normal" ? item.bucket : item.id;
}

function normalNumber(title) {
  return title.split(" ")[0];
}

function normalText(title) {
  return title.split(" ").slice(1).join(" ");
}

function shortcutLabel(value) {
  return value === " " ? "space" : value;
}
</script>
