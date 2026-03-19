<template>
  <div class="dialog-backdrop" @click.self="$emit('close')">
    <section class="dialog-panel">
      <header class="dialog-header">
        <div>
          <p class="dialog-kicker">Delete Label</p>
          <h3>{{ label.name }}</h3>
        </div>
        <button class="ghost-button" @click="$emit('close')">Close</button>
      </header>

      <div class="dialog-form">
        <p class="welcome-copy">
          Delete the strange label bound to key {{ shortcutLabel(label.shortcutKey) }}.
        </p>
        <p class="dialog-help">
          Only labels with 0 traces can be deleted. This label currently has {{ label.count }} labeled
          {{ label.count === 1 ? "trace" : "traces" }}.
        </p>
        <p
          v-if="resultMessage"
          :class="['dialog-result', resultTone === 'success' ? 'dialog-result--success' : 'dialog-result--error']"
        >
          {{ resultMessage }}
        </p>
        <div class="dialog-actions">
          <button class="ghost-button" type="button" @click="$emit('close')">
            {{ resultMessage ? "Done" : "Cancel" }}
          </button>
          <button
            v-if="resultTone !== 'success'"
            class="danger-button"
            type="button"
            :disabled="submitting"
            @click="confirmDelete"
          >
            {{ submitting ? "Deleting…" : "Confirm delete" }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
  label: { type: Object, required: true },
  deleteLabel: { type: Function, required: true },
});

defineEmits(["close"]);

const submitting = ref(false);
const resultMessage = ref("");
const resultTone = ref("");

async function confirmDelete() {
  resultMessage.value = "";
  resultTone.value = "";
  submitting.value = true;
  try {
    await props.deleteLabel(props.label.name);
    resultTone.value = "success";
    resultMessage.value = `Deleted label "${props.label.name}".`;
  } catch (error) {
    resultTone.value = "error";
    resultMessage.value = error.message;
  } finally {
    submitting.value = false;
  }
}

function shortcutLabel(value) {
  return value === " " ? "space" : value;
}
</script>
