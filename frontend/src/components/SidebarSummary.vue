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
        class="summary-card"
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
      </article>
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
});

const visibleItems = computed(() =>
  props.type === "normal" ? props.items.filter((item) => !item.hidden) : props.items,
);

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
