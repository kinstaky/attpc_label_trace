<template>
  <div class="mapping-canvas-shell">
    <div class="mapping-canvas-status">
      <p class="page-kicker">Selection</p>
      <strong v-if="selectedPad">
        Cobo {{ selectedPad.cobo }} · Asad {{ selectedPad.asad }} · Aget {{ selectedPad.aget }} · Ch {{ selectedPad.channel }} · Pad {{ selectedPad.pad }}
      </strong>
      <span v-else>No pad selected.</span>
    </div>

    <div ref="root" class="mapping-canvas-root"></div>

    <div class="mapping-canvas-footer">
      <p>
        x: {{ mouseX.toFixed(2) }} mm, y: {{ mouseY.toFixed(2) }} mm
      </p>
      <span>Drag to pan. Scroll to zoom. Click a pad to inspect it.</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Application, Container, Graphics, Point } from "pixi.js";

import type { MappingPad, MappingRenderRule, MappingViewMode } from "../types";

const props = defineProps<{
  pads: MappingPad[];
  rules: MappingRenderRule[];
  view: MappingViewMode;
}>();

interface PadGraphicEntry {
  index: number;
  data: MappingPad;
  graphic: Graphics;
  hovered: boolean;
}

const DEFAULT_COLOR = 0xc0c0c0;
const SELECTED_COLOR = 0x111111;
const FLOAT_SCALE = 1.3;
const HALF_EDGE = 4.5;
const HEIGHT = HALF_EDGE * (3 ** 0.5);
const HALF_HEIGHT = HEIGHT * 0.5;
const INIT_X_SCALE = 1.3;
const INIT_Y_SCALE = -1.3;

const root = ref<HTMLDivElement | null>(null);
const mouseX = ref(0);
const mouseY = ref(0);
const selectedIndex = ref<number | null>(null);

const selectedPad = computed<MappingPad | null>(() => {
  if (selectedIndex.value === null) {
    return null;
  }
  return props.pads[selectedIndex.value] ?? null;
});

let app: Application | null = null;
let container: Container | null = null;
let entries: PadGraphicEntry[] = [];
let zoomScale = 1;
let dragging = false;
let dragged = false;
let lastPointerWasPad = false;
let dragStart = { x: 0, y: 0 };
let containerStart = { x: 0, y: 0 };

let onMouseDown: ((event: MouseEvent) => void) | null = null;
let onMouseMove: ((event: MouseEvent) => void) | null = null;
let onMouseUp: (() => void) | null = null;
let onMouseLeave: (() => void) | null = null;
let onWheel: ((event: WheelEvent) => void) | null = null;

function matchesRule(pad: MappingPad, rule: MappingRenderRule): boolean {
  return (
    (rule.cobo === "*" || Number(rule.cobo) === pad.cobo) &&
    (rule.asad === "*" || Number(rule.asad) === pad.asad) &&
    (rule.aget === "*" || Number(rule.aget) === pad.aget) &&
    (rule.channel === "*" || Number(rule.channel) === pad.channel)
  );
}

function resolveFillColor(pad: MappingPad): number {
  for (const rule of props.rules) {
    if (matchesRule(pad, rule)) {
      const normalized = rule.color.startsWith("#") ? rule.color.slice(1) : rule.color;
      const parsed = Number.parseInt(normalized, 16);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }
  }
  return DEFAULT_COLOR;
}

function padPoints(direction: number): number[] {
  return direction === 1
    ? [-HEIGHT / 3, -HALF_EDGE, -HEIGHT / 3, HALF_EDGE, (HEIGHT * 2) / 3, 0]
    : [HEIGHT / 3, -HALF_EDGE, HEIGHT / 3, HALF_EDGE, (-HEIGHT * 2) / 3, 0];
}

function resetGraphic(entry: PadGraphicEntry): void {
  const isSelected = selectedIndex.value === entry.index;
  const scaleMultiplier = isSelected || entry.hovered ? FLOAT_SCALE : 1;
  const fillColor = isSelected ? SELECTED_COLOR : resolveFillColor(entry.data);
  entry.graphic.clear();
  entry.graphic.poly(padPoints(entry.data.direction));
  entry.graphic.fill(fillColor);
  entry.graphic.position.set(entry.data.cx, entry.data.cy);
  entry.graphic.scale.set(entry.data.scale * scaleMultiplier);
  if (isSelected && container) {
    container.setChildIndex(entry.graphic, container.children.length - 1);
  }
}

