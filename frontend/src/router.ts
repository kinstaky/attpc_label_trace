import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("./views/WelcomeView.vue"),
  },
  {
    path: "/label",
    name: "label",
    component: () => import("./views/LabelView.vue"),
  },
  {
    path: "/histograms",
    name: "histograms",
    component: () => import("./views/HistogramView.vue"),
  },
  {
    path: "/review",
    name: "review",
    component: () => import("./views/TraceReviewView.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
