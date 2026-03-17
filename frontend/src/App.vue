<template>
  <div class="app-shell" @keydown.stop>
    <SidebarSummary
      title="Normal"
      kicker="Peak count"
      type="normal"
      side="left"
      :active="state.activeSidebar === 'left'"
      :items="state.bootstrap?.normalSummary || []"
    />

    <main class="main-panel">
      <section class="status-strip">
        <span v-if="state.loading">Loading…</span>
        <span class="status-error" v-else-if="state.error">{{ state.error }}</span>
        <span v-else-if="state.statusMessage">{{ state.statusMessage }}</span>
        <span v-else>&nbsp;</span>
      </section>

      <WelcomeView
        v-if="state.bootstrap && state.page === 'welcome'"
        :bootstrap="state.bootstrap"
        @start="startLabeling"
        @open-dialog="openDialog"
      />

      <LabelView
        v-else-if="state.currentTrace && state.page === 'label'"
        :trace="state.currentTrace"
        :mode="state.mode"
        :current-label-text="currentLabelText()"
      />

      <section v-else class="welcome-panel">
        <p class="eyebrow">Trace Manual</p>
        <h1>Loading app state…</h1>
      </section>
    </main>

    <SidebarSummary
      title="Strange"
      kicker="Special cases"
      type="strange"
      side="right"
      :active="state.activeSidebar === 'right'"
      :items="state.bootstrap?.strangeSummary || []"
    />

    <AddLabelDialog
      v-if="state.dialogOpen"
      :save-label="onSaveLabel"
      @close="closeDialog"
    />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from "vue";
import AddLabelDialog from "./components/AddLabelDialog.vue";
import SidebarSummary from "./components/SidebarSummary.vue";
import LabelView from "./views/LabelView.vue";
import WelcomeView from "./views/WelcomeView.vue";
import { useAppStore } from "./stores/app";

const {
  state,
  init,
  startLabeling,
  openDialog,
  closeDialog,
  addStrangeLabel,
  handleKeydown,
  currentLabelText,
} = useAppStore();

async function onSaveLabel(payload) {
  await addStrangeLabel(payload.name, payload.shortcutKey);
}

onMounted(async () => {
  await init();
  window.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>
