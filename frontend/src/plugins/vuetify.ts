import "@mdi/font/css/materialdesignicons.css";
import "vuetify/styles";

import { createVuetify } from "vuetify";
import { aliases, mdi } from "vuetify/iconsets/mdi";
import {
  VAlert,
  VApp,
  VBtn,
  VBtnToggle,
  VCard,
  VCardActions,
  VCardText,
  VCardTitle,
  VChip,
  VCol,
  VContainer,
  VDialog,
  VIcon,
  VLayout,
  VList,
  VListItem,
  VMain,
  VNavigationDrawer,
  VProgressCircular,
  VProgressLinear,
  VRow,
  VSelect,
  VSpacer,
  VSwitch,
  VTextField,
} from "vuetify/components";
import { Ripple } from "vuetify/directives";

const vuetify = createVuetify({
  components: {
    VAlert,
    VApp,
    VBtn,
    VBtnToggle,
    VCard,
    VCardActions,
    VCardText,
    VCardTitle,
    VChip,
    VCol,
    VContainer,
    VDialog,
    VIcon,
    VLayout,
    VList,
    VListItem,
    VMain,
    VNavigationDrawer,
    VProgressCircular,
    VProgressLinear,
    VRow,
    VSelect,
    VSpacer,
    VSwitch,
    VTextField,
  },
  directives: {
    Ripple,
  },
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: { mdi },
  },
  theme: {
    defaultTheme: "estimator",
    themes: {
      estimator: {
        dark: false,
        colors: {
          background: "#f5f0e5",
          surface: "#fffaf2",
          surfaceVariant: "#f0e6d6",
          primary: "#205845",
          secondary: "#9b6b2f",
          accent: "#345f99",
          info: "#345f99",
          success: "#205845",
          warning: "#9b6b2f",
          error: "#a33232",
          "on-primary": "#ffffff",
          "on-surface": "#241f17",
        },
      },
    },
  },
});

export default vuetify;