function rebuildPads(): void {
  if (!container) {
    return;
  }
  const sceneContainer = container;
  const children = sceneContainer.removeChildren();
  for (const child of children) {
    child.destroy();
  }
  entries = [];
  selectedIndex.value = null;
  props.pads.forEach((pad, index) => {
    const graphic = new Graphics();
    const entry: PadGraphicEntry = { index, data: pad, graphic, hovered: false };
    graphic.eventMode = "static";
    graphic.cursor = "pointer";
    graphic.on("pointerover", () => {
      entry.hovered = true;
      resetGraphic(entry);
    });
    graphic.on("pointerout", () => {
      entry.hovered = false;
      resetGraphic(entry);
    });
    graphic.on("pointertap", () => {
      if (dragged) {
        return;
      }
      lastPointerWasPad = true;
      selectedIndex.value = index;
      redrawAll();
    });
    entries.push(entry);
    resetGraphic(entry);
    sceneContainer.addChild(graphic);
  });
}

function redrawAll(): void {
  for (const entry of entries) {
    resetGraphic(entry);
  }
}

function currentRevertX(): number {
  return props.view === "Upstream" ? -1 : 1;
}

function updateContainerScale(): void {
  if (!container) {
    return;
  }
  container.scale.x = INIT_X_SCALE * zoomScale * currentRevertX();
  container.scale.y = INIT_Y_SCALE * zoomScale;
}

function eventClipPosition(event: MouseEvent | WheelEvent): { x: number; y: number } {
  const canvas = app?.canvas;
  if (!canvas || !app) {
    return { x: 0, y: 0 };
  }
  const rect = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left) * (app.renderer.width / rect.width),
    y: (event.clientY - rect.top) * (app.renderer.height / rect.height),
  };
}

async function mountPixi(): Promise<void> {
  if (!root.value || app) {
    return;
  }
  app = new Application();
  await app.init({
    background: "#fffdf8",
    resizeTo: root.value,
    antialias: true,
  });
  root.value.appendChild(app.canvas);

  container = new Container();
  app.stage.addChild(container);
  container.position.set(app.screen.width / 2, app.screen.height / 2);
  updateContainerScale();
  rebuildPads();

  onMouseDown = (event: MouseEvent) => {
    dragging = true;
    dragged = false;
    const { x, y } = eventClipPosition(event);
    dragStart = { x, y };
    containerStart = {
      x: container?.x ?? 0,
      y: container?.y ?? 0,
    };
  };

  onMouseMove = (event: MouseEvent) => {
    if (!container) {
      return;
    }
    const { x, y } = eventClipPosition(event);
    const worldPosition = container.toLocal(new Point(x, y));
    mouseX.value = worldPosition.x;
    mouseY.value = worldPosition.y;
    if (!dragging) {
      return;
    }
    dragged = true;
    container.x = containerStart.x + (x - dragStart.x);
    container.y = containerStart.y + (y - dragStart.y);
  };

  onMouseUp = () => {
    dragging = false;
    if (lastPointerWasPad) {
      lastPointerWasPad = false;
      return;
    }
    if (!dragged) {
      selectedIndex.value = null;
      redrawAll();
    }
  };

  onMouseLeave = () => {
    dragging = false;
  };

  onWheel = (event: WheelEvent) => {
    if (!container) {
      return;
    }
    event.preventDefault();
    const { x, y } = eventClipPosition(event);
    const before = container.toLocal(new Point(x, y));
    const factor = event.deltaY < 0 ? 1.1 : 1 / 1.1;
    zoomScale = Math.min(Math.max(zoomScale * factor, 0.8), 12);
    updateContainerScale();
    const after = container.toLocal(new Point(x, y));
    container.x += (after.x - before.x) * INIT_X_SCALE * zoomScale * currentRevertX();
    container.y += (after.y - before.y) * INIT_Y_SCALE * zoomScale;
  };

  app.canvas.addEventListener("mousedown", onMouseDown);
  app.canvas.addEventListener("mousemove", onMouseMove);
  app.canvas.addEventListener("mouseup", onMouseUp);
  app.canvas.addEventListener("mouseleave", onMouseLeave);
  app.canvas.addEventListener("wheel", onWheel, { passive: false });
}

function cleanupPixi(): void {
  if (app?.canvas && onMouseDown && onMouseMove && onMouseUp && onMouseLeave && onWheel) {
    app.canvas.removeEventListener("mousedown", onMouseDown);
    app.canvas.removeEventListener("mousemove", onMouseMove);
    app.canvas.removeEventListener("mouseup", onMouseUp);
    app.canvas.removeEventListener("mouseleave", onMouseLeave);
    app.canvas.removeEventListener("wheel", onWheel);
  }
  entries = [];
  container = null;
  if (app) {
    app.destroy(true, { children: true });
    app = null;
  }
}

watch(
  () => props.rules,
  () => {
    redrawAll();
  },
);

watch(
  () => props.view,
  () => {
    updateContainerScale();
  },
);

watch(
  () => props.pads,
  () => {
    rebuildPads();
  },
);

onMounted(() => {
  void mountPixi();
});

onBeforeUnmount(() => {
  cleanupPixi();
});
</script>
