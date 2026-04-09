<template>
  <v-dialog :model-value="modelValue" max-width="420" @update:model-value="$emit('update:modelValue', $event)">
    <v-card rounded="xl">
      <v-card-title class="dialog-title">Delete Strange Label</v-card-title>
      <v-card-text>
        <p class="dialog-copy">
          Delete <strong>{{ label?.name }}</strong>?
        </p>
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
        <v-btn variant="text" @click="$emit('update:modelValue', false)">Cancel</v-btn>
        <v-btn color="error" :loading="deleting" @click="submit">Delete</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  label: { type: Object, default: null },
  deleteLabel: { type: Function, required: true },
});

const emit = defineEmits(["update:modelValue"]);

const error = ref("");
const deleting = ref(false);

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      error.value = "";
      deleting.value = false;
    }
  },
);

async function submit() {
  if (!props.label?.name) {
    return;
  }
  deleting.value = true;
  error.value = "";
  try {
    await props.deleteLabel(props.label.name);
    emit("update:modelValue", false);
  } catch (caughtError) {
    error.value = caughtError.message;
  } finally {
    deleting.value = false;
  }
}
</script>
