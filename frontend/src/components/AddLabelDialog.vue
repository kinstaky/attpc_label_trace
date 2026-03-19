<template>
  <div class="dialog-backdrop" @click.self="$emit('close')">
    <section class="dialog-panel">
      <header class="dialog-header">
        <div>
          <p class="dialog-kicker">Strange Label</p>
          <h3>Create strange label</h3>
        </div>
        <button class="ghost-button" @click="$emit('close')">Close</button>
      </header>
      <form class="dialog-form" @submit.prevent="submit">
        <label>
          <span>Name</span>
          <input v-model.trim="name" type="text" maxlength="48" autofocus />
        </label>
        <label>
          <span>Shortcut key</span>
          <input v-model.trim="shortcutKey" type="text" maxlength="12" />
        </label>
        <p class="dialog-help">
          Reserved: arrows, h/j/k/l, q, esc, space, 0-9
        </p>
        <p class="dialog-error" v-if="localError">{{ localError }}</p>
        <div class="dialog-actions">
          <button class="ghost-button" type="button" @click="$emit('close')">Cancel</button>
          <button class="primary-button" type="submit" :disabled="submitting">Save</button>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
  saveLabel: { type: Function, required: true },
});

defineEmits(["close"]);

const name = ref("");
const shortcutKey = ref("");
const localError = ref("");
const submitting = ref(false);

async function submit() {
  localError.value = "";
  if (!name.value) {
    localError.value = "Name is required.";
    return;
  }
  if (!shortcutKey.value) {
    localError.value = "Shortcut key is required.";
    return;
  }
  submitting.value = true;
  try {
    await props.saveLabel({ name: name.value, shortcutKey: shortcutKey.value });
    name.value = "";
    shortcutKey.value = "";
  } catch (error) {
    localError.value = error.message;
  } finally {
    submitting.value = false;
  }
}
</script>
