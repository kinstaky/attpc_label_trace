<template>
  <v-dialog :model-value="modelValue" max-width="440" @update:model-value="$emit('update:modelValue', $event)">
    <v-card rounded="xl">
      <v-card-title class="dialog-title">Create Strange Label</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="name"
          label="Label name"
          variant="outlined"
        />
        <v-text-field
          v-model="shortcutKey"
          hint="Single key used in label mode"
          label="Shortcut key"
          persistent-hint
          variant="outlined"
        />
        <v-alert
          v-if="error"
          class="mt-4"
          color="error"
          icon="mdi-alert-circle-outline"
          variant="tonal"
        >
          {{ error }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Cancel</v-btn>
        <v-btn color="primary" :loading="saving" @click="submit">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  saveLabel: { type: Function, required: true },
});

const emit = defineEmits(["update:modelValue"]);

const name = ref("");
const shortcutKey = ref("");
const error = ref("");
const saving = ref(false);

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      name.value = "";
      shortcutKey.value = "";
      error.value = "";
      saving.value = false;
    }
  },
);

function close() {
  emit("update:modelValue", false);
}

async function submit() {
  saving.value = true;
  error.value = "";
  try {
    await props.saveLabel({
      name: name.value,
      shortcutKey: shortcutKey.value,
    });
    close();
  } catch (caughtError) {
    error.value = caughtError.message;
  } finally {
    saving.value = false;
  }
}
</script>
